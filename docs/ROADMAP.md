# Roadmap — Interview-Ready Project Plan

**Goal:** DiagnoZ ko ek **interview me dikhane layak, depth-wala project** banana hai
(full production product nahi). Priority sirf un cheezon pe hai jo interview me "impressive"
aur "defendable" lagengi — real-time systems, media infra, geospatial.

---

## Current Status (jo ban chuka hai)

- ✅ Repo scaffold — `backend/`, `frontend/`, `docker-compose.yml`, `.gitignore`
- ✅ Docs: README, TECHNICAL_SPEC, SETUP, ROADMAP, CODE_NOTES, INTERVIEW_NOTES
- ✅ **Phase 1 complete** — SQLAlchemy models (`users`, `technician_profiles`,
  `diagnostic_sessions`, `service_dispatches`), PostGIS + Alembic migration (GIST indexes),
  JWT/RBAC auth (register/login/me), `docker-compose.yml` verified end-to-end (db, redis,
  minio, backend, worker all boot + migrate clean). Detail: [PHASE_1_NOTES.md](PHASE_1_NOTES.md)
- ✅ **Phase 2 complete** — `/ws/audio/triage` (binary PCM → STT stub → keyword-based LLM
  triage extractor → synthetic TTS stream), sessions API, offline-first service layer
  (`services/whisper_client.py`, `llm_triage.py`, `tts_client.py`) so the pipeline runs with
  zero external API keys. Verified with a real WebSocket client end-to-end, including DB
  persistence. Detail: [PHASE_2_NOTES.md](PHASE_2_NOTES.md)
- ✅ **Phase 3 complete** — `/ws/video/signal` (WebRTC signaling broker), `/ws/canvas/sync`
  (Redis Pub/Sub annotation broadcast), `/api/v1/videos/stream` (HTTP 206 byte-range, JWT
  protected). All verified with real multi-client WebSocket tests + range-request HTTP tests.
  Detail: [PHASE_3_NOTES.md](PHASE_3_NOTES.md)
- ✅ **Phase 4 complete** — PostGIS KNN dispatch (`services/spatial_matcher.py`), Redis
  distributed lock (5-min TTL), dual-OTP state machine (`PENDING→ACCEPTED→IN_PROGRESS→
  COMPLETED`), technician profile/location/availability endpoints. Verified full lifecycle
  end-to-end including a real bug found + fixed (KNN returning the wrong FK). Detail:
  [PHASE_4_NOTES.md](PHASE_4_NOTES.md)
- ✅ **Phase 5 complete** — `tasks.transcode_to_hls` (real FFmpeg multi-bitrate HLS, fixed a
  broken reference command via `-filter_complex`+`split`), `tasks.generate_report`
  (WeasyPrint PDF, pinned a `pydyf` compat issue), `tasks.settle_payouts` (idempotent weekly
  wallet-balance settlement, Celery beat scheduled). All 3 verified running for real (ffmpeg,
  WeasyPrint, MinIO) inside `docker compose`, not mocked. Detail:
  [PHASE_5_NOTES.md](PHASE_5_NOTES.md)
- ✅ **Frontend complete** — React 19 + Vite demo UI (CustomerRoom, TechnicianConsole,
  DispatchTracker), wired to every backend endpoint/WebSocket. Verified with headless
  Playwright against the real running backend in both dev-server mode and the fully
  Dockerized Nginx-served build — a real CORS bug was caught and fixed in the process.
  Detail: [PHASE_FRONTEND_NOTES.md](PHASE_FRONTEND_NOTES.md)
- ✅ **Evaluation harness complete** — `eval/scenarios.json` (18 triage + 4 dispatch labeled
  scenarios) + `eval/run_eval.py`, run against the real system. Measured: 100% appliance-type
  accuracy, 88.9% urgency accuracy, 100% dispatch KNN precision. Caught and fixed a real
  substring-matching bug in `llm_triage.py` along the way. Numbers are in
  `docs/INTERVIEW_NOTES.md` section 3a. Detail: [PHASE_EVAL_NOTES.md](PHASE_EVAL_NOTES.md)
- **Project is functionally complete: backend (Phase 1–5), frontend, and evaluation harness
  are all implemented and verified against the real running system.**

---

## Phase Order (spec ke 5 phases)

### Phase 1 — Foundation: DB models, PostGIS, Auth
SQLAlchemy models (`users`, `technician_profiles`, `diagnostic_sessions`,
`service_dispatches`) + PostGIS `GEOMETRY(Point, 4326)` columns + GIST indexes via Alembic.
JWT issuance + RBAC dependency guards (`CUSTOMER` / `TECHNICIAN` / `ADMIN`).

**Kyun pehle:** baaki sab isi pe khada hai. PostGIS extension enable karna, `geoalchemy2`
use karna — ye setup interview me "spatial DB experience" prove karta hai.

### Phase 2 — Binary Audio AI Triage
`/ws/audio/triage/{session_id}` — raw 16kHz PCM binary ingestion, ~1.5s buffering,
streaming Whisper STT → LLM function calling (structured `appliance_type / suspected_issue /
urgency`) → streaming TTS wapas client ko.

