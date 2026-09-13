# Build Plan — Kaise Chalna Hai

Ye file batati hai ki DiagnoZ ko step-by-step kaise build karenge, kaun kya karega, aur
kitna time lagega. Har session ke baad isko update karte rahenge (✅ mark karte jaana).

---

## Working Style

- **Claude (main):** phase-wise chalta hua code likhega — models, WebSockets, Celery,
  frontend. Har phase ke baad `docker compose up` pe run hona chahiye.
- **Nitish (tu):** har phase ke baad code khud padhega, trace karega, "ye kyun" poochega,
  aur khud ek baar chala ke har flow test karega. Ye part skip nahi karna — interview me
  yahi kaam aata hai.
- Ek time pe ek hi phase. Phase pura + run verify hone ke baad hi agla.

---

## Build Schedule (Claude ka output)

| Session | Phase | Deliverable | Status |
|---|---|---|---|
| 1 | Phase 1 | SQLAlchemy models, PostGIS + Alembic migration, JWT/RBAC auth, `docker-compose.yml` chalu (db+redis+minio+backend+worker) | ✅ |
| 1 | Phase 2 | `/ws/audio/triage` (binary PCM → STT → LLM function calling → TTS), sessions API | ✅ |
| 2 | Phase 3 | `/ws/video/signal` (WebRTC SDP/ICE broker), `/ws/canvas/sync` (normalized coords + Redis Pub/Sub), `/api/v1/videos/stream` (HTTP 206 byte-range) | ✅ |
| 3 | Phase 4 | PostGIS KNN dispatch + Redis 5-min lock, Dual-OTP state machine | ✅ |
| 3 | Phase 5 | Celery: FFmpeg HLS transcode + WeasyPrint PDF + 85/15 payout split | ⬜ |
| 4 | Frontend + wiring | React 19 demo UI (CustomerRoom, TechnicianConsole, DispatchTracker), end-to-end wiring, local run verify | ⬜ |

**Claude ka effort:** ~4 working sessions. Back-to-back karein toh 1–2 din.

---

## Nitish ka Part (interview-ready banne ke liye)

Har phase ke baad:
1. [CODE_NOTES.md](CODE_NOTES.md) padh — us phase ki files ka "kya / kyun"
2. Code line-by-line trace kar, jo samajh na aaye Claude se pooch
3. `docker compose up` karke us phase ka flow khud chala (audio bhej, dispatch trigger kar, video stream kar)
4. [INTERVIEW_NOTES.md](INTERVIEW_NOTES.md) ka relevant Q&A bolke practice kar

**Nitish ka effort:** ~4–5 din (daily 2–3 ghante).

---

## Total Timeline

| Scenario | Time |
|---|---|
| Sirf chalta hua code (Claude) | ~4 sessions / 1–2 din |
| Code + tu confidently explain kar sake | **~1 hafta** (daily 2–3 ghante) |
| Interview-ready MVP (Phase 2+3+4 solid, 5 stubbed, minimal UI) | ~10–12 din |

---

## Order of Execution

1. Phase 1 — models + PostGIS + auth
2. Phase 2 — audio triage
3. Phase 3 — video engine (signaling + canvas + 206)
4. Phase 4 — dispatch + dual-OTP
5. Phase 5 — Celery workers
6. Frontend demo UI
7. Docker compose + deployment (Neon + Render + Vercel)
8. Eval script + INTERVIEW_NOTES me real numbers bharna

Detail har phase ka [ROADMAP.md](ROADMAP.md) me hai.

---

## Known Time-Sinks (jahan atkega)

- **WebRTC** — STUN/TURN, ICE candidates, browser quirks. TURN ke liye free metered.ca use karenge.
- **FFmpeg HLS** — multi-bitrate command tuning.
- **Real-time audio** — buffering size vs latency ka trade-off debug karna.
- **Voice pipeline** — external LLM/TTS API se fast; self-host kiya toh +3–4 din.

---

## Next Step

Phase 1 se 4 tak complete ho chuke hain — detail [PHASE_1_NOTES.md](PHASE_1_NOTES.md),
[PHASE_2_NOTES.md](PHASE_2_NOTES.md), [PHASE_3_NOTES.md](PHASE_3_NOTES.md),
[PHASE_4_NOTES.md](PHASE_4_NOTES.md) me. Phase 5 (Celery workers) chal raha hai.
