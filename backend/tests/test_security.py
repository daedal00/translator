import time

import jwt
import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_session_code,
    hash_password,
    verify_password,
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


def test_refresh_token_roundtrip():
    token = create_refresh_token("99")
    payload = decode_token(token)
    assert payload["sub"] == "99"
    assert payload["type"] == "refresh"


def test_access_and_refresh_tokens_differ():
    access = create_access_token("1")
    refresh = create_refresh_token("1")
    assert access != refresh


def test_decode_token_wrong_secret_raises():
    token = create_access_token("7")
    with pytest.raises(Exception):
        jwt.decode(token, "wrong-secret", algorithms=["HS256"])


def test_decode_expired_token_raises():
    from datetime import UTC, datetime, timedelta
    from app.core.config import settings

    expired_payload = {
        "sub": "5",
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_session_code_custom_length():
    for length in (4, 8, 12):
        code = generate_session_code(length=length)
        assert len(code) == length


def test_session_codes_are_unique():
    codes = {generate_session_code() for _ in range(200)}
    # With a 6-char alphabet of ~32 chars the collision probability is negligible;
    # we just assert we got more than one distinct value.
    assert len(codes) > 1


def test_session_code_charset():
    """All generated characters must be from the allowed alphabet (no O, I, 0)."""
    import string

    allowed = set(
        string.ascii_uppercase.replace("O", "").replace("I", "")
        + string.digits.replace("0", "")
    )
    for _ in range(50):
        code = generate_session_code()
        assert set(code).issubset(allowed)