**Interview point:** "base64 JSON kyun nahi use kiya" — 33% bandwidth overhead + har chunk
pe string encode/decode event loop pe. Raw `ArrayBuffer` optimal hai.

### Phase 3 — Video Room & Streaming
- `/ws/video/signal` — FastAPI async signaling broker (offer/answer/ice_candidate routing).
- `/ws/canvas/sync` — normalized `[0.0, 1.0]` coordinate broadcast over Redis Pub/Sub.
- `/api/v1/videos/stream/{id}` — HTTP 206 byte-range `StreamingResponse` (file pointer
  seek, no RAM bloat, instant scrubbing).

**Interview point:** "rapid seeking kaise handle hota hai" — browser `Range: bytes=X-Y`
bhejta hai, hum `file.seek(start)` karke sirf woh slice yield karte hain.

### Phase 4 — Geospatial Dispatch & Dual-OTP
PostGIS KNN query (`<->` operator + GIST index + `ST_DWithin` 5km filter) closest available
technician nikalta hai `O(log N)` me. Redis distributed lock 5 min ke liye assignment hold
karta hai. Dual-OTP state machine: `ASSIGNED → (start_otp) IN_PROGRESS → (end_otp) COMPLETED`,
OTP hashed store hote hain (`pgcrypto` / bcrypt).

**Interview point:** "PostGIS vs bounding box" — flat Euclidean math Earth curvature ignore
karta hai aur full-table scan `O(N)` hota hai; GIST R-Tree `O(log N)`.

### Phase 5 — Celery Media, Invoicing & Payout
- `tasks.transcode_to_hls` — FFmpeg ABR HLS (1080/720/480), `master.m3u8` + 4s `.ts`
  segments → MinIO.
- `tasks.generate_report` — WeasyPrint inspection PDF (snapshots, transcript, parts,
  signature).
- `tasks.settle_payouts` — weekly batch: `commission = amount * 0.15`,
  `payout = amount * 0.85 - TDS(1%)`, ledger update.

---

## Aage ki priority (proof-of-work — spec se bahar, but interview me strong)

### A. Evaluation / metrics script
`eval/scenarios.json` — 15-20 sample fault descriptions with expected structured output.
Ek script measure kare: triage extraction accuracy, remote-resolution rate simulate,
dispatch KNN precision (kya sach me nearest technician mila).

**Kyun:** "bana ke chhod diya" vs "maine measure kiya" — interviewer turant pakadta hai.
Numbers strong hote hain.

### B. Frontend demo UI (React 19 + Vite)
`CustomerRoom` (mic widget + video + canvas overlay), `TechnicianConsole` (draw tools),
`DispatchTracker` (map + OTP entry). Live demo Swagger se hamesha better lagta hai.

### C. `docs/INTERVIEW_NOTES.md` — ✅ already likha hua
30-sec pitch, problem, "real ya toy?", full flow, architecture, 6 USP deep-dives, ROI table,
limitations + mitigations, interview presentation script, aur anticipated Q&A (technical +
product). Jaise-jaise implementation aage badhe, isme concrete numbers (measured
remote-resolution rate, dispatch latency) add karte rehna.

Aage add karne layak Q&A:
- "WebRTC signaling FastAPI pe kyun, dedicated SFU kyun nahi" → P2P hai, SFU sirf
  multi-party ke liye chahiye; 1-on-1 triage ke liye signaling broker kaafi
- "dispatch lock TTL 5 min kyun" → technician ko accept/reject ka realistic window,
  itni der me stale nahi hota
- "OTP hash kyun, plain kyun nahi" → DB leak pe job hijack na ho

---

## Deployment Plan (free tier)

| Piece | Kahan | Kyun |
|---|---|---|
| PostgreSQL + PostGIS | [Neon](https://neon.tech) / [Supabase](https://supabase.com) | Free tier, PostGIS supported |
| Redis | [Upstash](https://upstash.com) | Free serverless Redis, pub/sub + TLS |
| Backend + Worker | [Render](https://render.com) | Docker se deploy, background worker service |
| Object storage | [Cloudflare R2](https://developers.cloudflare.com/r2/) / Supabase Storage | S3-compatible, free egress (R2) |
| Frontend | [Vercel](https://vercel.com) / [Netlify](https://netlify.com) | Free static, GitHub auto-deploy |

**Gotchas:**
- WebRTC ke liye TURN server chahiye hoga (coturn) agar dono peer strict NAT ke peeche ho —
  free [metered.ca](https://www.metered.ca/tools/openrelay/) TURN use kar sakte ho.
- Render free tier sleep hota hai — demo se pehle URL warm kar lena.
- `.env` kabhi commit mat karna — `.gitignore` already exclude karta hai, sirf
  `.env.example` commit hota hai.

---

## Order of Execution

1. Phase 1 — models + PostGIS + auth
2. Phase 2 — audio triage
3. Phase 3 — video engine (signaling + canvas + 206)
4. Phase 4 — dispatch + dual-OTP
5. Phase 5 — Celery workers
6. Evaluation script
7. Frontend demo UI
8. Deployment
9. `docs/INTERVIEW_NOTES.md` refine — real measured numbers bharna
