"""Builds the single user-prompt (task) from a conversation's message rows.

Per SPEC, the 3-way conversation is presented to the model as one labelled
transcript in a single user prompt — not user/assistant turns — because a
third participant (the human owner) can appear at any point.
"""

from .config import OWNER_NAME

_LABELS = {
    "visitor": "Visitor",
    "avatar": "Avatar",
    "human": f"Human ({OWNER_NAME})",
}


def build_task_prompt(rows: list[dict], visitor_name: str | None = None) -> str:
    """Format all message rows (chronological) into the task prompt.

    The rows must already include the visitor's latest message as the last
    visitor entry.
    """
    who = f' The visitor gave their name/initials as "{visitor_name}".' if visitor_name else ""
    lines = [
        "Here is the full conversation so far between the Visitor, you (the Avatar), "
        f"and possibly the Human ({OWNER_NAME}) themself:{who}",
        "",
    ]
    for row in rows:
        label = _LABELS.get(row["role"], row["role"])
        lines.append(f"{label}: {row['content']}")
        lines.append("")
    lines.append(
        "Respond now to the Visitor's latest message above, as the Avatar. "
        "Reply with the message text only — no role label prefix."
    )
    return "\n".join(lines)
