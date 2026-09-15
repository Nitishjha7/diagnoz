# Test Suite — Integration Tests Against the Real Stack

**Status:** ✅ Complete — 34 tests, all passing against `docker compose`
**Date:** 2026-09-15

---

## Why integration tests, not unit tests with mocks

Every other phase of this project was verified against the real running system (real
Postgres+PostGIS, real Redis, a real browser) rather than mocks — because the bugs that
actually mattered (an FK pointing at the wrong table, a PostGIS query returning the wrong
column, a Redis lock race, a substring-matching bug) only show up when the real
infrastructure is in the loop. The test suite in `backend/tests/` follows the same
philosophy: `fastapi.testclient.TestClient` calls the real app object, which talks to the
real `db` and `redis` containers over the same Docker network the app uses at runtime. No
`sqlite`-in-memory swap, no `unittest.mock.patch`.

Run with:

```bash
docker compose up -d db redis backend
docker compose exec backend pytest tests/ -v
```

## What's covered

| File | Covers |
|---|---|
| `test_auth.py` | Register, duplicate-email rejection, invalid role, login, `/me` auth guard |
| `test_sessions.py` | Session create/get, RBAC (customer-only), 404 for unknown session |
| `test_technicians.py` | Profile create/update, RBAC, 404 without a profile, availability toggle |
| `test_dispatch.py` | Full dual-OTP lifecycle (`PENDING→ACCEPTED→IN_PROGRESS→COMPLETED`), KNN match, no-match 404, concurrent-lock 409, wrong-OTP 400, cross-technician 403, out-of-order-transition 409 |
| `test_streaming.py` | HTTP 206 partial content, full-file 200, out-of-range 416, auth requirement |
| `test_websockets.py` | Full audio triage pipeline (transcript → diagnosis → TTS), DB persistence, canvas sync relay, WebRTC signaling relay |

## Test isolation for the dispatch/KNN tests

The `available_technician` fixture in `conftest.py` uses the same isolation trick as
`eval/run_eval.py`: it temporarily marks every *other* `is_available=TRUE` technician in the
database unavailable for the duration of the test, then restores them — so KNN-matching
tests are deterministic regardless of what demo or other-test data already exists, and safe
to run repeatedly against a shared database.

## Two real bugs this test suite caught (both fixed)

1. **`/ws/audio/triage` raised an unhandled `RuntimeError` on client disconnect.** The
   handler only caught `WebSocketDisconnect`, but Starlette's `websocket.receive()` raises a
   plain `RuntimeError` (not `WebSocketDisconnect`) if the client has already torn down the
   connection while a `send` was still in flight — which is exactly what happens when a test
   (or a real browser tab closing mid-stream) disconnects while the server is still
   streaming TTS audio packets back. Fixed by also catching `RuntimeError`, narrowed to only
   swallow it when `websocket.client_state` confirms the client actually disconnected (so a
   genuine bug elsewhere in the handler still surfaces as a real error, not a silently eaten
   exception).
2. **Fixture aliasing bug in the test suite itself** (not app code): an early version of
   `test_a_different_technician_cannot_act_on_someone_elses_dispatch` requested both the
   `available_technician` fixture and the plain `technician` fixture in the same test —
   since `available_technician` itself depends on `technician`, and pytest caches
   function-scoped fixtures per test, both names resolved to the *same* underlying
   technician. The "different technician" in the test was actually the same one, so the 403
   assertion silently passed for the wrong reason once, then failed once the aliasing was
   noticed. Fixed by registering a genuinely separate technician via `register_user` instead
   of reusing a fixture.

---

## Next

The project is functionally complete: backend (Phase 1–5), frontend, evaluation harness, and
now an integration test suite, all verified against the real running stack.
