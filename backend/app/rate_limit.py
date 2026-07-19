"""Per-conversation rate limit: 20 chat messages per minute.

Moving-window limiter from the `limits` package, held in memory per process
(sufficient because OpenRouter caps overall spend and a browser's requests
stick to one machine — SPEC Q&A #12).
"""

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from .config import RATE_LIMIT

_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)
_rate = parse(RATE_LIMIT)
_reset_rate = parse("3/hour")


def allow(conversation_id: str) -> bool:
    """True if this conversation may send another chat message now."""
    return _limiter.hit(_rate, "chat", conversation_id)


def allow_reset_request() -> bool:
    """Password-reset codes are capped at 3/hour (global, in-memory)."""
    return _limiter.hit(_reset_rate, "admin", "reset")
