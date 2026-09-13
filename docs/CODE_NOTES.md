# Code Notes — Kya Kis Liye Hai

Ye file har file / dependency ka **kaam aur reason** track karti hai, taaki baad me (ya
interview me) yaad rahe ki har cheez kyun li gayi. Jaise-jaise code likha jayega, isko
update karte rahenge.

**Status:** Backend (Phase 1–5) aur Frontend (React 19 + Vite) dono complete + verified hain.
Detail [PHASE_1_NOTES.md](PHASE_1_NOTES.md), [PHASE_2_NOTES.md](PHASE_2_NOTES.md),
[PHASE_3_NOTES.md](PHASE_3_NOTES.md), [PHASE_4_NOTES.md](PHASE_4_NOTES.md),
[PHASE_5_NOTES.md](PHASE_5_NOTES.md), aur [PHASE_FRONTEND_NOTES.md](PHASE_FRONTEND_NOTES.md)
me. Baaki sirf evaluation script + INTERVIEW_NOTES me real numbers.

---

## backend/requirements.txt

| Package | Kya kaam karta hai | Kyun liya |
|---|---|---|
| `fastapi` | ASGI web framework — REST + WebSocket endpoints | Async-native, WebSocket first-class support, auto `/docs`. Poore project ka gateway isi pe hai |
| `uvicorn[standard]` | ASGI server jo FastAPI app run karta hai | FastAPI khud server nahi hai. `[standard]` me `websockets` + `httptools` aate hain jo WS/HTTP perf ke liye chahiye |
| `sqlalchemy` | ORM / SQL toolkit | Postgres models + query execution |
| `psycopg2-binary` | Sync PostgreSQL driver | Phase 1 me sync SQLAlchemy engine use kiya (simplicity + Alembic ka sync support seedha kaam karta hai). Async `asyncpg` baad me perf-critical path pe consider karenge |
| `geoalchemy2` | SQLAlchemy ke liye PostGIS spatial types | `GEOMETRY(Point, 4326)` columns ko Python me map karne ke liye. Raw SQL likhe bina spatial queries |
| `alembic` | DB migration tool | Schema versioning — `postgis` extension enable, GIST index create sab migration me |
| `redis` | Redis client (async: `redis.asyncio`) | Canvas sync Pub/Sub, WebRTC signaling relay, dispatch distributed lock, Celery broker |
| `celery` | Distributed task queue | Long-running kaam (FFmpeg transcode, PDF gen, payout batch) request cycle se bahar |
| `pydantic` / `pydantic-settings` | Validation + typed config | Request/response models; `.env` se typed settings load |
| `email-validator` | `EmailStr` validation | Pydantic `EmailStr` ko internally isi ki zaroorat hai — na ho to import error |
| `python-jose[cryptography]` | JWT encode/decode | Auth token issuance + verification |
| `passlib[bcrypt]` | Password + OTP hashing | `hashed_password`, `start_otp_hash`, `end_otp_hash` — kabhi plain store nahi |
| `bcrypt==4.0.1` | Passlib ka bcrypt backend, pinned | `bcrypt` 5.x me passlib 1.7.4 ke saath incompatibility hai (`password cannot be longer than 72 bytes` error backend detection ke waqt hi aata hai) — 4.0.1 pe pin karna padha |
| `python-multipart` | Form/file upload parsing | OAuth2 password form (`/auth/login`) aur video upload endpoint ke liye |
| `shapely` | Python geometry objects (`Point`, etc.) | `geoalchemy2.shape.from_shape()` ko chahiye Python lat/lon se PostGIS geometry banane ke liye (technician location update, dispatch customer_location) |
| `boto3` | S3 client | MinIO pe HLS segments + PDF reports upload karne ke liye |
| `weasyprint` | HTML → PDF | Inspection report generation (Celery task) |
| `pydyf==0.10.0` | WeasyPrint ki PDF-writing dependency, pinned | Latest `pydyf` (0.12.1) weasyprint 62.3 ke saath breaking-incompatible hai — pin zaroori tha |

FFmpeg, WeasyPrint, boto3, faster-whisper, httpx — ye Phase 2/5 me add honge jab unki
zaroorat aayegi (abhi rakhna scope-creep hota).

