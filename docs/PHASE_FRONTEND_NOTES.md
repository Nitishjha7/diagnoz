# Frontend Phase — React 19 + Vite Demo UI

**Status:** ✅ Complete & verified (real browser, Playwright-driven, both dev and Docker/Nginx modes)
**Date:** 2026-09-13

---

## Kya banaya

1. **Scaffold** — `npm create vite@latest . -- --template react` (React 19.2, Vite 8). Structure
   follows `docs/TECHNICAL_SPEC.md` section 5: `components/`, `hooks/`, `pages/`, `lib/`.
2. **`src/lib/api.js`** — single fetch wrapper for every backend call (auth, sessions,
   technicians, dispatch). Attaches the JWT from `localStorage` automatically. Base URL
   resolves differently per environment (see gotcha below).
3. **Hooks:**
   - `useAuth.js` — login/register/logout + current-user state, backed by `/auth/me`.
   - `useWebSocket.js` — generic WS connection lifecycle hook.
   - `useAudioRecorder.js` — `AudioContext` + `ScriptProcessorNode` mic capture, downsamples
     to 16kHz mono and hands raw PCM16 `ArrayBuffer`s to a callback — matches the
     `/ws/audio/triage` binary contract exactly (no base64).
4. **Components:**
   - `AudioTriageWidget.jsx` — connects to `/ws/audio/triage/{session_id}`, streams mic audio,
     renders live `TRANSCRIPT_CHUNK` messages and the final `DIAGNOSIS_COMPLETE` payload.
   - `AnnotationCanvas.jsx` — click-to-draw on an HTML5 canvas; normalizes click coordinates
     to `[0,1]` before sending over `/ws/canvas/sync/{session_id}`, and re-draws whatever
     normalized coordinates arrive back from the Redis relay (so the same drawing looks
     correct at any canvas resolution, matching the backend's documented contract).
   - `ProtectedRoute.jsx` — redirects to `/login` when not authenticated.
5. **Pages:** `LoginPage`, `RegisterPage`, `CustomerRoom` (audio widget + canvas),
   `TechnicianConsole` (location/availability + dispatch accept/OTP verify + draw tools),
   `DispatchTracker` (request nearest technician, view returned OTPs).
6. **`App.jsx`** — `react-router-dom` routes, all behind `ProtectedRoute` except
   `/login`/`/register`.
7. **`Dockerfile`** (filled in from empty) — multi-stage: `node:22-alpine` build → static
   files served by `nginx:1.27-alpine`.
8. **`nginx.conf`** (naya) — SPA fallback (`try_files ... /index.html`) plus `/api/` and
   `/ws/` `proxy_pass` to the `backend` service, including the `Upgrade`/`Connection` headers
   WebSocket upgrades need.
9. **`backend/app/main.py`** — added `CORSMiddleware` (wildcard, dev-friendly) so the Vite
   dev server (port 5173) can call the API (port 8000) directly during local development.
10. **`docker-compose.yml`** — uncommented and filled in the `frontend` service (was a stub
    comment since Phase 1, per `docs/BUILD_PLAN.md` session 4).

---

## Kaise verify kiya

Followed the project's `run` skill pattern for a browser-driven app: started the real backend
(`docker compose up -d db redis backend`), started the frontend (both as a Vite dev server on
5173, and separately as the full Dockerized Nginx build), and drove it with a headless
Playwright Chromium instance — not just a build/typecheck pass.

**Dev-server mode (localhost:5173 → localhost:8000):**
1. Registered a real user via the `/register` form, verified redirect to `/login`.
2. Logged in, verified redirect to `/` showing the actual logged-in user's name/role
   (fetched live from `/api/v1/auth/me`).
3. Navigated to Customer Room — confirmed a real `DiagnosticSession` UUID was created via the
   live API and displayed.
4. Clicked "Connect" on the audio widget — confirmed the `/ws/audio/triage/{id}` WebSocket
   opened (button changed to "Start Talking") with zero console errors.
5. Clicked on the annotation canvas — confirmed the draw event round-tripped through
   `/ws/canvas/sync/{id}` (Redis Pub/Sub) with zero console errors.
6. Navigated to Dispatch Tracker, clicked "Request Technician" — got back a real dispatch ID
   and two real OTPs from the live PostGIS KNN + dual-OTP backend.
7. Navigated to Technician Console — confirmed all three sections (location, dispatch
   lifecycle, draw tools) render correctly.

**Docker/Nginx mode (localhost:5173 → nginx → backend container, relative paths, no CORS):**
Repeated the register → login → Customer Room flow entirely through the built, Nginx-served
app — confirmed the `/api/` proxy_pass routes correctly and the flow works identically with
zero console errors, proving the "two different base-URL strategies per environment" logic in
`api.js` is correct in both modes.

All screenshots and console/page-error logs were captured and inspected — no blank frames,
no thrown errors, in either mode.

---

## Bug found & fixed during verification

**CORS was never configured**, so the very first real-browser test (register from the Vite
dev server) failed: the browser's preflight `OPTIONS /api/v1/auth/register` request got back
`405 Method Not Allowed` from FastAPI (no CORS middleware means no route handles `OPTIONS`),
and the actual `POST` never even got sent. This was invisible to `curl`-based testing in every
earlier phase because `curl` doesn't perform the preflight dance — it only shows up when a
real browser drives the app across two origins. Fixed by adding `CORSMiddleware` to
`app/main.py`. This is exactly why the `run` skill insists on browser-driven verification for
web UIs rather than treating a clean `npm run build` as proof the feature works.

---

## Decisions / gotchas (interview-relevant)

- **Two different API base URL strategies, chosen at build/runtime, not hardcoded**: in dev
  (`import.meta.env.DEV`), defaults to `http://localhost:8000` for a fast local loop against
  `docker compose up backend` without needing Nginx. In the Docker/Nginx production build,
  `VITE_API_BASE_URL` is left unset, so the app makes same-origin relative requests and lets
  Nginx's `proxy_pass` do the routing — this is also what makes CORS a non-issue in that mode.
- **`useAudioRecorder` uses `ScriptProcessorNode`, not the newer `AudioWorklet`** — deprecated
  but far simpler to wire without a separate worklet module file, and sufficient for this
  interview-project's scope; a production system would move to `AudioWorklet` to keep the
  resampling off the main thread.
- **CORS is wildcard (`allow_origins=["*"]`)** — acceptable for a project without a fixed
  production frontend domain yet; the code comment flags it as the thing to lock down once a
  real deployed frontend origin exists.

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"How did you verify the frontend actually works, not just that it builds?"** — drove it
  with headless Playwright against the real running backend, in both the Vite dev-server mode
  and the fully Dockerized Nginx-served build, checking for console/page errors and taking
  screenshots at each step; this is also how a CORS misconfiguration was caught that no amount
  of `curl` testing in earlier phases would have surfaced.
- **"Why does the canvas normalize coordinates before sending?"** — same reasoning as the
  backend's `canvas_sync` documentation: a customer's phone and a technician's desktop monitor
  have different resolutions, so raw pixel coordinates would land in the wrong place on the
  other screen; `[0,1]` normalization makes the annotation resolution-independent.

---

## Next

Backend (Phase 1–5) and frontend are both complete and verified. Remaining, per
`docs/ROADMAP.md`: the evaluation/metrics script (`eval/scenarios.json`), and filling
concrete measured numbers into `docs/INTERVIEW_NOTES.md`.
