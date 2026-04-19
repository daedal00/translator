"""Integration tests for the /sessions endpoints."""
import pytest


async def _register_and_login(client, email: str, org: str = "Church") -> str:
    """Register a user and return a valid Bearer token."""
    resp = await client.post(
        "/auth/register",
        json={"org_name": org, "email": email, "password": "supersecret123"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Create session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_success(client):
    token = await _register_and_login(client, "create@example.com")
    resp = await client.post(
        "/sessions",
        json={"title": "Sunday Service", "source_lang": "ko"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Sunday Service"
    assert body["source_lang"] == "ko"
    assert len(body["code"]) == 6
    assert body["is_live"] is False
    assert body["attendees"] == 0


@pytest.mark.asyncio
async def test_create_session_default_values(client):
    token = await _register_and_login(client, "defaults@example.com")
    resp = await client.post("/sessions", json={}, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_lang"] == "ko"
    assert body["title"] == ""


@pytest.mark.asyncio
async def test_create_session_requires_auth(client):
    resp = await client.post("/sessions", json={"title": "No Auth"})
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# List sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    token = await _register_and_login(client, "listempty@example.com")
    resp = await client.get("/sessions", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_sessions_returns_own_sessions(client):
    token = await _register_and_login(client, "listowned@example.com")
    for title in ("Session A", "Session B"):
        await client.post("/sessions", json={"title": title}, headers=_auth(token))

    resp = await client.get("/sessions", headers=_auth(token))
    assert resp.status_code == 200
    titles = [s["title"] for s in resp.json()]
    assert "Session A" in titles
    assert "Session B" in titles


@pytest.mark.asyncio
async def test_list_sessions_isolated_across_orgs(client):
    token_a = await _register_and_login(client, "orga@example.com", org="Org A")
    token_b = await _register_and_login(client, "orgb@example.com", org="Org B")

    await client.post("/sessions", json={"title": "A's session"}, headers=_auth(token_a))

    resp = await client.get("/sessions", headers=_auth(token_b))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_sessions_requires_auth(client):
    resp = await client.get("/sessions")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Start session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_session_success(client):
    token = await _register_and_login(client, "start@example.com")
    code = (await client.post("/sessions", json={}, headers=_auth(token))).json()["code"]

    resp = await client.post(f"/sessions/{code}/start", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    sessions = await client.get("/sessions", headers=_auth(token))
    session = next(s for s in sessions.json() if s["code"] == code)
    assert session["is_live"] is True


@pytest.mark.asyncio
async def test_start_session_wrong_org(client):
    token_owner = await _register_and_login(client, "owner@example.com", org="Owner Org")
    token_other = await _register_and_login(client, "other@example.com", org="Other Org")

    code = (await client.post("/sessions", json={}, headers=_auth(token_owner))).json()["code"]

    resp = await client.post(f"/sessions/{code}/start", headers=_auth(token_other))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_session_nonexistent(client):
    token = await _register_and_login(client, "nostart@example.com")
    resp = await client.post("/sessions/ZZZZZZ/start", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_session_requires_auth(client):
    resp = await client.post("/sessions/AAAAAA/start")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# End session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_session_success(client):
    token = await _register_and_login(client, "end@example.com")
    code = (await client.post("/sessions", json={}, headers=_auth(token))).json()["code"]
    await client.post(f"/sessions/{code}/start", headers=_auth(token))

    resp = await client.post(f"/sessions/{code}/end", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    sessions = await client.get("/sessions", headers=_auth(token))
    session = next(s for s in sessions.json() if s["code"] == code)
    assert session["is_live"] is False


@pytest.mark.asyncio
async def test_end_session_wrong_org(client):
    token_owner = await _register_and_login(client, "endowner@example.com", org="End Owner")
    token_other = await _register_and_login(client, "endother@example.com", org="End Other")

    code = (await client.post("/sessions", json={}, headers=_auth(token_owner))).json()["code"]

    resp = await client.post(f"/sessions/{code}/end", headers=_auth(token_other))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_end_session_nonexistent(client):
    token = await _register_and_login(client, "noend@example.com")
    resp = await client.post("/sessions/ZZZZZZ/end", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_end_session_requires_auth(client):
    resp = await client.post("/sessions/AAAAAA/end")
    assert resp.status_code in (401, 403)