---

## backend/app/main.py

FastAPI app ka entrypoint — HTTP + WebSocket routers wire karta hai, koi business logic nahi.

- `include_router(api_router, prefix="/api/v1")` — saare REST routes yahin se mount.
- `/health` — Docker healthcheck ping, `docker-compose.yml` isko poll nahi karta abhi (backend
  ka apna healthcheck nahi laga, sirf DB ka `depends_on: condition: service_healthy` hai) —
  manual curl se verify kiya.
- WebSocket routers (`audio_triage`, `canvas_sync`, `webrtc_signaling`) Phase 2/3 me yahan
  `include_router` honge — abhi wire nahi kiye kyunki unki file khaali hai.
- CORS middleware abhi nahi laga — frontend banne ke baad (Phase 4) add karenge jab actual
  origin pata chalega.

---

## backend/app/core/ (Phase 1 — naya)

Config, DB engine, aur security ka central jagah — TECHNICAL_SPEC ke "Target File Structure"
me `app/core/{config,database,security}.py` planned tha, wahi bana.

- **`config.py`** — `pydantic-settings.BaseSettings` se `.env` typed load hota hai
  (`DATABASE_URL`, `JWT_SECRET_KEY`, dispatch economics vars, sab yahin). Poore app me kahin
  bhi `os.getenv` nahi likha — sirf `from app.core.config import settings`.
- **`database.py`** — sync SQLAlchemy `engine` + `SessionLocal` + `Base` (naya
  `DeclarativeBase` style, SQLAlchemy 2.0). `get_db()` generator FastAPI `Depends` ke liye —
  request khatam hote hi session close.
- **`security.py`** — password hash/verify (`passlib.bcrypt`) + JWT create/decode
  (`python-jose`). OTP hashing bhi isi `hash_password`/`verify_password` se hoga (Phase 4) —
  alag function nahi banaya, same primitive kaafi hai.
- **`deps.py`** — `get_current_user` (token decode → DB se user fetch → `is_active` check) aur
  `require_roles(*roles)` factory jo RBAC guard deta hai. Endpoint pe
  `Depends(require_roles("ADMIN"))` laga do to sirf ADMIN role hi access kar payega — 403
  warna.

**Kyun `require_roles` factory pattern:** ek hi dependency function se saare role-combinations
cover ho jaate hain (`require_roles("TECHNICIAN", "ADMIN")` bhi likh sakte ho), alag-alag
`is_admin`/`is_technician` dependency nahi likhni padi.

---

## backend/app/models/ (Phase 1 — naya)

SQLAlchemy 2.0 `Mapped[]` style models, TECHNICAL_SPEC ke SQL schema (section 4) ka 1:1
Python mapping:

- **`user.py`** → `users` table. `role` plain `String(20)` + DB-level `CHECK` constraint
  (migration me), Python side `UserRole` enum sirf documentation/reference ke liye hai,
  column type khud enum nahi banaya (Postgres native enum migration me pain deta — string +
  CHECK simpler aur Alembic-friendly).
- **`technician.py`** → `technician_profiles`. `current_location` = `geoalchemy2.Geometry
  (geometry_type="POINT", srid=4326)` — yahi column Python object se PostGIS `GEOMETRY(Point,
  4326)` ban jaata hai.
- **`session.py`** → `diagnostic_sessions`. `ai_structured_summary` = `JSONB` — LLM ka
  structured triage output yahin store hoga.
- **`dispatch.py`** → `service_dispatches`. `current_location` jaisa hi geometry column
  `customer_location` pe.

**Kyun alag file per table, ek models.py nahi:** TECHNICAL_SPEC file structure me explicitly
`models/{user,session,dispatch}.py` diya tha — aur 4 tables ek file me daalna already
mushkil-to-navigate ho jaata.

---

## backend/app/schemas/user.py + api/v1/endpoints/auth.py (Phase 1 — naya)

Auth ka poora flow:

- **`UserRegister`** — Pydantic input model, `role` field `pattern="^(CUSTOMER|TECHNICIAN|
  ADMIN)$"` se hi restrict, DB tak galat role pahunchta hi nahi.
