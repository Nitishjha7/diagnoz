# Code Notes — Kya Kis Liye Hai

Ye file har file / dependency ka **kaam aur reason** track karti hai, taaki baad me (ya
interview me) yaad rahe ki har cheez kyun li gayi. Jaise-jaise code likha jayega, isko
update karte rahenge. Abhi zyada files khaali hai — ye "planned intent" note hai.

---

## backend/requirements.txt (planned)

| Package | Kya kaam karta hai | Kyun liya |
|---|---|---|
| `fastapi` | ASGI web framework — REST + WebSocket endpoints | Async-native, WebSocket first-class support, auto `/docs`. Poore project ka gateway isi pe hai |
| `uvicorn[standard]` | ASGI server jo FastAPI app run karta hai | FastAPI khud server nahi hai. `[standard]` me `websockets` + `httptools` aate hain jo WS/HTTP perf ke liye chahiye |
| `websockets` | Low-level WS protocol implementation | Uvicorn isi ke through binary frames handle karta hai (audio PCM chunks) |
| `sqlalchemy` | ORM / SQL toolkit | Postgres models + query execution. Async engine use karenge (`asyncpg`) |
| `asyncpg` | Async PostgreSQL driver | FastAPI async hai — sync `psycopg2` event loop block kar deta. `asyncpg` fast + non-blocking |
| `geoalchemy2` | SQLAlchemy ke liye PostGIS spatial types | `GEOMETRY(Point, 4326)` columns ko Python me map karne ke liye. Raw SQL likhe bina spatial queries |
| `alembic` | DB migration tool | Schema versioning — `postgis` extension enable, GIST index create sab migration me |
| `redis` | Redis client (async: `redis.asyncio`) | Canvas sync Pub/Sub, WebRTC signaling relay, dispatch distributed lock, Celery broker |
| `celery` | Distributed task queue | Long-running kaam (FFmpeg transcode, PDF gen, payout batch) request cycle se bahar |
| `pydantic` / `pydantic-settings` | Validation + typed config | Request/response models; `.env` se typed settings load |
| `python-jose[cryptography]` | JWT encode/decode | Auth token issuance + verification |
| `passlib[bcrypt]` | Password + OTP hashing | `hashed_password`, `start_otp_hash`, `end_otp_hash` — kabhi plain store nahi |
| `python-multipart` | Form/file upload parsing | Video recording upload endpoint ke liye |
| `weasyprint` | HTML → PDF | Inspection report / invoice generation (Celery task) |
| `boto3` | S3 client | MinIO / S3 pe HLS segments, PDF, snapshots upload |
| `openai-whisper` / `faster-whisper` | Streaming STT | Audio chunk → transcript. `faster-whisper` (CTranslate2) low-latency ke liye better |
| `httpx` | Async HTTP client | LLM / TTS API calls (async, event loop friendly) |

FFmpeg khud OS package hai (`apt install ffmpeg`) — pip package nahi. Dockerfile me install
hoga.

---

## backend/app/main.py

FastAPI app ka entrypoint — HTTP + WebSocket routers wire karta hai, koi business logic nahi.

- `include_router()` se `api/v1/router.py` (REST) aur `websockets/*` (WS) mount honge.
- `@app.on_event("startup")` — DB engine warm-up, Redis connection pool init.
- CORS middleware — abhi dev me `allow_origins=["*"]`, production me frontend domain tak
  restrict. Note kar liya.
- `/health` — Docker healthcheck ping.

---

## backend/app/websockets/audio_triage.py

**Project ka real-time core #1.** `/ws/audio/triage/{session_id}`.

- Browser raw 16kHz mono 16-bit PCM binary chunks bhejta hai (base64 nahi — 33% overhead
  aur string encode/decode bachta hai).
- `bytearray` buffer me accumulate; ~48,000 bytes (~1.5s) hone pe ek STT inference.
- Partial transcript `TRANSCRIPT_CHUNK` JSON se wapas (live caption feel).
- Jab client `text` frame bhejta hai (customer ne bolna khatam kiya) → full transcript LLM
  ko jaata hai **function-calling schema** ke saath → structured `{appliance_type,
  suspected_issue, urgency}` nikalta hai → `DIAGNOSIS_COMPLETE` JSON.
- Phir TTS stream: synthesized PCM `send_bytes()` se wapas, target < 500ms.

**Design choice:** `receive()` (generic) use kiya `receive_bytes()`/`receive_text()` ke
bajaye — kyunki ek hi socket pe dono aa sakte hain (audio binary + control text).

---

## backend/app/websockets/canvas_sync.py

**Real-time core #2.** `/ws/canvas/sync/{session_id}`. Live annotation overlay.

- Har session ka apna Redis channel: `canvas_sync:{session_id}`.
- Do kaam parallel: (1) `receive_text()` se incoming draw events lena aur Redis pe
  `publish` karna, (2) `pubsub.listen()` se channel ke messages lekar socket pe `send_text`.
- Dusra kaam ek background `asyncio.Task` me chalta hai (`redis_listener`), disconnect pe
  `cancel`.
- Coordinates normalized `[0.0, 1.0]` aate hain (`norm_x`, `norm_y`) — client apni canvas
  width/height se multiply karke actual pixel nikalta hai. Isliye 4K aur 1080p dono pe
  arrow sahi jagah dikhta hai.

