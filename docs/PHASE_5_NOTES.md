# Phase 5 — Celery Media, Invoicing & Payout Pipeline

**Status:** ✅ Complete & verified (all 3 tasks run for real against `docker compose`)
**Date:** 2026-09-13

---

## Kya banaya

1. **`backend/workers/storage.py`** (naya) — shared `boto3` S3/MinIO helper:
   `get_s3_client()`, `ensure_bucket()` (create-if-missing), `upload_directory()` (recursive,
   for HLS output), `upload_file()` (single file, for PDFs).
2. **`backend/workers/tasks/media_transcode.py`** (filled in) — `tasks.transcode_to_hls`:
   FFmpeg multi-bitrate HLS (1080p/720p/480p) → uploads the whole output directory to
   `hls/{session_id}/` in MinIO.
3. **`backend/workers/tasks/report_generate.py`** (naya) — `tasks.generate_report`: renders
   an HTML inspection report (customer/technician, diagnosis, transcript, parts replaced,
   billing breakdown) via WeasyPrint into a PDF, uploads to `reports/{dispatch_id}.pdf`.
4. **`backend/workers/tasks/payout_settle.py`** (naya) — `tasks.settle_payouts`: finds every
   `COMPLETED` dispatch with `settled_at IS NULL`, credits `technician_earnings` onto that
   technician's `wallet_balance`, stamps `settled_at`. Idempotent — a re-run only touches
   still-unsettled rows.
5. **`backend/app/models/dispatch.py`** + **`alembic/versions/0002_add_settled_at.py`** —
   added a `settled_at` nullable timestamp column (see gotcha below for why).
6. **`backend/workers/celery_app.py`** — registered all 3 new tasks in `include=[...]`, added
   `beat_schedule` (`crontab(hour=2, minute=0, day_of_week=1)` — every Monday 02:00 — for the
   weekly payout job).
7. **`docker-compose.yml`** — new `beat` service (`celery -A workers.celery_app beat`),
   `worker` gets a `diagnoz_media` volume for local scratch space before S3 upload.
8. **`backend/Dockerfile`** — added `ffmpeg` and WeasyPrint's system deps (`libpango`,
   `libcairo`, `libgdk-pixbuf`, etc.) to the apt install.
9. **`requirements.txt`** — `boto3`, `weasyprint`, `pydyf==0.10.0` (pinned, see gotcha).

---

## Kaise verify kiya

All three tasks were invoked directly (`.apply().get()`, synchronous) inside the running
`worker` container against real dependencies — not mocked:

1. **Transcode**: generated a real 2-second test video with `ffmpeg -f lavfi` inside the
   container, ran `transcode_recording_to_hls`, confirmed 3 real renditions
   (`segment_0/1/2_000.ts` + `stream_0/1/2.m3u8` + `master.m3u8`) were produced on disk *and*
   present in MinIO (`list_objects_v2` returned all 7 files under `hls/test-session-1/`).
2. **Report**: ran `generate_inspection_report` with sample dispatch data, downloaded the
   resulting object back from MinIO, confirmed it starts with the real PDF magic bytes
   (`%PDF-`) and is a non-trivial size (9.4KB).
3. **Payout**: created a full dispatch lifecycle via the live API (register → technician
   profile → dispatch → accept → both OTPs → `COMPLETED` with `total_service_fee=1000`,
   yielding `technician_earnings=841.5`), ran `settle_weekly_payouts`, confirmed via
   `GET /technicians/me/availability`-adjacent wallet check that `wallet_balance` went from
   `0` to `841.5` and the dispatch's `settled_at` was stamped. Ran the task a second time and
   confirmed `settled_count: 0` — idempotent, no double-crediting.

---

## Bugs found & fixed during verification