- **`POST /api/v1/auth/register`** — email/phone duplicate check → `hash_password` →
  `User` row insert → `UserOut` return (hashed_password kabhi response me nahi jaata,
  `UserOut` schema me wo field hi nahi hai).
- **`POST /api/v1/auth/login`** — `OAuth2PasswordRequestForm` (standard OAuth2 form:
  `username` + `password`) use kiya, taaki Swagger UI ka "Authorize" button seedha kaam
  kare aur ye FastAPI ka documented convention follow kare. `username` field me email jaata
  hai.
- **`GET /api/v1/auth/me`** — `Depends(get_current_user)` se protected, JWT/RBAC ka
  end-to-end proof — bina token 401, valid token pe current user.

`docker compose` me manually test kiya: register → login → token se `/me` call → 200; bina
token `/me` → 401. Sab pass.

---

## backend/alembic/ (Phase 1 — naya)

- **`env.py`** — `settings.DATABASE_URL` se `sqlalchemy.url` runtime pe set hota hai (alembic.ini
  me khaali chhoda), aur `app.models` se saare models import karke `Base.metadata` ko
  `target_metadata` diya — taaki `--autogenerate` future migrations me kaam kare.
- **`versions/0001_initial_schema.py`** — hand-written (autogenerate ke bajaye, kyunki local
  machine pe Python/venv setup nahi tha is session me) — lekin models se schema exactly match
  karta hai:
  - `CREATE EXTENSION postgis` + `pgcrypto`
  - 4 tables (`users`, `technician_profiles`, `diagnostic_sessions`, `service_dispatches`)
  - `CHECK` constraints role/status enums ke liye
  - `idx_technician_location` aur `idx_dispatch_location` — dono `GIST` index geometry
    columns pe (spatial KNN query Phase 4 me isi index se fast hogi)
- `docker-compose.yml` ka `backend` service startup pe `alembic upgrade head` khud chalata
  hai (`command: sh -c "alembic upgrade head && uvicorn ..."`) — matlab `docker compose up`
  ek hi command se DB migrate + app boot dono kar deta hai, alag se migration step yaad
  nahi rakhna padta.

**Verify kiya:** `docker exec` se `psql \dt` aur `\di` chala ke confirm kiya ki saare 4 table
+ dono GIST index ban chuke hain, aur `postgis_version()` 3.4 return kar raha hai.

---

## backend/app/services/ (Phase 2 — naya)

Provider-agnostic service layer — TECHNICAL_SPEC file structure me
`services/{whisper_client,llm_triage,tts_client}.py` planned tha, wahi bana. Har ek ka apna
**offline fallback** hai taaki bina kisi paid API key ke poora pipeline chal jaaye:

- **`whisper_client.py`** — `transcribe_audio_chunk()`. Abhi `audioop.rms()` se silence vs
  signal detect karke placeholder transcript deta hai. Real `faster-whisper` yahi function ke
  andar plug hoga — signature/contract change nahi hoga.
- **`llm_triage.py`** — `analyze_appliance_issue()`. Keyword-based extractor:
  `APPLIANCE_KEYWORDS` dict se appliance type, `URGENCY_KEYWORDS` se HIGH/MEDIUM/LOW. Real LLM
  function-calling ke liye `FUNCTION_SCHEMA` already defined hai, `settings.LLM_API_KEY` set
  hote hi wahan real API call jaayegi.
- **`tts_client.py`** — `synthesize_speech_stream()`. `TTS_API_KEY` na ho to synthetic 440Hz
  sine-wave PCM chunks generate karta hai — ye prove karta hai ki streaming/framing contract
  sahi hai, bina real voice model ke.

**Kyun stub-in-production, mock-in-tests nahi:** `docker compose up` se turant poora demo
chal jaata hai, koi API key maangta hi nahi. Jab real provider chahiye ho, sirf `if
settings.LLM_API_KEY:` branch ke andar call daalni hai.

---

## backend/app/websockets/audio_triage.py

**Project ka real-time core #1.** `/ws/audio/triage/{session_id}`.

- Browser raw 16kHz mono 16-bit PCM binary chunks bhejta hai (base64 nahi — 33% overhead
  aur string encode/decode bachta hai).
