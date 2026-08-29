# DiagnoZ: Technical Specification & Implementation Guide

Real-Time Video Tele-Diagnostic, Voice AI Triage & Field Service Dispatch Platform.

**Core framework:** FastAPI (Python 3.12, ASGI) · React 19 · Celery distributed workers
**Target domain:** Enterprise remote diagnostics, high-concurrency media, spatial logistics
**Industry references:** Frontdoor Pro, TechSee, Urban Company, JioCinema/Hotstar media infra

---

## 1. Executive Summary & Business Case

### The industry problem

In home appliances (AC, washing machines, refrigerators, commercial chillers), **35–45% of
physical technician dispatches are redundant**. Technicians spend 1–2 hours in city traffic
to diagnose a tripped breaker, a loose connector, a clogged filter, or a wrong mode setting.

For service companies (Urban Company, ServiceTitan, warranty insurers) this causes:

- **Fuel & fleet cost** — ₹250–₹400 wasted per false-alarm dispatch.
- **Low technician utilization** — skilled engineers spend ~60% of the day in transit, not
  on billable repairs.
- **Slow turnaround** — customers wait 4–24 hours for issues resolvable in 3 minutes over a
  guided visual session.

### The solution & quantifiable ROI

- **First-Contact Remote Resolution** — 30–40% of breakdowns resolved during the video
  triage session, no truck roll.
- **Pre-dispatch spare-parts guarantee** — when a visit is mandatory, the technician
  arrives with the exact component identified on video (e.g. *AC run capacitor 45µF*),
  eliminating second visits.
- **Dual-OTP anti-fraud lifecycle** — cryptographically validated OTP state transitions
  stop contractor fraud (false job starts/completions).
- **Automated inspection monetization** — diagnostic recordings + AI summaries compile into
  billable warranty inspection reports.

---

## 2. System Architecture

```
[ React 19 Frontend (Vite) ]
  |-- Web Audio API (16kHz PCM binary mic stream)
  |-- WebRTC PeerConnection + interactive HTML5 Canvas annotation layer
  \-- Video.js player (HTTP 206 byte-range scrubbable VOD & HLS)
                           |
                           v  (high-concurrency async ASGI gateway)
[ FastAPI Core Gateway (Python 3.12) ]
  |-- /ws/audio/triage    binary audio ingestion & STT/LLM/TTS pipeline
  |-- /ws/video/signal    WebRTC SDP offer/answer & ICE candidate exchange
  |-- /ws/canvas/sync     bi-directional normalised X/Y annotation broadcast
  |-- /api/v1/videos/stream   HTTP 206 partial content video streaming
  \-- /api/v1/dispatch    PostGIS spatial KNN match & OTP state machine
                           |
       +-------------------+-------------------+
       v                                       v
[ PostgreSQL 16 + PostGIS ]           [ Redis Cluster ]
  |-- users, technician_profiles (spatial)   |-- pub/sub (signaling, canvas sync)
  |-- diagnostic_sessions & dispatches       \-- distributed locks (5-min hold)
  \-- Alembic schema migrations                     |
                                                    v
                                       [ Celery Distributed Workers ]
                                         |-- FFmpeg HLS multi-bitrate transcoder
                                         |-- WeasyPrint inspection PDF engine
                                         \-- weekly 15% platform payout settler
                                                    |
                                                    v
                                       [ MinIO / S3 Object Storage ]
                                         |-- .m3u8 playlists & .ts segments
                                         \-- PDF invoices & diagnostic snapshots
```

### Component matrix

| Component | Technology | Primary role |
|---|---|---|
| API gateway | FastAPI + Uvicorn | Async ASGI gateway; REST + WebSocket endpoints |
| Voice triage | Whisper (streaming STT), LLM function calling, Piper/ElevenLabs TTS | Speech → structured diagnosis → spoken reply < 500ms |
| Video room | WebRTC (P2P media), FastAPI signaling broker | SDP/ICE exchange, peer connection setup |
| Annotation sync | Redis Pub/Sub + WebSocket | Normalised coordinate broadcast, < 20ms |
| VOD streaming | FastAPI `StreamingResponse` (HTTP 206) | Byte-range partial content, zero RAM bloat |
| Media transcode | Celery + FFmpeg | Adaptive bitrate HLS (1080/720/480) |
| Reporting | Celery + WeasyPrint | Inspection PDF / invoice generation |
| Data store | PostgreSQL 16 + PostGIS | Relational + spatial (GIST index, EPSG:4326) |
| Cache / locks | Redis | Pub/sub relay, distributed 5-min dispatch lock |
| Object storage | MinIO / S3 | HLS segments, PDFs, snapshots |
| Frontend | React 19 + Vite | Audio widget, WebRTC room, canvas, player |
| Containerization | Docker & Docker Compose | Multi-service orchestration |

