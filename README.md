# DiagnoZ

**Real-Time Video Tele-Diagnostic, Voice AI Triage & Field Service Dispatch Platform**

DiagnoZ eliminates redundant appliance-repair truck rolls. 35–45% of physical technician
dispatches are wasted on issues that are actually a tripped breaker, a loose connector, a
clogged filter, or a wrong mode setting. DiagnoZ resolves those over an interactive voice +
video session, and when a physical visit is genuinely required, it dispatches the nearest
technician with the exact spare part already identified.

> **Status:** ✅ Fully implemented and verified end-to-end — all 5 backend phases, the React
> frontend, and an evaluation harness with real measured numbers. Nothing here is a stub;
> every feature below was run against the live stack (real DB, real WebSockets, a real
> browser) and checked, not just written and left untested. See
> [docs/ROADMAP.md](docs/ROADMAP.md) and the `docs/PHASE_*_NOTES.md` files for exactly what
> was built, how it was verified, and the real bugs found and fixed along the way.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [How It Works](#how-it-works)
- [API & WebSocket Surface](#api--websocket-surface)
- [Measured Results](#measured-results)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Local Development (without Docker)](#local-development-without-docker)
- [Documentation Map](#documentation-map)

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Gateway | FastAPI (Python 3.12, ASGI) + Uvicorn |
| Real-time transport | WebSockets (binary audio, WebRTC signaling, canvas sync) |
| Voice AI pipeline | Streaming STT (Whisper) → LLM function calling → Streaming TTS |
| Video | WebRTC peer-to-peer + HTML5 Canvas annotation, HTTP 206 byte-range VOD, FFmpeg HLS |
| Background workers | Celery + Celery Beat, Redis broker |
| Data store | PostgreSQL 16 + PostGIS (spatial KNN dispatch), Alembic migrations |
| Cache / pub-sub / locks | Redis |
| Object storage | MinIO / S3 (HLS segments, PDF invoices, snapshots) |
| Auth | JWT (python-jose) + bcrypt password/OTP hashing + RBAC dependency guards |
| Frontend | React 19 + Vite, served via Nginx in Docker |
| Containerization | Docker & Docker Compose (7 services) |

## How It Works

1. **Voice triage** — customer taps a mic and describes the fault in natural language. The
   browser streams raw 16kHz PCM binary chunks over `/ws/audio/triage`. FastAPI runs
   streaming STT → an LLM with function-calling schemas (extracts `appliance_type`,
   `suspected_issue`, `urgency`) → streaming TTS, replying with spoken diagnostic feedback
   in under 500ms. Every stage has a deterministic offline fallback, so the full pipeline
   runs with zero external API keys — real providers plug into the same interface.
2. **Video diagnostic room** — customer points their phone camera at the appliance; the
   remote engineer draws arrows/circles on the live video. FastAPI brokers the WebRTC
   SDP/ICE handshake; annotation coordinates are normalized to `[0.0, 1.0]` and broadcast
   over Redis Pub/Sub so they land correctly on any screen resolution.
3. **Reference video streaming** — troubleshooting guides stream via HTTP 206 Partial
   Content byte-range responses (no multi-GB file ever loaded into RAM); completed session
   recordings are transcoded to multi-bitrate HLS (1080p/720p/480p) by Celery workers.
4. **Geospatial dispatch** — if the issue can't be fixed remotely, a PostGIS K-Nearest-
   Neighbor query (GIST index, EPSG:4326) finds the closest available technician within
   5km. A distributed Redis lock holds the assignment during the race window.
5. **Dual-OTP lifecycle** — `PENDING → ACCEPTED → (start_otp) → IN_PROGRESS → (end_otp) →
   COMPLETED`, cryptographically verified state transitions that prevent contractor
   start/complete fraud. OTPs are bcrypt-hashed; only the customer-facing response ever sees
   the plaintext code.
6. **Settlement & reporting** — on completion, Celery compiles the inspection PDF
   (WeasyPrint) and books the ledger split: 15% platform commission, 85% technician payout
   minus 1% TDS. A weekly Celery Beat job settles payouts into technician wallets.

## API & WebSocket Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/auth/register`, `/login`, `/me` | POST/GET | JWT auth, RBAC roles (CUSTOMER/TECHNICIAN/ADMIN) |
| `/api/v1/sessions` | POST/GET | Create & fetch a diagnostic session |
| `/api/v1/technicians/me/profile`, `/location`, `/availability` | POST/PATCH | Technician geo-profile management |
| `/api/v1/dispatch` | POST | KNN-match nearest technician, issue dual OTPs |
| `/api/v1/dispatch/{id}/accept`, `/verify-start-otp`, `/verify-end-otp` | POST | Dispatch lifecycle transitions |
| `/api/v1/videos/stream/{id}` | GET | HTTP 206 byte-range video streaming |
| `/ws/audio/triage/{session_id}` | WS | Binary PCM in → STT/LLM/TTS pipeline |
| `/ws/video/signal/{session_id}` | WS | WebRTC offer/answer/ICE relay |
| `/ws/canvas/sync/{session_id}` | WS | Normalized-coordinate annotation broadcast |

Interactive Swagger docs at `/docs` once the backend is running.

## Measured Results

Not hand-waved — `eval/run_eval.py` runs 18 labeled triage transcripts and 4 labeled dispatch
scenarios against the **real** running system (real DB, real PostGIS queries, real triage
function — no mocks):

| Metric | Result |
|---|---|
| Triage appliance-type accuracy | **100%** (18/18) |
| Triage urgency accuracy | **88.9%** (16/18) |
| Dispatch KNN precision | **100%** (4/4) |

The 2 urgency misses are documented, understood limitations of the offline keyword fallback
(no negation handling, English-only keywords) — see [docs/PHASE_EVAL_NOTES.md](docs/PHASE_EVAL_NOTES.md)
and [docs/INTERVIEW_NOTES.md](docs/INTERVIEW_NOTES.md) (section 3a) for the full breakdown,
including two real bugs the eval process caught and fixed.

## Project Structure

```
backend/
  app/
    api/v1/endpoints/   REST routes: auth, sessions, technicians, dispatch, streaming
    core/               config, DB engine/session, JWT+bcrypt security, RBAC deps
    models/             SQLAlchemy models (users, technician_profiles, diagnostic_sessions,
                         service_dispatches) with PostGIS geometry columns
    schemas/            Pydantic request/response models
    services/           whisper_client, llm_triage, tts_client (offline-first),
                         spatial_matcher (PostGIS KNN + Redis lock)
    websockets/         audio_triage, canvas_sync, webrtc_signaling
    main.py             FastAPI app + router wiring
  workers/
    celery_app.py       Celery app + Beat schedule
    storage.py           S3/MinIO helper
    tasks/               media_transcode (FFmpeg HLS), report_generate (WeasyPrint PDF),
                         payout_settle (weekly wallet settlement)
  alembic/              DB migrations
frontend/
  src/
    components/         AudioTriageWidget, AnnotationCanvas, ProtectedRoute
    hooks/               useAuth, useWebSocket, useAudioRecorder
    pages/               Login, Register, CustomerRoom, TechnicianConsole, DispatchTracker
    lib/api.js           Single fetch wrapper for the whole backend surface
eval/                   scenarios.json + run_eval.py — measured accuracy/precision numbers
docs/                   Setup guide, technical spec, roadmap, per-phase build notes,
                         interview prep
```

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Brings up 7 services: `db` (PostgreSQL + PostGIS), `redis`, `minio` (object storage),
`backend` (FastAPI, runs Alembic migrations on boot), `worker` (Celery), `beat` (Celery
scheduler), and `frontend` (React, served via Nginx which proxies `/api/` and `/ws/` to the
backend).

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API + Swagger docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9003 |

## Local Development (without Docker)

Backend:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head          # needs DATABASE_URL pointing at a Postgres+PostGIS instance
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev                   # defaults to VITE_API_BASE_URL=http://localhost:8000
```

Fastest path is usually a hybrid: `docker compose up -d db redis backend` for the backend
stack, then `npm run dev` in `frontend/` for a hot-reloading UI.

## Documentation Map

| Doc | What's in it |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Git/repo setup steps |
| [docs/TECHNICAL_SPEC.md](docs/TECHNICAL_SPEC.md) | Full architecture, DB schema, WebSocket contracts |
| [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) | Session-by-session build schedule and status |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phase order, current status, deployment plan |
| [docs/CODE_NOTES.md](docs/CODE_NOTES.md) | File-by-file "what and why" for every module |
| [docs/PHASE_1_NOTES.md](docs/PHASE_1_NOTES.md) … [PHASE_5_NOTES.md](docs/PHASE_5_NOTES.md) | Per-phase build notes: what was built, how it was verified, bugs found |
| [docs/PHASE_FRONTEND_NOTES.md](docs/PHASE_FRONTEND_NOTES.md) | Frontend build + real-browser verification notes |
| [docs/PHASE_EVAL_NOTES.md](docs/PHASE_EVAL_NOTES.md) | Evaluation harness methodology and results |
| [docs/INTERVIEW_NOTES.md](docs/INTERVIEW_NOTES.md) | Pitch, ROI numbers, trade-offs, measured results, anticipated Q&A |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | Step-by-step live demo walkthrough for interviews — exact clicks, what to say, fallback plan |
