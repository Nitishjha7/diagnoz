def test_customer_cannot_create_a_technician_profile(client, customer):
    _, headers = customer
    resp = client.post(
        "/api/v1/technicians/me/profile",
        json={"latitude": 28.6139, "longitude": 77.2090},
        headers=headers,
    )
    assert resp.status_code == 403


def test_technician_can_create_and_update_profile(client, technician):
    _, headers = technician

    created = client.post(
        "/api/v1/technicians/me/profile",
        json={"latitude": 28.6139, "longitude": 77.2090},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["is_available"] is True

    updated = client.patch(
        "/api/v1/technicians/me/location",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]


def test_update_location_404s_without_a_profile_first(client, technician):
    _, headers = technician
    resp = client.patch(
        "/api/v1/technicians/me/location",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=headers,
    )
    assert resp.status_code == 404


def test_set_availability_toggles_the_flag(client, technician):
    _, headers = technician
    client.post(
        "/api/v1/technicians/me/profile",
        json={"latitude": 28.6139, "longitude": 77.2090},
        headers=headers,
    )

    resp = client.patch("/api/v1/technicians/me/availability?is_available=false", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_available"] is False

    resp = client.patch("/api/v1/technicians/me/availability?is_available=true", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_available"] is True


def test_profile_endpoints_require_auth(client):
    resp = client.post("/api/v1/technicians/me/profile", json={"latitude": 1, "longitude": 1})
    assert resp.status_code == 401
