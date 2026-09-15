import uuid


def test_register_creates_user_without_leaking_password_hash(client, register_user):
    user, _ = register_user(role="CUSTOMER")
    assert user["role"] == "CUSTOMER"
    assert user["is_active"] is True
    assert "hashed_password" not in user
    assert "password" not in user


def test_register_rejects_duplicate_email(client, register_user):
    user, password = register_user(role="CUSTOMER")
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dupe",
            "email": user["email"],
            "phone_number": f"9{uuid.uuid4().int % 10**9:09d}",
            "password": "testpass123",
            "role": "CUSTOMER",
        },
    )
    assert resp.status_code == 400


def test_register_rejects_invalid_role(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Bad Role",
            "email": f"badrole_{uuid.uuid4().hex[:8]}@example.com",
            "phone_number": f"9{uuid.uuid4().int % 10**9:09d}",
            "password": "testpass123",
            "role": "SUPERADMIN",
        },
    )
    assert resp.status_code == 422


def test_login_with_wrong_password_is_rejected(client, register_user):
    user, _ = register_user(role="CUSTOMER")
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": user["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_me_requires_a_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_for_valid_token(client, customer):
    user, headers = customer
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == user["id"]


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
