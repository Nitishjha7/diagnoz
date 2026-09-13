# Phase 2 — Binary Audio AI Triage

**Status:** ✅ Complete & verified (real WebSocket client run against `docker compose`)
**Date:** 2026-09-13

---

## Kya banaya

1. **`backend/app/services/`** — three pluggable, provider-agnostic services:
   - `whisper_client.py` — `transcribe_audio_chunk(pcm_bytes) -> str`. Real STT (faster-whisper)
     plugs in here later; for now, a stub uses `audioop.rms` to detect whether a chunk has
     actual signal (vs silence) and returns a placeholder transcript describing the audio.
   - `llm_triage.py` — `analyze_appliance_issue(transcript) -> dict`. If `LLM_API_KEY` is set,
     a real function-calling LLM call would run (schema already defined as `FUNCTION_SCHEMA`).
     Without a key, a deterministic keyword extractor detects appliance type (AC, fridge,
     washing machine, ...) and urgency (HIGH/MEDIUM/LOW) from the transcript text.
   - `tts_client.py` — `synthesize_speech_stream(text) -> AsyncIterator[bytes]`. Without
     `TTS_API_KEY`, streams synthetic sine-wave PCM chunks (proves the streaming/framing
     contract works) instead of a real voice.
2. **`backend/app/websockets/audio_triage.py`** — `/ws/audio/triage/{session_id}`:
   - Accumulates raw binary PCM in a `bytearray`; every ~48,000 bytes (~1.5s @ 16kHz mono
     16-bit) runs STT and sends back a `TRANSCRIPT_CHUNK` JSON message.
   - On a `text` frame (customer signals "done speaking"), runs the LLM triage extractor,
     persists `voice_transcript` + `ai_structured_summary` onto the `DiagnosticSession` row,
     replies with `DIAGNOSIS_COMPLETE`, then streams synthesized audio back via `send_bytes`.
3. **`backend/app/api/v1/endpoints/sessions.py`** + `schemas/session.py` — `POST /api/v1/sessions`
   (CUSTOMER-only, creates a `DiagnosticSession` row) and `GET /api/v1/sessions/{id}` — needed
   so there's a real session UUID to open the WebSocket against.
4. **`config.py`** — added `WHISPER_MODEL`, `LLM_API_KEY`, `LLM_MODEL`, `TTS_API_KEY`,
   `TTS_VOICE` settings (present in `.env.example` since Phase 0 scaffold but not yet wired
   into `Settings`).
5. **`main.py`** — mounted the audio triage WebSocket router.

---

## Kaise verify kiya

```bash
docker compose up -d --build backend
```

Register + login + create a session (see Phase 1 notes for the auth calls), then open a
WebSocket to `/ws/audio/triage/{session_id}` and:

1. Send raw 16-bit PCM binary bytes (≥ 48,000 bytes of non-silent audio) → expect a
   `TRANSCRIPT_CHUNK` JSON message back.
2. Send a text frame with the full spoken sentence (e.g. *"Mera AC cooling nahi kar raha aur
   compressor se rattling sound aa rahi hai"*) → expect `DIAGNOSIS_COMPLETE` with
   `{"appliance_type": "AC", "suspected_issue": "...", "urgency": "MEDIUM", "voice_summary": "..."}`
   followed by several binary audio packets.
3. `GET /api/v1/sessions/{id}` afterwards → `voice_transcript` and `ai_structured_summary`
   should be persisted.

This was run in-session with a Python `websockets` client executed inside the `backend`
container (no local Python on the host machine) and all three checks passed, including the
DB persistence check.

---

## Decisions / gotchas (interview-relevant)

- **Offline-first service stubs, not mocks-in-tests.** Instead of only unit-testing with
  mocks, the actual runtime code path has a working fallback when no API key is configured.
  This means `docker compose up` gives a fully running, demo-able pipeline with zero external
  API keys — swapping in real Whisper/LLM/TTS later is just filling in the `if
  settings.LLM_API_KEY:` branches without changing the WebSocket contract or call signatures.
- **`receive()` not `receive_bytes()`/`receive_text()`** — same reasoning as the original
  spec: one socket carries both binary audio frames and a text "I'm done talking" control
  frame, so the generic `receive()` (returning a dict with either key) is required.
- **Why urgency/appliance detection is keyword-based and not a toy random choice** — it's
  deterministic and inspectable, which matters for the eventual evaluation script
  (`docs/ROADMAP.md` section A) that will measure triage extraction accuracy against a labeled
  test set.
- **DB write happens inside the WebSocket handler using a fresh `SessionLocal()`**, not the
  `get_db` FastAPI dependency (that only works for HTTP request/response cycles, not
  long-lived WebSocket connections) — opened and closed per diagnosis event, not held for the
  life of the socket.

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"What happens if no LLM/TTS API key is configured — does the demo break?"** — No. Every
  service module has a deterministic offline fallback, so the entire audio triage flow
  (including realistic-shaped responses and streamed audio) works without any paid API keys.
  This was a deliberate architecture choice for a demo/interview project — the *service
  interface* is what matters for the architecture story, not which vendor sits behind it.
- **"Why base64 JSON was rejected"** — already documented in TECHNICAL_SPEC.md / ROADMAP.md;
  same reasoning holds and was verified in practice: `send_bytes()`/binary frames flow
  through with zero string encoding overhead in the implementation above.

---

## Next

Phase 3 — WebRTC video signaling, live canvas annotation sync (Redis Pub/Sub), and HTTP 206
byte-range video streaming. See [ROADMAP.md](ROADMAP.md).
