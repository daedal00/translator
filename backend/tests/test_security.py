import pytest
from app.core.security import (
    generate_session_code,
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_password_roundtrip():
    pw = "supersecret123"
    assert verify_password(pw, hash_password(pw))


def test_wrong_password():
    assert not verify_password("wrong", hash_password("correct"))


def test_session_code_format():
    code = generate_session_code()
    assert len(code) == 6
    # No ambiguous characters
    assert "O" not in code and "I" not in code and "0" not in code


def test_access_token_roundtrip():
    token = create_access_token("42")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