---

## 3. Core Features & Deep Technical Concepts

### Feature 1 — Sub-500ms Voice AI Triage (binary WebSockets)

**Interaction:** customer taps mic and says *"Mera AC cooling nahi kar raha aur compressor
se rattling sound aa rahi hai."*

**Ingestion:**
- Browser captures audio via `AudioContext` + `AudioWorklet`, downsamples to 16kHz mono
  16-bit PCM.
- Packets stream as raw binary chunks over `/ws/audio/triage` — no base64, no per-chunk
  string serialization on the event loop.

**Async pipeline:**
1. **Streaming STT** — audio chunks route into a streaming Whisper instance.
2. **LLM function calling** — transcript passes to a low-latency LLM with function-calling
   schemas, extracting `{appliance_type: AC, suspected_issue: compressor_rattle,
   urgency: HIGH}`.
3. **Streaming TTS** — diagnostic text streams through Piper/ElevenLabs, synthesized PCM
   chunks returned to the client in under 500ms.

**Why raw binary, not base64 JSON:** base64 adds ~33% bandwidth and forces string
encode/decode on both browser and server event loop every ~100ms. Raw `ArrayBuffer` bytes
keep memory allocations optimal and pass straight to native Whisper bindings.

### Feature 2 — Interactive Video Diagnostic Room (WebRTC + live canvas sync)

**Interaction:** customer points phone camera at the appliance; the remote engineer draws
arrows/circles around valves, terminals, or error codes on the live video.

- **Signaling gateway:** FastAPI is an async broker routing `offer`, `answer`,
  `ice_candidate` messages over WebSockets. Media itself is peer-to-peer.
- **Coordinate normalization** — to keep draw accuracy across a 4K monitor vs a 1080p
  phone, coordinates are normalized to `[0.0, 1.0]`:

  ```
  X_norm = X_pixel / CanvasWidth
  Y_norm = Y_pixel / CanvasHeight
  ```

- **Real-time broadcast** — coordinates fan out over Redis Pub/Sub with < 20ms latency and
  re-render on the peer's canvas overlay.

### Feature 3 — HTTP 206 Partial Content & HLS video pipeline

- **Byte-range parser (HTTP 206)** — FastAPI parses `Range: bytes=start-end`, seeks the
  file pointer (`video_file.seek(start)`), and yields only the requested slice via
  `StreamingResponse` with status `206` and `Content-Range: bytes start-end/total`. No
  multi-GB file ever enters RAM; rapid scrubbing/seeking stays instant.
- **FFmpeg multi-bitrate HLS** — completed diagnostics are transcoded asynchronously by
  Celery into ABR HLS:
  - 1080p (4500 kbps)
  - 720p (2500 kbps)
  - 480p (1000 kbps)
  - `master.m3u8` + 4-second `.ts` segments saved to MinIO/S3.

### Feature 4 — PostGIS geospatial dispatch & Dual-OTP state machine

**Interaction:** if the issue can't be resolved remotely, the platform books the nearest
available technician within a 5km radius.

**K-Nearest-Neighbor spatial search** — PostGIS spherical geography with GIST indexing:

```sql
SELECT id, full_name,
       ST_Distance(current_location,
         ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326)::geography) AS distance_meters
FROM technician_profiles
WHERE is_available = TRUE
  AND ST_DWithin(current_location,
        ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326)::geography, 5000)
ORDER BY current_location <-> ST_SetSRID(ST_MakePoint(77.2090, 28.6139), 4326)::geometry
LIMIT 1;
```

**Why PostGIS beats a bounding-box query:** flat Euclidean math ignores Earth curvature and
needs a full-table scan `O(N)` when filters combine. PostGIS uses a GIST 2D R-Tree over
EPSG:4326 and evaluates KNN in `O(log N)`.

**Dual-OTP state machine:**

```
ASSIGNED  --(technician arrives, verifies start_otp)-->  IN_PROGRESS
IN_PROGRESS  --(service complete, verifies end_otp)-->  COMPLETED
```

A Redis distributed lock holds the assignment for 5 minutes so two dispatchers cannot claim
the same technician.

### Feature 5 — Celery async media, invoicing & payout pipeline

- **Inspection report** — on completion Celery compiles customer details, snapshot URLs,
  transcripts, replaced parts, and digital signatures into a formatted PDF (WeasyPrint).
- **Commission split (15% cut):**

  ```
  platform_commission = invoice_amount * 0.15
  technician_payout    = invoice_amount * 0.85 - TDS (1%)
  ```

- Ledger balances maintained for automated weekly batch settlement.

---

