"""Visitor chat: the SSE streaming endpoint and the conversation fetch/poll.

POST /api/chat order of operations (SPEC):
  1. rate-limit check -> 429 JSON before anything else (no DB write, no LLM)
  2. clamp message to 20,000 chars (+ note) — the clamped text is stored AND sent
  3. insert the visitor row
  4. bare `Qn` -> instant FAQ answer, no LLM call
  5. otherwise run the Agent and stream tokens + tool activity over SSE
"""

import asyncio
import json

from agents import Runner
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent

from .. import config, db, rate_limit, settings_store
from ..agent import avatar_agent
from ..models import ChatRequest, ConversationResponse
from ..tools.faq import find_faq, parse_qn_shortcut
from ..tools.push import push
from ..transcript import build_task_prompt

router = APIRouter()

# Fire-and-forget background tasks (e.g. the new-conversation push) need a
# strong reference somewhere, or asyncio may garbage-collect them mid-flight.
_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _clamp(message: str) -> str:
    if len(message) <= config.MAX_MESSAGE_CHARS:
        return message
    return message[: config.MAX_MESSAGE_CHARS] + "\n" + config.TRUNCATION_NOTE


async def _notify_new_conversation(who: str, content: str) -> None:
    """Best-effort: a Pushover hiccup here must never surface to the visitor.

    A short timeout bounds the worst case for a background thread-pool
    worker — this notification is non-critical, unlike push_tool/attention
    pushes, which the visitor is actively waiting on and keep the full 15s.
    """
    try:
        await asyncio.to_thread(
            push, f"[New conversation] {who}: {content[:300]}", 5
        )
    except Exception:
        pass


@router.post("/api/chat")
async def chat(request: ChatRequest):
    if not rate_limit.allow(request.conversation_id):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited"},
        )

    state = await asyncio.to_thread(
        settings_store.conversation_state, request.conversation_id
    )
    if state["visitor_blocked"]:
        return JSONResponse(status_code=403, content={"error": "blocked"})

    content = _clamp(request.message)
    visitor_name = (request.visitor_name or "").strip() or None
    faq_number = parse_qn_shortcut(request.message)

    # Mandatory name/initials — except the ?q=N auto-submit on page load,
    # which fires before the visitor has had a chance to type anything.
    name_exempt = request.auto_deep_link and faq_number is not None
    if not visitor_name and not name_exempt:
        return JSONResponse(status_code=400, content={"error": "name_required"})

    visitor_row = await asyncio.to_thread(
        db.insert_message,
        conversation_id=request.conversation_id,
        role="visitor",
        content=content,
        conversation_name=visitor_name,
        needs_attention=request.attention,
        tool_calls=[{"tool": "attention_request"}] if request.attention else None,
    )

    async def stream():
        yield _sse(
            "visitor_message",
            {
                "id": visitor_row["id"],
                "content": visitor_row["content"],
                "created_at": visitor_row["created_at"],
            },
        )
        # Fetched once, up front: doubles as "is this conversation brand new"
        # (exactly one row so far) and, on the agent path below, the transcript.
        rows = await asyncio.to_thread(db.fetch_conversation, request.conversation_id)
        is_new_conversation = len(rows) == 1
        if state["avatar_muted"]:
            yield _sse("meta", {"mode": "muted"})
        elif faq_number is not None:
            yield _sse("meta", {"mode": "instant", "faq_number": faq_number})
        else:
            yield _sse("meta", {"mode": "agent"})
        try:
            if is_new_conversation:
                # Fire-and-forget: this is a side notification for the human,
                # not part of answering the visitor — it must never add
                # latency (or risk) to the actual reply below.
                _fire_and_forget(
                    _notify_new_conversation(visitor_name or "A visitor", content)
                )
            if request.attention:
                # The visitor pressed the attention toggle: ping the human
                # directly, before (and regardless of) any model involvement.
                who = visitor_name or "A visitor"
                yield _sse("tool_call", {"tool": "attention_push"})
                await asyncio.to_thread(
                    push,
                    f"[Attention requested] {who}: {content[:500]}",
                )
                yield _sse("tool_result", {"tool": "attention_push"})

            avatar_row = None
            if state["avatar_muted"]:
                # The human is handling this conversation live right now —
                # stay silent so the visitor never gets two replies.
                pass
            elif faq_number is not None:
                answer = find_faq(faq_number)
                yield _sse("token", {"text": answer})
                avatar_row = await asyncio.to_thread(
                    db.insert_message,
                    conversation_id=request.conversation_id,
                    role="avatar",
                    content=answer,
                    tool_calls=[{"tool": "instant_faq", "faq_number": faq_number}],
                )
            else:
                yield _sse("meta", {"mode": "agent"})
                task = build_task_prompt(rows, visitor_name=visitor_name)
                result = Runner.run_streamed(avatar_agent, task)
                text_parts: list[str] = []
                tools_used: list[str] = []
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(
                        event.data, ResponseTextDeltaEvent
                    ):
                        text_parts.append(event.data.delta)
                        yield _sse("token", {"text": event.data.delta})
                    elif event.type == "run_item_stream_event":
                        if event.name == "tool_called":
                            tool = getattr(event.item, "tool_name", None) or "tool"
                            tools_used.append(tool)
                            yield _sse("tool_call", {"tool": tool})
                        elif event.name == "tool_output":
                            tool = tools_used[-1] if tools_used else "tool"
                            yield _sse("tool_result", {"tool": tool})
                answer = "".join(text_parts) or str(result.final_output or "")
                avatar_row = await asyncio.to_thread(
                    db.insert_message,
                    conversation_id=request.conversation_id,
                    role="avatar",
                    content=answer,
                    tool_calls=[{"tool": t} for t in tools_used] or None,
                    needs_attention="push_tool" in tools_used,
                )
            yield _sse(
                "done",
                {
                    "id": avatar_row["id"] if avatar_row else None,
                    "created_at": avatar_row["created_at"] if avatar_row else None,
                    "needs_attention": avatar_row["needs_attention"] if avatar_row else False,
                },
            )
        except Exception as exc:  # surface a terminal error event to the client
            yield _sse("error", {"message": f"The Avatar hit a problem: {exc}"})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/api/conversation/{conversation_id}", response_model=ConversationResponse
)
async def get_conversation(conversation_id: str, after_id: int | None = None):
    """Full thread (Keep-chat resume) or, with after_id, only newer rows (polling).

    Not auth-gated: possession of the unguessable conversation_id UUID is the
    visitor's access control (SPEC Q&A #6).
    """
    rows = await asyncio.to_thread(db.fetch_conversation, conversation_id, after_id)
    return ConversationResponse(
        conversation_id=conversation_id,
        conversation_name=db.derive_conversation_name(rows),
        messages=rows,
    )
