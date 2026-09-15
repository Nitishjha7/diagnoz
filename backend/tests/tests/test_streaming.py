from pathlib import Path

import pytest

from app.core.config import settings

VIDEO_ID = "test-stream-video"
VIDEO_BYTES = 1000  # small fake payload, content doesn't matter for range-parsing tests


@pytest.fixture(scope="module", autouse=True)
def fake_video_file():
    video_dir = Path(settings.REFERENCE_VIDEO_PATH)
    video_dir.mkdir(parents=True, exist_ok=True)
    video_path = video_dir / f"{VIDEO_ID}.mp4"
    video_path.write_bytes(bytes(range(256)) * (VIDEO_BYTES // 256 + 1))
    yield video_path
    video_path.unlink(missing_ok=True)


def test_streaming_requires_auth(client):
    resp = client.get(f"/api/v1/videos/stream/{VIDEO_ID}")
    assert resp.status_code == 401


def test_streaming_returns_full_file_without_range_header(client, customer):
    _, headers = customer
    resp = client.get(f"/api/v1/videos/stream/{VIDEO_ID}", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["accept-ranges"] == "bytes"


def test_streaming_returns_206_for_a_partial_range(client, customer):
    _, headers = customer
    resp = client.get(
        f"/api/v1/videos/stream/{VIDEO_ID}",
        headers={**headers, "Range": "bytes=100-199"},
    )
    assert resp.status_code == 206
    assert resp.headers["content-length"] == "100"
    assert "100-199" in resp.headers["content-range"]


def test_streaming_416s_for_an_out_of_bounds_range(client, customer):
    _, headers = customer
    resp = client.get(
        f"/api/v1/videos/stream/{VIDEO_ID}",
        headers={**headers, "Range": "bytes=999999-9999999"},
    )
    assert resp.status_code == 416


def test_streaming_404s_for_an_unknown_video(client, customer):
    _, headers = customer
    resp = client.get("/api/v1/videos/stream/does-not-exist", headers=headers)
    assert resp.status_code == 404
