import json
import struct
import uuid

TRIAGE_BUFFER_THRESHOLD_BYTES = 48_000


def _loud_pcm(seconds=1.6, sample_rate=16_000):
    samples = [3000 if i % 2 == 0 else -3000 for i in range(int(sample_rate * seconds))]
    return struct.pack(f"<{len(samples)}h", *samples)


def test_audio_triage_full_pipeline(client, customer):
    _, headers = customer
    session = client.post("/api/v1/sessions", headers=headers).json()

    with client.websocket_connect(f"/ws/audio/triage/{session['id']}") as ws:
        ws.send_bytes(_loud_pcm())
        transcript_msg = json.loads(ws.receive_text())
        assert transcript_msg["type"] == "TRANSCRIPT_CHUNK"

        ws.send_text("Mera AC cooling nahi kar raha aur awaaz aa rahi hai")
        diagnosis_msg = json.loads(ws.receive_text())
        assert diagnosis_msg["type"] == "DIAGNOSIS_COMPLETE"
        payload = diagnosis_msg["payload"]
        assert payload["appliance_type"] == "AC"
        assert payload["urgency"] in ("LOW", "MEDIUM", "HIGH")

        # TTS audio packets stream back as binary frames
        audio_packet = ws.receive_bytes()
        assert isinstance(audio_packet, bytes)
        assert len(audio_packet) > 0


def test_audio_triage_persists_transcript_and_diagnosis_to_session(client, customer):
    _, headers = customer
    session = client.post("/api/v1/sessions", headers=headers).json()

    with client.websocket_connect(f"/ws/audio/triage/{session['id']}") as ws:
        ws.send_bytes(_loud_pcm())
        ws.receive_text()  # TRANSCRIPT_CHUNK
        ws.send_text("Washing machine is leaking water everywhere")
        ws.receive_text()  # DIAGNOSIS_COMPLETE
        ws.receive_bytes()  # first TTS packet, drain so the socket closes cleanly

    updated = client.get(f"/api/v1/sessions/{session['id']}", headers=headers).json()
    assert updated["voice_transcript"] == "Washing machine is leaking water everywhere"
    assert updated["ai_structured_summary"]["appliance_type"] == "WASHING_MACHINE"


def test_canvas_sync_relays_draw_event_between_two_peers():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    session_id = f"test-canvas-{uuid.uuid4().hex[:8]}"
    draw_event = {"action": "DRAW", "norm_x": 0.4, "norm_y": 0.7, "color": "#ff0000"}

    with client.websocket_connect(f"/ws/canvas/sync/{session_id}") as ws_a:
        with client.websocket_connect(f"/ws/canvas/sync/{session_id}") as ws_b:
            ws_a.send_text(json.dumps(draw_event))
            received = json.loads(ws_b.receive_text())
            assert received == draw_event


def test_webrtc_signaling_relays_offer_to_the_other_peer():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    session_id = f"test-video-{uuid.uuid4().hex[:8]}"
    offer = {"type": "offer", "payload": {"sdp": "fake-sdp"}}

    with client.websocket_connect(f"/ws/video/signal/{session_id}") as customer_ws:
        with client.websocket_connect(f"/ws/video/signal/{session_id}") as technician_ws:
            customer_ws.send_json(offer)
            received = technician_ws.receive_json()
            assert received == offer
