"""Loads the owner's knowledge files once at import time.

knowledge.md — first-person profile of the owner.
style.md     — voice, formatting and safety rules.
"""

from .config import KNOWLEDGE_DIR

KNOWLEDGE = (KNOWLEDGE_DIR / "knowledge.md").read_text(encoding="utf-8")
STYLE = (KNOWLEDGE_DIR / "style.md").read_text(encoding="utf-8")