- `bytearray` buffer me accumulate; ~48,000 bytes (~1.5s) hone pe ek STT inference
  (`services.whisper_client`).
- Partial transcript `TRANSCRIPT_CHUNK` JSON se wapas (live caption feel).
- Jab client `text` frame bhejta hai (customer ne bolna khatam kiya) → full transcript LLM
  ko jaata hai **function-calling schema** ke saath (`services.llm_triage`) → structured
  `{appliance_type, suspected_issue, urgency}` nikalta hai → session row me persist
  (`voice_transcript`, `ai_structured_summary`) → `DIAGNOSIS_COMPLETE` JSON.
- Phir TTS stream (`services.tts_client`): synthesized PCM `send_bytes()` se wapas.

**Design choice:** `receive()` (generic) use kiya `receive_bytes()`/`receive_text()` ke
bajaye — kyunki ek hi socket pe dono aa sakte hain (audio binary + control text).

**DB write WebSocket ke andar `SessionLocal()` se direct** — `get_db` FastAPI dependency
sirf HTTP request/response cycle ke liye hai, long-lived socket ke liye nahi. Har diagnosis
event pe apna session open/close hota hai.

**Verify kiya:** ek real Python `websockets` client se (container ke andar chalaya) audio
bytes bheje, transcript chunk mila, text bhej ke diagnosis + audio packets mile, aur DB me
`GET /api/v1/sessions/{id}` se confirm kiya ki transcript + summary save hui.

---

## backend/app/api/v1/endpoints/sessions.py (Phase 2 — naya)

`POST /api/v1/sessions` (CUSTOMER role required) — naya `DiagnosticSession` row banata hai
`session_status="INITIATED"` ke saath. `GET /api/v1/sessions/{id}` — kisi bhi authenticated
role se session detail. Ye session_id hi WebSocket URL me use hota hai.

---

## backend/app/websockets/canvas_sync.py

**Real-time core #2.** `/ws/canvas/sync/{session_id}`. Live annotation overlay. **(Phase 3 —
implemented, real Redis Pub/Sub, `redis.asyncio` se test kiya)**

- Har session ka apna Redis channel: `canvas_sync:{session_id}`. Har connection apna
  `redis.asyncio.from_url(settings.REDIS_URL)` client banata hai (config se URL, hardcoded
  nahi ab).
- Do kaam parallel: (1) `receive_text()` se incoming draw events lena aur Redis pe
  `publish` karna, (2) `pubsub.listen()` se channel ke messages lekar socket pe `send_text`.
- Dusra kaam ek background `asyncio.Task` me chalta hai (`redis_listener`), disconnect pe
  `cancel` + `pubsub.unsubscribe` + `aclose()` — connection leak nahi hota.
- Coordinates normalized `[0.0, 1.0]` aate hain (`norm_x`, `norm_y`) — client apni canvas
  width/height se multiply karke actual pixel nikalta hai. Isliye 4K aur 1080p dono pe
  arrow sahi jagah dikhta hai.

**Kyun Redis Pub/Sub, in-memory dict nahi:** multi-pod deploy me alag pod pe alag peer ho
sakta hai — Redis se sab pods ko broadcast milta hai. Single source of truth.

**Verify kiya:** do WebSocket clients same session pe connect kiye, ek se DRAW event bheja,
doosre pe exact wahi JSON receive hua.

---

## backend/app/websockets/webrtc_signaling.py (Phase 3 — naya)

`/ws/video/signal/{session_id}`. FastAPI sirf **signaling broker** hai — actual video/audio
media WebRTC se peer-to-peer jaata hai, server se nahi (bandwidth bachta hai).

- `offer` / `answer` / `ice_candidate` JSON messages ko session ke dusre peer(s) tak route
  karta hai. In-memory `dict[session_id, list[WebSocket]]` room registry — canvas_sync ki
  tarah Redis Pub/Sub nahi kiya kyunki single-instance deploy me dono peer same process pe
  hote hain, koi cross-pod broadcast zaroorat nahi. Multi-replica scale karna ho to Redis pe
  move karna padega (documented gap, TECHNICAL_SPEC section 8).
- Production me TURN server (coturn) chahiye jab dono peer strict NAT ke peeche ho.

