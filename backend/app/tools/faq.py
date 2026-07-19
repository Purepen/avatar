"""The numbered FAQ: loaded once from knowledge/faq.jsonl.

Each row: {"faq": n, "question": ..., "answer": ..., "query": ...}.
The short `query` phrasings are listed in the agent instructions for routing;
the tool and the Qn shortcut both return the full original question + answer.
"""

import json
import re

from agents import function_tool

from ..config import KNOWLEDGE_DIR

with (KNOWLEDGE_DIR / "faq.jsonl").open(encoding="utf-8") as f:
    FAQS: list[dict] = [json.loads(line) for line in f if line.strip()]

FAQ_LOOKUP: dict[int, dict] = {faq["faq"]: faq for faq in FAQS}

_QN_RE = re.compile(r"^q(\d{1,2})$", re.IGNORECASE)


def find_faq(question_number: int) -> str:
    """Full question + answer for a FAQ number, or a friendly miss message."""
    faq = FAQ_LOOKUP.get(question_number)
    if faq:
        return f"**Q{faq['faq']}:** {faq['question']}\n\n{faq['answer']}"
    return (
        f"There's no FAQ number {question_number} — the list currently runs "
        f"from Q1 to Q{max(FAQ_LOOKUP)}. Feel free to just ask your question directly."
    )


def parse_qn_shortcut(text: str) -> int | None:
    """Return the FAQ number if the message is a bare Qn shortcut (e.g. 'Q2')."""
    match = _QN_RE.match(text.strip())
    return int(match.group(1)) if match else None


@function_tool
def faq_tool(question_number: int) -> str:
    """Retrieve the full answer to a frequently asked question by its number.

    Args:
        question_number: The FAQ number from the list in your instructions.
    """
    return find_faq(question_number)
