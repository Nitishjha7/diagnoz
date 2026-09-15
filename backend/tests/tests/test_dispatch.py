from tests.conftest import DELHI_LAT, DELHI_LON

NEARBY_LAT, NEARBY_LON = 28.6150, 77.2100
FAR_LAT, FAR_LON = 19.0760, 72.8777  # Mumbai - outside the 5km Delhi radius


def test_dispatch_matches_the_nearby_available_technician(client, customer, available_technician):
    tech_user, _ = available_technician
    _, cust_headers = customer

    resp = client.post(
        "/api/v1/dispatch",
        json={"latitude": NEARBY_LAT, "longitude": NEARBY_LON},
        headers=cust_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["dispatch"]["technician_id"] == tech_user["id"]
    assert body["dispatch"]["dispatch_status"] == "PENDING"
    assert len(body["start_otp"]) == 6
    assert len(body["end_otp"]) == 6
    assert body["start_otp"] != body["end_otp"]


def test_dispatch_404s_when_nobody_is_in_range(client, customer, available_technician):
    _, cust_headers = customer
    resp = client.post(
        "/api/v1/dispatch",
        json={"latitude": FAR_LAT, "longitude": FAR_LON},
        headers=cust_headers,
    )
    assert resp.status_code == 404


def test_dispatch_requires_customer_role(client, technician):
    _, tech_headers = technician
    resp = client.post(
        "/api/v1/dispatch",
        json={"latitude": NEARBY_LAT, "longitude": NEARBY_LON},
        headers=tech_headers,
    )
    assert resp.status_code == 403


def test_second_dispatch_for_the_same_technician_is_locked_out(client, customer, available_technician):
    _, cust_headers = customer

    first = client.post(
        "/api/v1/dispatch",
        json={"latitude": NEARBY_LAT, "longitude": NEARBY_LON},
        headers=cust_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/dispatch",
        json={"latitude": NEARBY_LAT, "longitude": NEARBY_LON},
        headers=cust_headers,
    )
    assert second.status_code == 409


def _create_dispatch(client, cust_headers):
    resp = client.post(
        "/api/v1/dispatch",
        json={"latitude": NEARBY_LAT, "longitude": NEARBY_LON},
        headers=cust_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_full_dual_otp_lifecycle_reaches_completed(client, customer, available_technician):
    _, cust_headers = customer
    _, tech_headers = available_technician

    created = _create_dispatch(client, cust_headers)
    dispatch_id = created["dispatch"]["id"]

    accept_resp = client.post(f"/api/v1/dispatch/{dispatch_id}/accept", headers=tech_headers)
    assert accept_resp.status_code == 200
    assert accept_resp.json()["dispatch_status"] == "ACCEPTED"

    wrong_start = client.post(
        f"/api/v1/dispatch/{dispatch_id}/verify-start-otp",
        json={"otp": "000000"},
        headers=tech_headers,
    )
    assert wrong_start.status_code == 400

    start_resp = client.post(
        f"/api/v1/dispatch/{dispatch_id}/verify-start-otp",
        json={"otp": created["start_otp"]},
        headers=tech_headers,
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["dispatch_status"] == "IN_PROGRESS"

    wrong_end = client.post(
        f"/api/v1/dispatch/{dispatch_id}/verify-end-otp",
        json={"otp": "000000"},
        headers=tech_headers,
    )
    assert wrong_end.status_code == 400

    end_resp = client.post(
        f"/api/v1/dispatch/{dispatch_id}/verify-end-otp",
        json={"otp": created["end_otp"]},
        headers=tech_headers,
    )
    assert end_resp.status_code == 200
    completed = end_resp.json()
    assert completed["dispatch_status"] == "COMPLETED"
    assert completed["completed_at"] is not None


def test_cannot_skip_from_pending_straight_to_start_otp(client, customer, available_technician):
    _, cust_headers = customer
    _, tech_headers = available_technician

    created = _create_dispatch(client, cust_headers)
    dispatch_id = created["dispatch"]["id"]

    resp = client.post(
        f"/api/v1/dispatch/{dispatch_id}/verify-start-otp",
        json={"otp": created["start_otp"]},
        headers=tech_headers,
    )
    assert resp.status_code == 409


def test_a_different_technician_cannot_act_on_someone_elses_dispatch(
    client, customer, available_technician, register_user, auth_headers
):
    _, cust_headers = customer
    other_user, other_password = register_user(role="TECHNICIAN")
    other_tech_headers = auth_headers(other_user["email"], other_password)

    created = _create_dispatch(client, cust_headers)
    dispatch_id = created["dispatch"]["id"]

    resp = client.post(f"/api/v1/dispatch/{dispatch_id}/accept", headers=other_tech_headers)
    assert resp.status_code == 403


def test_get_dispatch_404s_for_unknown_id(client, customer):
    _, headers = customer
    resp = client.get("/api/v1/dispatch/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404
