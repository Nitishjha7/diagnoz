# Phase 4 — Geospatial Dispatch & Dual-OTP State Machine

**Status:** ✅ Complete & verified (full lifecycle tested against `docker compose`)
**Date:** 2026-09-13

---

## Kya banaya

1. **`backend/app/services/spatial_matcher.py`** (naya) —
   - `find_nearest_available_technician()`: raw SQL (via `sqlalchemy.text`) PostGIS KNN
     query — `is_available = TRUE` + `ST_DWithin(...::geography, radius_m)` (hard 5km radius
     filter, GIST-index-assisted) + `ORDER BY current_location <-> point` (KNN `<->` operator,
     index-assisted nearest-neighbor) + `LIMIT 1`. Returns `technician_profiles.user_id` (not
     the profile's own `id` — this matters, see gotcha below).
   - `acquire_technician_lock()` / `release_technician_lock()`: Redis `SET NX EX` /
     `DELETE` — `lock:technician:{user_id}` held for `DISPATCH_LOCK_TTL_SECONDS` (300s) so two
     concurrent dispatch requests can't both claim the same technician.
2. **`backend/app/api/v1/endpoints/technicians.py`** (naya) —
   `POST /me/profile` (create/update technician's own geo-profile), `PATCH /me/location`,
   `PATCH /me/availability`. All `TECHNICIAN`-role-only.
3. **`backend/app/api/v1/endpoints/dispatch.py`** (filled in from empty) — full dual-OTP
   lifecycle:
   - `POST /dispatch` (CUSTOMER) — KNN match → Redis lock → generate + hash both OTPs →
     create `ServiceDispatch` row `PENDING` → **plaintext OTPs returned once** in the response
     (never stored plaintext; the DB only ever has bcrypt hashes).
   - `POST /dispatch/{id}/accept` (TECHNICIAN, assigned only) — `PENDING → ACCEPTED`, marks
     the technician profile `is_available = False` so KNN won't match them again mid-job.
   - `POST /dispatch/{id}/verify-start-otp` — `ACCEPTED → IN_PROGRESS`, only if the OTP
     matches the bcrypt hash.
   - `POST /dispatch/{id}/verify-end-otp` — `IN_PROGRESS → COMPLETED`, computes
     `platform_commission_fee` (15%) and `technician_earnings` (85% minus 1% TDS) from
     `total_service_fee`, sets `completed_at`, restores `is_available = True`, and releases
     the Redis lock.
4. **`core/security.py`** — added `generate_otp()` (`secrets.randbelow`, cryptographically
   secure 6-digit code), `hash_otp()` / `verify_otp()` (reuse the same bcrypt primitive as
   passwords — no need for a separate hashing scheme).
5. **`schemas/dispatch.py`**, **`schemas/technician.py`** — request/response models.
6. **`requirements.txt`** — added `shapely` (geoalchemy2's `from_shape()` helper needs it to
   build `POINT` geometries from lat/lon in Python).

---

## Kaise verify kiya

Full lifecycle run against `docker compose`:

1. Registered a technician, set their profile location to Delhi coordinates
   (`28.6139, 77.2090`) via `POST /technicians/me/profile`.
2. Registered a customer, called `POST /dispatch` with a nearby point
   (`28.6150, 77.2100`, ~150m away) → got back a `PENDING` dispatch + plaintext
   `start_otp`/`end_otp`.
3. **No-match case**: called `POST /dispatch` from Mumbai coordinates (`19.0760, 72.8777`,
   >1000km away) → correctly `404 No available technician found within 5000m`.
4. **Distributed lock**: immediately called `POST /dispatch` again for the same nearby point
   while the first dispatch's lock was still held → correctly `409 Nearest technician is
   currently being assigned to another job`. Confirmed via `redis-cli TTL` that the lock key
   existed with ~260s remaining.
5. **Dual-OTP happy path**: `accept` (`PENDING→ACCEPTED`) → `verify-start-otp` with a wrong
   code (`400 Invalid start OTP`) → with the correct code (`ACCEPTED→IN_PROGRESS`) →
   `verify-end-otp` with the correct code (`IN_PROGRESS→COMPLETED`, `completed_at` set).
6. **Lock release + re-availability**: after completion, `redis-cli EXISTS` on the lock key
   returned `0` (released), and a brand new `POST /dispatch` for the same technician
   succeeded immediately — proving `is_available` was restored and the lock was freed.

---

## Bug found & fixed during verification

**KNN query returned the wrong ID.** `service_dispatches.technician_id` is a foreign key to
`users.id` (per the schema — a dispatch references a *user*, not a technician profile row),
but the first version of `find_nearest_available_technician()` selected
`technician_profiles.id` (the profile's own primary key). Creating a dispatch then failed
with `IntegrityError: ForeignKeyViolation` because that profile ID doesn't exist in `users`.
Fixed by selecting `user_id` instead. This is exactly the kind of foreign-key-direction bug
that only shows up when you actually run the flow end-to-end — caught here because Phase 4
was verified with real HTTP calls, not just read over.

---

## Decisions / gotchas (interview-relevant)

- **Why `ST_DWithin(...::geography, ...)` for the radius filter but `<->` (no cast) for
  ORDER BY** — `::geography` cast gives accurate great-circle distance in meters for the hard
  radius cutoff (correctness matters here — a wrong cutoff either misses or wrongly includes
  a technician). The `<->` KNN operator on the raw `geometry` column is what lets PostgreSQL
  use the GIST index for fast nearest-neighbor ordering (index-assisted `O(log N)`); casting
  to geography there would prevent the index from being used for ordering. This is the
  standard PostGIS pattern: geometry index for ordering, geography cast for the distance
  guarantee.
- **OTPs are returned in the API response exactly once** (at dispatch creation) and never
  stored in plaintext anywhere — only `bcrypt` hashes live in the DB. In a real product this
  would go out via SMS instead of the HTTP response; returning it here is a simplification for
  a project without an SMS provider.
- **Distributed lock TTL is a safety net, not the primary "is this tech busy" signal** — the
  primary signal is `technician_profiles.is_available`, flipped to `False` on `accept` and
  back to `True` on completion. The Redis lock only covers the narrow race window between "KNN
  found technician X" and "the dispatch row referencing X is committed" — without it, two
  near-simultaneous dispatch requests could both KNN-match the same still-`is_available=True`
  technician before either one's DB write lands.
- **Role + ownership checks stack on every dispatch transition** (`require_roles("TECHNICIAN")`
  AND `dispatch.technician_id == current_user.id`) — RBAC alone isn't enough here; any
  technician could otherwise complete someone else's job.

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"Why is the Redis lock keyed by technician, not by dispatch?"** — the problem it solves is
  "don't let two dispatch requests grab the *same technician*", which is a property of the
  technician, not of a not-yet-created dispatch row.
- **"What if the lock expires (TTL) before the customer or technician acts?"** — the lock only
  protects the assignment race at creation time; once a dispatch row exists (even `PENDING`),
  the technician's `is_available` flag (persistent DB state, no TTL) is what actually keeps
  them out of future KNN matches until `accept`. If `accept` never happens, that's an
  operational timeout to handle separately (not built in this phase — noted as a gap).
- **"Why hash OTPs with the same bcrypt scheme as passwords instead of a lighter hash?"** —
  simplicity: one hashing primitive, one dependency, no reason to introduce a second scheme
  for a 6-digit code when bcrypt's cost factor is irrelevant at this volume.

---

## Next

Phase 5 — Celery workers: FFmpeg HLS transcode, WeasyPrint inspection PDF, weekly payout
settlement batch. See [ROADMAP.md](ROADMAP.md).
