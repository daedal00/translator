"""Tests for the in-process WebSocket broadcast hub."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.hub import SessionHub


@pytest.fixture
def hub():
    return SessionHub()


def _make_ws(fail: bool = False):
    ws = MagicMock()
    if fail:
        ws.send_json = AsyncMock(side_effect=RuntimeError("closed"))
    else:
        ws.send_json = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# join / leave / attendee_count
# ---------------------------------------------------------------------------


def test_initial_count_is_zero(hub):
    assert hub.attendee_count("ABC123") == 0


def test_join_increments_count(hub):
    ws = _make_ws()
    hub.join("ABC123", ws)
    assert hub.attendee_count("ABC123") == 1


def test_multiple_joins_same_code(hub):
    for _ in range(3):
        hub.join("XYZ", _make_ws())
    assert hub.attendee_count("XYZ") == 3


def test_join_different_codes_isolated(hub):
    hub.join("CODE1", _make_ws())
    hub.join("CODE2", _make_ws())
    assert hub.attendee_count("CODE1") == 1
    assert hub.attendee_count("CODE2") == 1


def test_leave_decrements_count(hub):
    ws = _make_ws()
    hub.join("ABC", ws)
    hub.leave("ABC", ws)
    assert hub.attendee_count("ABC") == 0


def test_leave_nonexistent_ws_is_safe(hub):
    ws = _make_ws()
    hub.leave("NOPE", ws)  # should not raise


def test_leave_only_removes_target_ws(hub):
    ws1, ws2 = _make_ws(), _make_ws()
    hub.join("CODE", ws1)
    hub.join("CODE", ws2)
    hub.leave("CODE", ws1)
    assert hub.attendee_count("CODE") == 1


def test_duplicate_join_does_not_double_count(hub):
    ws = _make_ws()
    hub.join("DUP", ws)
    hub.join("DUP", ws)  # same object again
    assert hub.attendee_count("DUP") == 1


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_sends_to_all(hub):
    ws1, ws2 = _make_ws(), _make_ws()
    hub.join("ROOM", ws1)
    hub.join("ROOM", ws2)
    await hub.broadcast("ROOM", {"type": "caption", "text": "hello"})
    ws1.send_json.assert_awaited_once_with({"type": "caption", "text": "hello"})
    ws2.send_json.assert_awaited_once_with({"type": "caption", "text": "hello"})


@pytest.mark.asyncio
async def test_broadcast_empty_room_is_safe(hub):
    await hub.broadcast("EMPTY", {"type": "ping"})  # should not raise


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections(hub):
    good = _make_ws(fail=False)
    dead = _make_ws(fail=True)
    hub.join("ROOM2", good)
    hub.join("ROOM2", dead)

    await hub.broadcast("ROOM2", {"type": "test"})

    # Dead connection should have been pruned
    assert hub.attendee_count("ROOM2") == 1
    assert dead not in hub._sessions["ROOM2"]
    assert good in hub._sessions["ROOM2"]


@pytest.mark.asyncio
async def test_broadcast_does_not_affect_other_rooms(hub):
    ws1 = _make_ws()
    ws2 = _make_ws()
    hub.join("ROOM_A", ws1)
    hub.join("ROOM_B", ws2)

    await hub.broadcast("ROOM_A", {"type": "msg"})

    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_not_awaited()