**Verify kiya:** do clients (customer/technician) same session pe connect, ek se `offer`
bheja, doosre pe wahi message forward hua.

---

## backend/app/api/v1/endpoints/streaming.py

HTTP 206 Partial Content byte-range VOD engine — reference troubleshooting videos serve
karne ke liye, poori file RAM me load kiye bina. **(Phase 3 — implemented, JWT-protected)**

- `Range: bytes=start-end` header parse karta hai.
- `file.seek(start)` + generator jo 64KB chunks yield karta hai → `StreamingResponse` with
  status `206` aur `Content-Range` header.
- Range invalid (start/end >= file_size) → `416 Requested Range Not Satisfiable`.
- Range absent → poori file stream (status 200) with `Accept-Ranges: bytes`.
- `Depends(get_current_user)` — JWT-protected, kyunki reference videos authenticated
  diagnostic flow ka hissa hain, public content nahi.

**Interview point:** scrubbing/seeking pe browser naya `Range` request bhejta hai; hum sirf
requested slice disk se padhte hain — disk saturation aur memory bloat dono avoid.

**Verify kiya:** 1MB test file pe — no-range → 200 full file; `bytes=100-199` → 206 with
`Content-Range: bytes 100-199/1000000`; no token → 401; out-of-bounds range → 416. Saare 4
pass.

---

## backend/app/services/spatial_matcher.py (Phase 4 — naya)

- **`find_nearest_available_technician()`** — raw SQL PostGIS KNN query — `is_available =
  TRUE` + `ST_DWithin(current_location::geography, point::geography, 5000)` (5km hard radius
  filter, accurate great-circle distance) + `ORDER BY current_location <-> point` (KNN `<->`
  operator, GIST-index-assisted, `O(log N)`, planar geometry — index ke liye cast nahi kiya)
  + `LIMIT 1`. Returns `user_id` (not `technician_profiles.id` — dispatch FK `users.id` ko
  point karta hai; ye ek real bug tha jo verification me pakda gaya, neeche detail hai).
- **`acquire_technician_lock()` / `release_technician_lock()`** — Redis `SET NX EX 300` /
  `DELETE` on `lock:technician:{user_id}`. Dispatch creation ke race window (KNN match se DB
  commit tak) ko cover karta hai; ongoing job ke dauraan asli "busy" signal
  `technician_profiles.is_available` hai (persistent, TTL nahi).

---

## backend/app/api/v1/endpoints/technicians.py (Phase 4 — naya)

Technician apna geo-profile manage karta hai: `POST /me/profile` (create/update location),
`PATCH /me/location`, `PATCH /me/availability`. Sab `require_roles("TECHNICIAN")` se
protected. `geoalchemy2.shape.from_shape(Point(lon, lat), srid=4326)` se Python
lat/lon → PostGIS geometry banta hai (`shapely` dependency isi ke liye).

---

## backend/app/api/v1/endpoints/dispatch.py

Geospatial dispatch + Dual-OTP state machine. **(Phase 4 — implemented aur full lifecycle
verify kiya)**

- **`POST /dispatch`** (CUSTOMER) — KNN match → Redis lock → `start_otp`/`end_otp` generate
  (`secrets.randbelow`, 6-digit) → dono ka bcrypt hash DB me → dispatch row `PENDING` →
  plaintext OTPs response me **ek hi baar** return (real product me SMS jaata, yahan
  simplification hai).
- **`POST /dispatch/{id}/accept`** (assigned TECHNICIAN only) — `PENDING → ACCEPTED`,
  technician `is_available = False` (taaki KNN dobara match na kare).
- **`POST /dispatch/{id}/verify-start-otp`** — `ACCEPTED → IN_PROGRESS`, `start_otp_hash`
  verify.
- **`POST /dispatch/{id}/verify-end-otp`** — `IN_PROGRESS → COMPLETED`, `end_otp_hash`
  verify, `platform_commission_fee` (15%) + `technician_earnings` (85% − 1% TDS) compute,
  `completed_at` set, technician `is_available = True` restore, Redis lock release.
- Har transition pe do checks stack hote hain: role (`require_roles("TECHNICIAN")`) AND
  ownership (`dispatch.technician_id == current_user.id`) — koi doosra technician kisi aur
  ka job complete na kar sake.

