"""In-process WebSocket broadcast hub. One instance per process."""
from collections import defaultdict

from fastapi import WebSocket


class SessionHub:
    def __init__(self) -> None:
        self._sessions: dict[str, set[WebSocket]] = defaultdict(set)

    def join(self, code: str, ws: WebSocket) -> None:
        self._sessions[code].add(ws)

    def leave(self, code: str, ws: WebSocket) -> None:
        self._sessions[code].discard(ws)

    def attendee_count(self, code: str) -> int:
        return len(self._sessions[code])

    async def broadcast(self, code: str, data: dict) -> None:
        dead: set[WebSocket] = set()
        for ws in list(self._sessions[code]):
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self._sessions[code] -= dead


hub = SessionHub()