**Kyun Redis Pub/Sub, in-memory dict nahi:** multi-pod deploy me alag pod pe alag peer ho
sakta hai — Redis se sab pods ko broadcast milta hai. Single source of truth.

---

## backend/app/websockets/webrtc_signaling.py (planned)

`/ws/video/signal/{session_id}`. FastAPI sirf **signaling broker** hai — actual video/audio
media WebRTC se peer-to-peer jaata hai, server se nahi (bandwidth bachta hai).

- `offer` / `answer` / `ice_candidate` messages ko session ke dusre peer tak route karta
  hai (Redis Pub/Sub se, canvas_sync jaisa hi pattern).
- Production me TURN server (coturn) chahiye jab dono peer strict NAT ke peeche ho.

---

## backend/app/api/v1/endpoints/streaming.py

HTTP 206 Partial Content byte-range VOD engine — reference troubleshooting videos serve
karne ke liye, poori file RAM me load kiye bina.

- `Range: bytes=start-end` header parse karta hai.
- `file.seek(start)` + generator jo 64KB chunks yield karta hai → `StreamingResponse` with
  status `206` aur `Content-Range` header.
- Range invalid (start/end >= file_size) → `416 Requested Range Not Satisfiable`.
- Range absent → poori file stream (status 200) with `Accept-Ranges: bytes`.

**Interview point:** scrubbing/seeking pe browser naya `Range` request bhejta hai; hum sirf
requested slice disk se padhte hain — disk saturation aur memory bloat dono avoid.

---

## backend/app/api/v1/endpoints/dispatch.py

Geospatial dispatch + Dual-OTP state machine.

- **KNN match:** PostGIS query — `is_available = TRUE` + `ST_DWithin(..., 5000)` (5km
  filter, GIST index use hota hai) + `ORDER BY current_location <-> point` (KNN operator,
  index-assisted nearest neighbor) + `LIMIT 1`.
- **Distributed lock:** match hone pe Redis `SET lock:technician:{id} NX EX 300` — 5 min ke
  liye technician hold, taaki do dispatcher ek hi banda claim na karein.
- **OTP:** `start_otp` aur `end_otp` generate, customer ko bhejo, hash DB me
  (`passlib.bcrypt`). Technician arrival pe `start_otp` verify → `IN_PROGRESS`. Kaam khatam
  pe `end_otp` verify → `COMPLETED`. Har transition atomic (DB transaction + status CHECK).

**Kyun hash:** DB leak ho jaye to bhi OTP se koi job hijack na kar sake.

---

## backend/workers/celery_app.py

Celery instance config — broker `redis://redis:6379/1`, result backend `/2`. Task
autodiscovery `workers.tasks.*` se. `worker` container isi ko `celery -A` se run karta hai.

---

## backend/workers/tasks/media_transcode.py

`tasks.transcode_to_hls` — session recording ko FFmpeg se ABR HLS me convert karta hai.

- Ek FFmpeg command me teen rendition: 1080p (4500k), 720p (2500k), 480p (1000k).
- `-var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2"` — har video stream ke saath audio pair.
- `-hls_time 4` — 4-second `.ts` segments; `master.m3u8` + `stream_%v.m3u8` playlists.
- Output MinIO/S3 pe upload, `hls_master_playlist_url` session row me save.
- `bind=True, max_retries=3` — FFmpeg fail (corrupt input) pe `self.retry(countdown=10)`.

**Kyun Celery, request ke andar nahi:** transcode minutes le sakta hai — HTTP request
timeout ho jaayega aur worker block hoga. Async offload + retry + progress tracking.

---

## backend/workers/tasks/report_generate.py (planned)

`tasks.generate_report` — WeasyPrint se inspection PDF. Customer details + snapshot URLs +
transcript + `parts_replaced` + digital signature → HTML template → PDF → S3 →
`invoice_pdf_url`.

---

## backend/workers/tasks/payout_settle.py (planned)

`tasks.settle_payouts` — weekly Celery beat schedule. Har `COMPLETED` dispatch pe:
`platform_commission = total * 0.15`, `technician_earnings = total * 0.85 - TDS(total*0.01)`.
Technician `wallet_balance` update, ledger entry.

---

## backend/Dockerfile

1. `python:3.12-slim` base.
2. `apt-get install ffmpeg` + WeasyPrint ki system deps (`libpango`, `libcairo`, `libgdk-pixbuf`).
3. `requirements.txt` pehle copy + install (layer caching).
4. `app/` + `workers/` copy.
5. `uvicorn app.main:app --host 0.0.0.0 --port 8000` (worker container CMD override karta hai).

---

## docker-compose.yml (planned services)

| Service | Image | Kaam |
|---|---|---|
| `db` | `postgis/postgis:16-3.4` | Relational + spatial store |
| `redis` | `redis:7-alpine` | Pub/sub, locks, Celery broker |
| `minio` | `minio/minio` | S3-compatible object storage |
| `backend` | build `./backend` | FastAPI gateway |
| `worker` | build `./backend` | `celery -A workers.celery_app worker` |
| `frontend` | build `./frontend` | React build served by Nginx (`/api/` + `/ws/` proxy) |

---

## .env.example

Real secrets (`.env`) `.gitignore` me hai. `.env.example` sirf template hai — batata hai
konse vars chahiye (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `LLM_API_KEY`,
`TTS_API_KEY`, `S3_*`) bina real values leak kiye.

---

## Aage jo bhi file banegi, uska explanation yahin niche add hoga.
