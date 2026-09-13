# DiagnoZ Frontend

React 19 + Vite demo UI for DiagnoZ. See [../docs/PHASE_FRONTEND_NOTES.md](../docs/PHASE_FRONTEND_NOTES.md)
for what's implemented and how it was verified.

## Local dev

```bash
npm install
npm run dev
```

Runs against `VITE_API_BASE_URL` (defaults to `http://localhost:8000` in dev). Start the
backend stack first: `docker compose up -d db redis backend` from the repo root.

## Docker

Built and served via Nginx as part of the full stack:

```bash
docker compose up --build frontend
```

Nginx proxies `/api/` and `/ws/` to the `backend` service (see `nginx.conf`), so the built
app talks to the API via relative paths — no CORS needed in that mode.

## Pages

- `/login`, `/register` — auth
- `/customer` — CustomerRoom: audio triage widget + live annotation canvas
- `/technician` — TechnicianConsole: location/availability, dispatch OTP lifecycle, draw tools
- `/dispatch` — DispatchTracker: request nearest technician, view OTPs