## 4. Production Database Schema (PostgreSQL 16 + PostGIS)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Core users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('CUSTOMER', 'TECHNICIAN', 'ADMIN')),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Technician profiles with spatial indexing
CREATE TABLE technician_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skills TEXT[] NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    current_location GEOMETRY(Point, 4326) NOT NULL,
    base_rating NUMERIC(3, 2) DEFAULT 5.00,
    wallet_balance NUMERIC(12, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_technician_location ON technician_profiles USING GIST(current_location);

-- 3. Tele-diagnostic sessions
CREATE TABLE diagnostic_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES users(id),
    technician_id UUID REFERENCES users(id),
    session_status VARCHAR(30) NOT NULL CHECK (session_status IN (
        'INITIATED', 'IN_PROGRESS', 'RESOLVED_REMOTELY', 'ESCALATED_TO_DISPATCH', 'TERMINATED')),
    raw_audio_url TEXT,
    voice_transcript TEXT,
    ai_structured_summary JSONB DEFAULT '{}'::jsonb,
    raw_recording_url TEXT,
    hls_master_playlist_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ
);

-- 4. Field service dispatches & OTP verification
CREATE TABLE service_dispatches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES diagnostic_sessions(id),
    customer_id UUID NOT NULL REFERENCES users(id),
    technician_id UUID NOT NULL REFERENCES users(id),
    customer_location GEOMETRY(Point, 4326) NOT NULL,
    dispatch_status VARCHAR(30) NOT NULL CHECK (dispatch_status IN (
        'PENDING', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    start_otp_hash VARCHAR(255) NOT NULL,
    end_otp_hash VARCHAR(255) NOT NULL,
    parts_replaced JSONB DEFAULT '[]'::jsonb,
    total_service_fee NUMERIC(10, 2) DEFAULT 0.00,
    platform_commission_fee NUMERIC(10, 2) DEFAULT 0.00,
    technician_earnings NUMERIC(10, 2) DEFAULT 0.00,
    invoice_pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_dispatch_location ON service_dispatches USING GIST(customer_location);
```

---

## 5. Target Project File Structure

```
diagnoz/
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/{auth,sessions,streaming,dispatch}.py
│   │   │   └── router.py
│   │   ├── core/{config,database,security}.py
│   │   ├── models/{user,session,dispatch}.py
│   │   ├── schemas/{user,session,dispatch}.py
│   │   ├── services/{whisper_client,llm_triage,tts_client,spatial_matcher}.py
│   │   ├── websockets/{audio_triage,webrtc_signaling,canvas_sync}.py
│   │   └── main.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks/{media_transcode,report_generate,payout_settle}.py
│   ├── alembic/ · alembic.ini
│   ├── Dockerfile · requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/{AudioTriageWidget,WebRTCVideoRoom,AnnotationCanvas,VideoPlayer}.jsx
│   │   ├── hooks/{useAudioRecorder,useWebRTC,useWebSocket}.js
│   │   ├── pages/{CustomerRoom,TechnicianConsole,DispatchTracker}.jsx
│   │   ├── App.jsx · main.jsx
│   ├── package.json · tailwind.config.js · vite.config.js
├── docker-compose.yml · .gitignore · README.md
```

> Note: the current repo scaffold is a subset of the above; files are added phase by phase
> per [ROADMAP.md](ROADMAP.md).

---

## 6. Reference Implementation Snippets

### A. HTTP 206 byte-range VOD streaming — `backend/app/api/v1/endpoints/streaming.py`

```python
import os
from pathlib import Path
from typing import Generator
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

router = APIRouter()
VIDEO_STORAGE_PATH = Path("/var/storage/diagnoz/reference_videos")

def file_byte_range_generator(file_path: Path, start: int, chunk_size: int) -> Generator[bytes, None, None]:
    with open(file_path, "rb") as video_file:
        video_file.seek(start)
        remaining = chunk_size
        while remaining > 0:
            data = video_file.read(min(remaining, 64 * 1024))  # 64KB chunks
            if not data:
                break
            remaining -= len(data)
            yield data

@router.get("/stream/{video_id}")
async def stream_reference_video(video_id: str, range: str = Header(None)):
    file_path = VIDEO_STORAGE_PATH / f"{video_id}.mp4"
    if not file_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video file not found")

    file_size = os.path.getsize(file_path)
    if range is None:
        return StreamingResponse(
            file_byte_range_generator(file_path, 0, file_size),
            media_type="video/mp4",
            headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"},
        )

    range_value = range.strip().lower().replace("bytes=", "")
    start_s, _, end_s = range_value.partition("-")
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1

    if start >= file_size or end >= file_size:
        raise HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            "Requested Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_length = (end - start) + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(
        file_byte_range_generator(file_path, start, chunk_length),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
```

### B. Binary audio ingestion & live AI triage — `backend/app/websockets/audio_triage.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.whisper_client import transcribe_audio_chunk
from app.services.llm_triage import analyze_appliance_issue
from app.services.tts_client import synthesize_speech_stream

router = APIRouter()

@router.websocket("/ws/audio/triage/{session_id}")
async def audio_triage_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    audio_buffer = bytearray()
    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes"):
                audio_buffer.extend(message["bytes"])
                # ~1.5s of audio at 16kHz 16-bit mono = 48,000 bytes
                if len(audio_buffer) >= 48000:
                    current_pcm = bytes(audio_buffer)
                    audio_buffer.clear()
                    partial = await transcribe_audio_chunk(current_pcm)
                    if partial.strip():
                        await websocket.send_json({"type": "TRANSCRIPT_CHUNK", "text": partial})

            elif message.get("text"):
                # customer finished speaking -> run diagnosis
                diagnosis = await analyze_appliance_issue(message["text"])
                await websocket.send_json({"type": "DIAGNOSIS_COMPLETE", "payload": diagnosis})
                async for audio_packet in synthesize_speech_stream(diagnosis["voice_summary"]):
                    await websocket.send_bytes(audio_packet)
    except WebSocketDisconnect:
        pass
```

### C. Live canvas annotation sync — `backend/app/websockets/canvas_sync.py`

```python
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

router = APIRouter()
redis_client = aioredis.from_url("redis://redis:6379/0", decode_responses=True)

@router.websocket("/ws/canvas/sync/{session_id}")
async def canvas_sync_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    channel = f"canvas_sync:{session_id}"
    await pubsub.subscribe(channel)

    async def redis_listener():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except Exception:
            pass

    listener_task = asyncio.create_task(redis_listener())
    try:
        while True:
            # {"action": "DRAW", "norm_x": 0.452, "norm_y": 0.781, "color": "#FF0000"}
            raw_data = await websocket.receive_text()
            await redis_client.publish(channel, raw_data)
    except WebSocketDisconnect:
        listener_task.cancel()
        await pubsub.unsubscribe(channel)
```

### D. Celery FFmpeg multi-bitrate HLS transcoder — `backend/workers/tasks/media_transcode.py`

```python
import subprocess
from pathlib import Path
from workers.celery_app import celery_app

@celery_app.task(name="tasks.transcode_to_hls", bind=True, max_retries=3)
def transcode_recording_to_hls(self, session_id: str, raw_video_path: str, output_dir: str):
    raw_path = Path(raw_video_path)
    out_path = Path(output_dir) / session_id
    out_path.mkdir(parents=True, exist_ok=True)
    master_playlist_path = out_path / "master.m3u8"

    ffmpeg_command = [
        "ffmpeg", "-y", "-i", str(raw_path),
        "-vf", "scale=w=1920:h=1080", "-c:v:0", "libx264", "-b:v:0", "4500k",
        "-maxrate:v:0", "4800k", "-bufsize:v:0", "9000k",
        "-vf", "scale=w=1280:h=720", "-c:v:1", "libx264", "-b:v:1", "2500k",
        "-maxrate:v:1", "2700k", "-bufsize:v:1", "5000k",
        "-vf", "scale=w=854:h=480", "-c:v:2", "libx264", "-b:v:2", "1000k",
        "-maxrate:v:2", "1100k", "-bufsize:v:2", "2000k",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "hls", "-hls_time", "4", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(out_path / "segment_%v_%03d.ts"),
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", "v:0,a:0 v:1,a:1 v:2,a:2",
        str(out_path / "stream_%v.m3u8"),
    ]
    try:
        subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"status": "SUCCESS", "master_playlist": str(master_playlist_path)}
    except subprocess.CalledProcessError as err:
        self.retry(exc=err, countdown=10)
```

---

## 7. Containerization & Deployment Model

Multi-service Docker Compose:

- **backend** — Python 3.12-slim, FastAPI + Uvicorn, ASGI.
- **worker** — same image, `celery -A workers.celery_app worker`.
- **db** — `postgis/postgis:16-3.4`.
- **redis** — pub/sub relay, distributed locks, Celery broker.
- **minio** — S3-compatible object storage for HLS output, PDFs, snapshots.
- **frontend** — multi-stage Node build served by Nginx with `/api/` + `/ws/` proxy.

Single command: `docker compose up --build`.

---

## 8. Future Extensions

| Phase | Enhancement | Technical impact |
|---|---|---|
| Phase 6 | TURN/coturn server | Reliable WebRTC through symmetric NATs / corporate firewalls |
| Phase 7 | Horizontal WS scaling | Redis-backed connection registry so any pod can route signaling |
| Phase 8 | Evaluation harness | Measure triage accuracy, remote-resolution rate, dispatch precision |
| Phase 9 | Multi-tenant isolation | Per-service-company schemas, row-level security, separate ledgers |