**Kyun hash:** DB leak ho jaye to bhi OTP se koi job hijack na kar sake. Password jaisa hi
`passlib.bcrypt` primitive reuse kiya — alag hashing scheme ki zaroorat nahi thi.

**Bug jo verification me pakda gaya:** pehla version `technician_profiles.id` return kar raha
tha KNN se, lekin `service_dispatches.technician_id` FK `users.id` hai — dispatch create karte
hi `IntegrityError: ForeignKeyViolation` aaya. `user_id` return karke fix kiya. Ye exactly
wahi bug hai jo sirf real end-to-end run se pakda jaata hai, code review se nahi.

**Verify kiya:** poora lifecycle — no-match case (404), distributed lock (409 on concurrent
request), wrong OTP (400), full `PENDING→ACCEPTED→IN_PROGRESS→COMPLETED`, aur completion ke
baad lock release + technician turant dobara available (naya dispatch turant match hua).

---

## backend/workers/celery_app.py

Celery instance config — broker `redis://redis:6379/1`, result backend `/2`. Task
autodiscovery `workers.tasks.*` se. `worker` container isi ko `celery -A` se run karta hai.

---

## backend/workers/storage.py (Phase 5 — naya)

Shared `boto3` S3/MinIO helper — teeno worker task isi ko use karte hain, koi bhi apna client
nahi banata. `get_s3_client()`, `ensure_bucket()` (bucket na ho to create), `upload_directory()`
(recursive, HLS output ke liye), `upload_file()` (PDF jaisi single file ke liye).

---

## backend/workers/tasks/media_transcode.py **(Phase 5 — implemented aur real FFmpeg se test kiya)**

`tasks.transcode_to_hls` — session recording ko FFmpeg se ABR HLS me convert karta hai.

- Ek FFmpeg command me teen rendition: 1080p (4500k), 720p (2500k), 480p (1000k).
- **`-filter_complex "[0:v]split=3[v1][v2][v3];[v1]scale=...[v1out];..."` + `-map [vNout]`
  per rendition** — spec ke reference snippet me repeated `-vf` per output tha, jo asal me
  kaam nahi karta (neeche bug section dekho). `split` filter se input ek baar decode hoke 3
  independent branches me scale hota hai.
- `-var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2"` — har video stream ke saath audio pair.
- `-hls_time 4` — 4-second `.ts` segments; `master.m3u8` + `stream_%v.m3u8` playlists.
- Output poora directory MinIO pe upload (`hls/{session_id}/`), `hls_master_playlist_url`
  return.
- `bind=True, max_retries=3` — FFmpeg fail (corrupt input) pe `self.retry(countdown=10)`.

**Kyun Celery, request ke andar nahi:** transcode minutes le sakta hai — HTTP request
timeout ho jaayega aur worker block hoga. Async offload + retry + progress tracking.

**Bug jo real ffmpeg run se pakda gaya:** `-vf scale=...` ko 3 baar repeat karna (ek per
output) sirf **last** wala rakhta hai — codec options (`-c:v:N`) ki tarah fan-out nahi hota.
Result tha: `hls: Unable to map stream at v:1`, zero output files. `-filter_complex` + `split`
+ explicit `-map` se fix kiya. Ye tabhi pakda jaata hai jab command real video file pe chalao,
sirf padhne se nahi.

**Verify kiya:** container ke andar `ffmpeg -f lavfi` se 2-second test video banaya, task run
kiya, 3 real renditions (segments + playlists) disk pe aur MinIO dono me confirm kiye.

---

## backend/workers/tasks/report_generate.py **(Phase 5 — implemented)**

`tasks.generate_report` — WeasyPrint se inspection PDF. Customer/technician name, diagnosis
summary, voice transcript, `parts_replaced` table, billing breakdown (fee/commission/earnings)
→ inline-styled HTML string → PDF (`HTML(string=...).write_pdf()`) → MinIO
(`reports/{dispatch_id}.pdf`) → `invoice_pdf_url` return.

