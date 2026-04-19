"""Integration tests for the /auth endpoints."""
import pytest

from app.core.security import create_access_token, create_refresh_token


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post(
        "/auth/register",
        json={"org_name": "Test Church", "email": "admin@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"org_name": "Org", "email": "dup@example.com", "password": "supersecret123"}
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already registered" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post(
        "/auth/register",
        json={"org_name": "Org", "email": "short@example.com", "password": "tooshort"},
    )
    assert resp.status_code == 400
    assert "12" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    resp = await client.post(
        "/auth/register",
        json={"org_name": "Org", "email": "not-an-email", "password": "supersecret123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/auth/register",
        json={"org_name": "Church", "email": "login@example.com", "password": "supersecret123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"org_name": "Church", "email": "wrongpw@example.com", "password": "supersecret123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "wrongpw@example.com", "password": "wrongpassword12"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(client):
    reg = await client.post(
        "/auth/register",
        json={"org_name": "Org", "email": "refresh@example.com", "password": "supersecret123"},
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client):
    reg = await client.post(
        "/auth/register",
        json={"org_name": "Org", "email": "badrefresh@example.com", "password": "supersecret123"},
    )
    access_token = reg.json()["access_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_garbage_token(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    resp = await client.get("/sessions")
    assert resp.status_code in (401, 403)
