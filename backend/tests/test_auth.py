from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    raw = "super_secure_pass_123"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "user-uuid-12345", "email": "test@example.com"}
    token = create_access_token(payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-12345"
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded


def test_invalid_jwt_token():
    decoded = decode_access_token("gibberish.invalid.token")
    assert decoded is None