**Gotcha:** `weasyprint==62.3` naye `pydyf` (0.12.1) ke saath incompatible hai
(`AttributeError: 'super' object has no attribute 'transform'`, ek breaking API change jo
WeasyPrint abhi tak catch up nahi kiya). `pydyf==0.10.0` explicitly pin kiya.

**Verify kiya:** sample dispatch data se PDF generate kiya, MinIO se download karke `%PDF-`
magic bytes confirm kiye.

---

## backend/workers/tasks/payout_settle.py **(Phase 5 — implemented)**

`tasks.settle_payouts` — weekly Celery beat schedule (`crontab(hour=2, minute=0,
day_of_week=1)`, har Monday). Har `COMPLETED` dispatch jiska `settled_at IS NULL` hai, uska
`technician_earnings` uss technician ke `wallet_balance` me credit hota hai, `settled_at`
stamp hota hai.

**Kyun `settled_at` column, `dispatch_status="SETTLED"` nahi:** DB `CHECK` constraint sirf
`PENDING/ACCEPTED/IN_PROGRESS/COMPLETED/CANCELLED` allow karta hai. Settlement job-lifecycle
se alag concern hai (dispute ho jaaye to job ko un-complete kiye bina bhi handle hona chahiye)
— isliye naya nullable timestamp column, naya Alembic migration (`0002_add_settled_at.py`).

**Kyun `settled_at IS NULL` filter, time-window nahi:** agar worker kuch din down rahe, agli
run purana sab catch up kar legi, silently skip nahi karegi.

**Verify kiya:** real dispatch lifecycle complete kiya (fee=1000 → commission=150,
earnings=841.5), task run kiya, `wallet_balance` 0 → 841.5 confirm kiya, dobara run kiya to
`settled_count: 0` (idempotent, double-credit nahi hua).

---

## backend/Dockerfile

1. `python:3.12-slim` base.
2. `apt-get install ffmpeg` + WeasyPrint ki system deps (`libpango`, `libcairo`, `libgdk-pixbuf`).
3. `requirements.txt` pehle copy + install (layer caching).
4. `app/` + `workers/` copy.
5. `uvicorn app.main:app --host 0.0.0.0 --port 8000` (worker container CMD override karta hai).

---

## docker-compose.yml

| Service | Image | Kaam | Host port |
|---|---|---|---|
| `db` | `postgis/postgis:16-3.4` | Relational + spatial store | `5434` (container: `5432`) |
| `redis` | `redis:7-alpine` | Pub/sub, locks, Celery broker | `6381` (container: `6379`) |
| `minio` | `quay.io/minio/minio` | S3-compatible object storage | `9002`/`9003` |
| `backend` | build `./backend` | FastAPI gateway, startup pe `alembic upgrade head` | `8000` |
| `worker` | build `./backend` | `celery -A workers.celery_app worker` | — |
| `beat` | build `./backend` | `celery -A workers.celery_app beat` (weekly payout scheduler) | — |
| `frontend` | build `./frontend` | (commented out) | — |

**`minio/minio` Docker Hub se hata diya gaya hai** (MinIO ne publishing model badla) — ab
`quay.io/minio/minio:latest` use karte hain.

**Host ports 5432/6379 default se hata ke 5434/6381/9002/9003 kiye** — is machine pe pehle se
ek doosra project (`webguard-*`) `5432` aur `6379` occupy kiye baitha tha; container-to-container
communication `db:5432` / `redis:6379` (internal Docker network names) unchanged hai, sirf host
se access karne ka port badla hai. `.env` / app code me kahin bhi host port hardcode nahi —
sab internal service name se baat karte hain.

**`frontend` service abhi comment-out hai** — `frontend/Dockerfile` khaali hai aur koi React
code nahi bana. Jab Frontend phase (BUILD_PLAN session 4) aayega, tab uncomment karke real
Dockerfile ke saath enable karenge. Isse pehle enable karte to `docker compose up` yahi pe
fail ho jaata.

---

## .env.example

Real secrets (`.env`) `.gitignore` me hai. `.env.example` sirf template hai — batata hai
konse vars chahiye (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `LLM_API_KEY`,
`TTS_API_KEY`, `S3_*`) bina real values leak kiye.

---

## Aage jo bhi file banegi, uska explanation yahin niche add hoga.
