# DiagnoZ — Real-Time Video Tele-Diagnostic, Voice AI Triage & Field Service Dispatch Platform

DiagnoZ eliminates redundant appliance-repair truck rolls. 35–45% of physical technician
dispatches are wasted on issues that are actually a tripped breaker, a loose connector, a
clogged filter, or a wrong mode setting. DiagnoZ resolves those over an interactive voice +
video session, and when a physical visit is genuinely required, it dispatches the nearest
technician with the exact spare part already identified.

## Tech Stack

| Layer | Technology |
|---|---|
| API Gateway | FastAPI (Python 3.12, ASGI) + Uvicorn |
| Real-time transport | WebSockets (binary audio, WebRTC signaling, canvas sync) |
| Voice AI pipeline | Streaming STT (Whisper) → LLM function calling → Streaming TTS |
| Video | WebRTC peer-to-peer + HTML5 Canvas annotation, HTTP 206 byte-range VOD, FFmpeg HLS |
| Background workers | Celery + Redis broker |
| Data store | PostgreSQL 16 + PostGIS (spatial KNN dispatch) |
| Cache / pub-sub / locks | Redis |
| Object storage | MinIO / S3 (HLS segments, PDF invoices, snapshots) |
| Frontend | React 19 + Vite |
| Containerization | Docker & Docker Compose |

## How it works

1. **Voice triage** — customer taps a mic and describes the fault in natural language. The
   browser streams raw 16kHz PCM binary chunks over `/ws/audio/triage`. FastAPI runs
   streaming STT → an LLM with function-calling schemas (extracts `appliance_type`,
   `suspected_issue`, `urgency`) → streaming TTS, replying with spoken diagnostic feedback
   in under 500ms.
2. **Video diagnostic room** — customer points their phone camera at the appliance; the
   remote engineer draws arrows/circles on the live video. FastAPI brokers the WebRTC
   SDP/ICE handshake; annotation coordinates are normalized to `[0.0, 1.0]` and broadcast
   over Redis Pub/Sub so they land correctly on any screen resolution.
3. **Reference video streaming** — troubleshooting guides stream via HTTP 206 Partial
   Content byte-range responses (no multi-GB file ever loaded into RAM); completed session
   recordings are transcoded to multi-bitrate HLS by Celery workers.
4. **Geospatial dispatch** — if the issue can't be fixed remotely, a PostGIS K-Nearest-
   Neighbor query (GIST index, EPSG:4326) finds the closest available technician within
   5km. A distributed Redis lock holds the assignment for 5 minutes.
5. **Dual-OTP lifecycle** — `ASSIGNED → (start_otp) → IN_PROGRESS → (end_otp) → COMPLETED`,
   cryptographically verified state transitions that prevent contractor start/complete fraud.
6. **Settlement & reporting** — on completion, Celery compiles the inspection PDF
   (WeasyPrint) and books the ledger split: 15% platform commission, 85% technician payout
   minus 1% TDS. Weekly batch settlement.

See [docs/TECHNICAL_SPEC.md](docs/TECHNICAL_SPEC.md) for the full architecture, database
schema, WebSocket contracts, and implementation detail.

## Project Structure

```
backend/    FastAPI gateway, WebSocket handlers, Celery workers
frontend/   React 19 + Vite client (audio widget, WebRTC room, annotation canvas, player)
docs/       Setup guide, technical spec, roadmap, code notes
```

## Setup

See [docs/SETUP.md](docs/SETUP.md) for git/repo setup steps.

```bash
docker compose up --build
```

Brings up: `db` (PostgreSQL + PostGIS), `redis`, `backend` (FastAPI), `worker` (Celery),
`minio` (object storage), and `frontend` (React via Nginx).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Short version:

- **Phase 1** — DB models + PostGIS spatial indexes + JWT/RBAC auth
- **Phase 2** — Binary audio AI triage (STT → LLM function calling → TTS)
- **Phase 3** — WebRTC signaling + live canvas sync + HTTP 206 video engine
- **Phase 4** — PostGIS KNN dispatch + Dual-OTP state machine
- **Phase 5** — Celery media/invoicing pipeline (HLS transcode, WeasyPrint PDF, payouts)
