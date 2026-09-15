def test_customer_can_create_a_session(client, customer):
    user, headers = customer
    resp = client.post("/api/v1/sessions", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["customer_id"] == user["id"]
    assert body["session_status"] == "INITIATED"
    assert body["technician_id"] is None


def test_technician_cannot_create_a_session(client, technician):
    _, headers = technician
    resp = client.post("/api/v1/sessions", headers=headers)
    assert resp.status_code == 403


def test_session_creation_requires_auth(client):
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 401


def test_get_session_returns_the_created_session(client, customer):
    _, headers = customer
    created = client.post("/api/v1/sessions", headers=headers).json()
    resp = client.get(f"/api/v1/sessions/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_session_404s_for_unknown_id(client, customer):
    _, headers = customer
    resp = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404