1. **The spec's own reference FFmpeg command doesn't work.** Repeating `-vf scale=...` once
   per output rendition (as in `docs/TECHNICAL_SPEC.md` section 6.D) only keeps the *last*
   `-vf` — FFmpeg does not fan a single `-vf` option out across multiple `-c:v:N` outputs the
   way it does for codec/bitrate options. The result was `hls: Unable to map stream at v:1`
   and zero output. Fixed with `-filter_complex "[0:v]split=3[v1][v2][v3];[v1]scale=...
   [v1out];..."` plus explicit `-map [v1out]` / `-map [v2out]` / `-map [v3out]` per rendition —
   this is the correct way to derive multiple independently-scaled outputs from one input in
   a single FFmpeg invocation. This is exactly the kind of bug that only surfaces by actually
   running the command against a real video file, not by reading the spec.
2. **`weasyprint==62.3` + latest `pydyf` (0.12.1) are incompatible** —
   `AttributeError: 'super' object has no attribute 'transform'` at PDF-write time, a known
   breaking API change in `pydyf` that WeasyPrint 62.3 hasn't caught up to. Pinned
   `pydyf==0.10.0` explicitly in `requirements.txt`.
3. **MinIO's Docker Hub image (`minio/minio`) is gone** — MinIO stopped publishing to Docker
   Hub; `docker-compose.yml` now pulls from `quay.io/minio/minio:latest` instead.
4. **Debian trixie (the `python:3.12-slim` base image) renamed `libgdk-pixbuf2.0-0`** to
   `libgdk-pixbuf-2.0-0` — updated the Dockerfile's apt package list.
5. **`dispatch_status` was almost overloaded with a non-schema `SETTLED` value** — caught
   before it shipped: the DB `CHECK` constraint only allows `PENDING/ACCEPTED/IN_PROGRESS/
   COMPLETED/CANCELLED`. Settlement is a separate concern from the job lifecycle, so a new
   `settled_at` nullable timestamp column was added instead via a proper Alembic migration
   (`0002`), keeping `dispatch_status` semantics unchanged.

---

## Decisions / gotchas (interview-relevant)

- **Every worker task validates against real infrastructure in this project (FFmpeg, WeasyPrint,
  MinIO), not mocks** — consistent with the offline-first-but-real philosophy from Phase 2:
  the code paths that run in `docker compose up` are the same code paths verified here, no
  separate "test-only" implementation to drift out of sync.
- **`beat` runs as its own Compose service, not folded into `worker`** — Celery's own
  guidance: exactly one `beat` process should run scheduling (running it twice double-fires
  scheduled tasks), while `worker` can be scaled to N replicas independently.
- **`payout_settle` uses `settled_at IS NULL` as the "needs settlement" filter**, not a
  time-window ("last 7 days") — simpler and correct regardless of how often the beat schedule
  actually fires (e.g. if the worker was down for two weeks, the next run catches up on
  everything, rather than silently skipping older completed jobs).

---

## Interview Q&A to add to INTERVIEW_NOTES.md

- **"Walk me through a real bug you hit and fixed."** — the FFmpeg `-filter_complex` fix
  above: the naive per-output `-vf` approach silently drops two of the three renditions
  because FFmpeg only keeps the last repeated flag; `split` + per-branch `scale` + explicit
  `-map` is the correct pattern for deriving N renditions from one input in a single pass
  (avoids decoding the source N times).
- **"Why is HLS output uploaded to S3 from the worker, not streamed live?"** — Phase 5 is VOD
  (post-session) transcoding of a completed recording, distinct from Phase 3's live WebRTC
  session — the recording only exists once the session has ended, so there's no live-streaming
  angle here to argue against.
- **"Why a separate `settled_at` column instead of a `SETTLED` dispatch status?"** — job
  lifecycle (was the technician physically there, verified by OTP) and financial settlement
  (has the platform paid out) are different state machines that can evolve independently
  (e.g. a dispute after completion shouldn't need to un-COMPLETE the job) — conflating them
  into one status field would make either concern harder to reason about or migrate later.

---

## Next

Frontend demo UI (React 19 + Vite) + end-to-end wiring — see [ROADMAP.md](ROADMAP.md) and
[BUILD_PLAN.md](BUILD_PLAN.md) session 4.
