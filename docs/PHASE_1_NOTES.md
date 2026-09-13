# Phase 1 — Foundation: DB Models, PostGIS, Auth

**Status:** ✅ Complete & verified (`docker compose up` se end-to-end tested)
**Date:** 2026-09-13

---

## Kya banaya

1. **`backend/app/core/`** — `config.py` (typed `.env` settings), `database.py` (SQLAlchemy
   engine + session), `security.py` (JWT + bcrypt hashing), `deps.py` (`get_current_user` +
   `require_roles` RBAC guard).
2. **`backend/app/models/`** — 4 SQLAlchemy models matching `TECHNICAL_SPEC.md` section 4
   exactly: `User`, `TechnicianProfile` (PostGIS `Geometry(POINT, 4326)`), `DiagnosticSession`,
   `ServiceDispatch` (PostGIS geometry too).
3. **`backend/app/schemas/user.py`** — Pydantic request/response models
   (`UserRegister`, `UserLogin`, `UserOut`, `Token`).
4. **`backend/app/api/v1/endpoints/auth.py`** + `router.py` — `/api/v1/auth/{register,login,me}`.
5. **`backend/alembic/`** — `env.py`, `script.py.mako`, and hand-written
   `versions/0001_initial_schema.py`: enables `postgis` + `pgcrypto` extensions, creates all 4
   tables with `CHECK` constraints, and 2 `GIST` indexes on the geometry columns.
6. **`backend/app/main.py`** — wires `api_router` under `/api/v1`, plus `/health`.
7. **`docker-compose.yml`** — `db` (postgis/postgis:16-3.4), `redis`, `minio`, `backend`
   (runs `alembic upgrade head` then `uvicorn`), `worker` (celery). `frontend` left commented
   out (no code there yet).
8. **`backend/Dockerfile`**, **`backend/requirements.txt`** — filled in from empty.

---

## Kaise verify kiya (tu bhi yahi steps se dobara chala sakta hai)

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs backend       # migration ran? uvicorn started?
curl http://localhost:8000/health
```

Register a user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@example.com","phone_number":"9999999999","password":"testpass123","role":"CUSTOMER"}'
```

Login (OAuth2 form, not JSON):

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"
```

Use the `access_token` from the response:

```bash
curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
```

Should return the user; without the header it returns `401`.

Check PostGIS + GIST indexes directly:

```bash
docker exec -it diagnoz-db-1 psql -U diagnoz -d diagnoz -c "\dt"
docker exec -it diagnoz-db-1 psql -U diagnoz -d diagnoz -c "\di"
docker exec -it diagnoz-db-1 psql -U diagnoz -d diagnoz -c "SELECT postgis_version();"
```

All of the above were run during this session and passed.

---

## Decisions / gotchas (interview-relevant)

- **Sync SQLAlchemy (`psycopg2`), not async (`asyncpg`), for Phase 1.** REST auth endpoints
  don't need async DB access; Alembic's sync support is simpler to wire correctly first.
  Async can be introduced later for the high-concurrency WebSocket paths (Phase 2/3) if
  profiling shows it's needed.
- **`role` and status fields are `String` + DB `CHECK` constraint, not a native Postgres
  enum.** Postgres enums are painful to alter in Alembic migrations (`ALTER TYPE ... ADD
  VALUE` can't run inside a transaction in older PG versions); a `VARCHAR` + `CHECK` gives the
  same guarantee and is trivially migratable.
- **`bcrypt` pinned to `4.0.1`.** `passlib==1.7.4` + `bcrypt>=5` breaks at backend-detection
  time with `ValueError: password cannot be longer than 72 bytes` — a known upstream
  incompatibility, not a real 72-byte password. Pin `bcrypt` until passlib ships a fix.
- **`email-validator` had to be added explicitly** — Pydantic's `EmailStr` type imports it
  lazily and raises `ImportError` at model-definition time if it's missing.
- **Host ports moved off the Postgres/Redis defaults (5432/6379 → 5434/6381).** Another
  project on this machine (`webguard-*`) already holds those ports. Internal
  container-to-container traffic still uses `db:5432` / `redis:6379` — only the host-exposed
  ports changed.
- **`frontend` service commented out of `docker-compose.yml`.** `frontend/Dockerfile` is
  empty and there's no React code yet — enabling it now would just break `docker compose up`.
  It gets uncommented in the Frontend phase.

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"Why GEOMETRY not GEOGRAPHY for `current_location`?"** — spec uses `::geography` casts in
  the KNN query for accurate great-circle distance, but the *column* is stored as `GEOMETRY`
  (planar) with SRID 4326 and cast to `geography` only at query time — this is the standard
  PostGIS pattern (cheaper storage/index, accurate distance on demand).
- **"Why hand-write the first migration instead of `alembic revision --autogenerate`?"** —
  no local Python/venv on this machine in this session; autogenerate needs a live DB
  connection and importable models, which only exist inside the Docker network here. The
  migration was hand-written to match the models exactly and was verified against a real
  Postgres instance. Future migrations should use `docker compose exec backend alembic
  revision --autogenerate -m "..."` once the stack is up.
- **"Why `OAuth2PasswordRequestForm` for login instead of a JSON body?"** — it's the
  documented FastAPI convention; it makes Swagger's built-in "Authorize" button work
  out of the box for testing protected endpoints.

---

## Next

Phase 2 — binary audio WebSocket triage (`/ws/audio/triage`): STT → LLM function calling →
TTS. See [ROADMAP.md](ROADMAP.md).
