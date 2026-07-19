"""Shared fixtures for the backend test suite.

Test conversations are created under randomly-generated UUIDs and deleted
after each test module via the cleanup fixture.
"""

import uuid

import httpx
import pytest

from app import db
from app.main import app


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=180
    ) as c:
        yield c


@pytest.fixture()
async def admin_client(client):
    """A client that has logged in to admin."""
    import os

    r = await client.post("/admin/login", json={"password": os.environ["ADMIN_PASSWORD"]})
    assert r.status_code == 200
    return client


@pytest.fixture()
def conversation_id():
    """A fresh conversation id, deleted from Supabase after the test."""
    cid = str(uuid.uuid4())
    yield cid
    db.get_client().table("messages").delete().eq("conversation_id", cid).execute()


async def collect_sse(client, payload) -> list[tuple[str, str]]:
    """POST /api/chat and return the (event, data) pairs of the SSE stream."""
    events: list[tuple[str, str]] = []
    async with client.stream("POST", "/api/chat", json=payload) as r:
        assert r.status_code == 200
        current = None
        async for line in r.aiter_lines():
            if line.startswith("event:"):
                current = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current:
                events.append((current, line.split(":", 1)[1].strip()))
                current = None
    return events
