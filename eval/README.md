# DiagnoZ Evaluation Harness

Measures the system against real, labeled scenarios instead of eyeballing it — see
`../docs/PHASE_EVAL_NOTES.md` for the full writeup and measured results.

## What it measures

1. **Triage extraction accuracy** — runs every transcript in `scenarios.json`'s
   `triage_scenarios` through the real `app.services.llm_triage.analyze_appliance_issue()`
   and checks appliance_type/urgency against labels.
2. **Dispatch KNN precision** — for each `dispatch_scenarios` entry, creates real technician
   rows in the DB at given coordinates, runs the real PostGIS KNN query, and checks it matched
   the expected technician (or nobody, where nobody should be in range).

Both run against the actual running system (real DB, real PostGIS), not mocks. The dispatch
eval temporarily marks any pre-existing technicians unavailable so results aren't skewed by
whatever demo data already exists, then restores everything and deletes its own fixtures —
safe to run against a shared/demo database.

## Running it

```bash
docker compose up -d db redis backend
docker cp eval/run_eval.py <backend-container>:/app/run_eval.py
docker cp eval/scenarios.json <backend-container>:/app/scenarios.json
docker exec <backend-container> python run_eval.py
```

## Adding scenarios

Add entries to `scenarios.json`. Triage scenarios need `transcript` + `expected.appliance_type`
+ `expected.urgency`. Dispatch scenarios need `customer` (lat/lon), a `technicians` list (each
with `name`/`latitude`/`longitude`/`is_available`), and `expected_match` (a technician `name`,
or `null` if none should be within the dispatch radius).
