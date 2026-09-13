# Phase 3 — Video Room & Streaming

**Status:** ✅ Complete & verified (real WebSocket + HTTP clients against `docker compose`)
**Date:** 2026-09-13

---

## Kya banaya

1. **`backend/app/websockets/webrtc_signaling.py`** (naya) — `/ws/video/signal/{session_id}`:
   FastAPI ek pure async **signaling broker** hai, media khud kabhi server se nahi guzarta
   (peer-to-peer). `offer` / `answer` / `ice_candidate` JSON messages jo bhi ek peer bhejta
   hai, session ke doosre peer(s) ko forward ho jaate hain. In-process `dict[session_id,
   list[WebSocket]]` room registry use kiya (single-instance deploy ke liye kaafi; horizontal
   scaling chahiye ho to Redis-backed registry chahiye hoga — `docs/TECHNICAL_SPEC.md` section
   8 "Future Extensions" me already noted hai).
2. **`backend/app/websockets/canvas_sync.py`** — `/ws/canvas/sync/{session_id}`: Redis
   Pub/Sub se normalized `[0.0, 1.0]` annotation coordinates broadcast. Har connection apna
   `redis.asyncio` client + `pubsub` banata hai, background `asyncio.Task` listen karta hai
   aur socket disconnect pe cleanly `cancel` + `unsubscribe` + `aclose` karta hai (connection
   leak na ho).
3. **`backend/app/api/v1/endpoints/streaming.py`** — `GET /api/v1/videos/stream/{video_id}`:
   HTTP 206 byte-range VOD streaming. `Range` header parse, `file.seek(start)` + generator
   64KB chunks yield karta hai, poori file kabhi RAM me nahi aati. JWT-protected
   (`Depends(get_current_user)`) — spec me auth mention nahi tha explicitly par sab
   authenticated-user-only endpoints hone chahiye.
4. **`config.py`** — `REFERENCE_VIDEO_PATH`, `HLS_OUTPUT_PATH` settings add kiye.
5. **`main.py`** + `api/v1/router.py`** — dono naye WebSocket router aur `streaming` REST
   router wire kiye.

---

## Kaise verify kiya

**Canvas sync** — do WebSocket clients (`ws_a`, `ws_b`) same `session_id` pe connect kiye,
`ws_a` se ek `DRAW` event bheja, `ws_b` pe exact wahi JSON receive hua (Redis Pub/Sub round
trip confirm).

**WebRTC signaling** — do clients (`customer`, `technician`) same session pe connect kiye,
`customer` se `offer` bheja, `technician` ne wahi message receive kiya (broker relay confirm).

**HTTP 206 streaming** — ek 1MB random test file container ke andar bana ke:
- Bina `Range` header → `200 OK`, poori file, `Accept-Ranges: bytes`.
- `Range: bytes=100-199` → `206 Partial Content`, `Content-Range: bytes 100-199/1000000`,
  `Content-Length: 100`.
- Bina JWT token → `401`.
- Out-of-bounds range → `416 Requested Range Not Satisfiable`.

Sab 4 cases pass hue.

---

## Decisions / gotchas (interview-relevant)

- **WebRTC signaling room registry in-memory, not Redis, for now.** A 1-on-1 triage room
  only needs the two peers connected to the *same* process instance to see each other; Redis
  Pub/Sub would only matter once there's more than one backend replica behind a load
  balancer. Kept simple for now, documented as a known scaling gap (matches
  TECHNICAL_SPEC.md's own "Future Extensions" phase 7).
- **`canvas_sync` opens a new Redis client per WebSocket connection** rather than sharing one
  global client — simpler cleanup semantics (each connection's `pubsub`/`aclose()` lifecycle
  is self-contained) at the cost of a few more Redis connections; fine at this project's scale.
- **Streaming endpoint requires JWT** even though the spec's reference snippet didn't show
  auth — added `Depends(get_current_user)` since reference videos are part of an
  authenticated diagnostic flow, not public content.
- **`redis.asyncio` needed no extra pip package** — `redis-py>=4.2` ships it in the base
  `redis` package; no separate `aioredis` dependency (that package is deprecated/merged into
  `redis-py` upstream).

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"Why not a dedicated SFU (Selective Forwarding Unit) for video?"** — this is 1-on-1
  triage, not multi-party conferencing; media flows peer-to-peer once FastAPI has brokered the
  SDP/ICE handshake. An SFU only earns its complexity at 3+ participants needing server-side
  media mixing/forwarding.
- **"What happens on rapid seek/scrub in the video player?"** — the browser issues a fresh
  `Range: bytes=X-Y` request per seek; the server does `file.seek(start)` and streams only
  that slice — verified above with a mid-file 100-byte range request returning exactly 100
  bytes with the correct `Content-Range`.
- **"How would canvas sync scale beyond one backend instance?"** — it already would, without
  code changes: Redis Pub/Sub is the source of truth, any backend replica subscribed to
  `canvas_sync:{session_id}` gets every event. WebRTC signaling's in-memory room registry is
  the one piece that would need to move to Redis for multi-replica correctness.

---

## Next

Phase 4 — PostGIS KNN geospatial dispatch, Redis distributed lock, dual-OTP state machine.
See [ROADMAP.md](ROADMAP.md).
