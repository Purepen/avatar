"""Pushover notification tool — how the Avatar gets the human involved."""

import requests
from agents import function_tool

from .. import config

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def push(message: str, timeout: int = 15) -> str:
    payload = {
        "user": config.PUSHOVER_USER,
        "token": config.PUSHOVER_TOKEN,
        "message": message,
    }
    status = requests.post(PUSHOVER_URL, data=payload, timeout=timeout).status_code
    return f"Message pushed with status code {status}."


@function_tool
def push_tool(message: str) -> str:
    """Send the given message to the human operator (your human twin) as a push notification.

    Use this when the visitor wants to get in touch (include their email and a short
    summary in the message), when they ask about pricing or try to negotiate scope or
    terms for work, when they offer work/a role/a collaboration, or when you can't
    answer a question and need the human.

    Args:
        message: The message to send to the human operator.
    """
    return push(message)
