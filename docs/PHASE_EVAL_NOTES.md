# Evaluation Harness — Measured Numbers, Not Hand-Waved

**Status:** ✅ Complete & run against the real system
**Date:** 2026-09-13

---

## Kya banaya

Per `docs/ROADMAP.md` section A ("proof-of-work" priority — "bana ke chhod diya" vs "maine
measure kiya"):

1. **`eval/scenarios.json`** — 18 labeled triage transcripts (mix of Hindi/Hinglish and
   English, covering AC/refrigerator/washing machine/chiller/water heater, and all three
   urgency levels) + 4 labeled dispatch scenarios (nearest match, unavailable-technician
   skip, out-of-radius no-match, distance tiebreak).
2. **`eval/run_eval.py`** — runs both evals against the **real running system**, not mocks:
   - Calls the actual `app.services.llm_triage.analyze_appliance_issue()` for every triage
     scenario and diffs against the expected labels.
   - For dispatch, creates real `User`/`TechnicianProfile` rows at the scenario's coordinates,
     calls the actual `find_nearest_available_technician()` PostGIS query, and checks the
     match — then cleans up its own fixtures and restores whatever technician-availability
     state existed before it ran.

---

## Measured results

| Metric | Result |
|---|---|
| Triage appliance-type accuracy | **100%** (18/18) |
| Triage urgency accuracy | **88.9%** (16/18) |
| Dispatch KNN precision | **100%** (4/4) |

Full failure detail in `docs/INTERVIEW_NOTES.md` section 3a.

---

## Two real bugs the eval process caught (both fixed)

1. **Substring-matching bug in `llm_triage.py`.** The naive keyword matcher used plain
   `keyword in text_lower`, so the appliance keyword `"ac"` matched as a substring inside
   `"machine"` — every washing-machine transcript containing the word "machine" got
   misclassified as `AC`. First eval run: appliance-type accuracy was only 83.3%. Fixed with
   a word-boundary regex (`\bac\b`) and by checking longer/multi-word keywords first (so
   "washing machine" wins over a coincidental later "washer"/"ac" match). Re-run:
   **100%** appliance-type accuracy.
2. **Eval-harness bug (not app code) in the dispatch eval itself.** The first version of
   `run_dispatch_eval()` never isolated one scenario's fixture technicians from the next
   scenario's KNN query — so scenario `d01`'s "available" technician was still in the DB and
   `is_available=True` when scenarios `d02`–`d04` ran, silently winning their KNN matches
   too. Dispatch precision measured `0%` on the first real run, `25%` after a first partial
   fix (isolating from *pre-existing* demo data but not from *earlier scenarios in the same
   run*), and **100%** after isolating each scenario's fixtures immediately after its
   assertion. This is worth remembering as its own lesson: an eval script that "measures 0%"
   is itself a signal to double-check the eval's own test isolation before assuming the
   underlying feature is broken.

---

## Why the urgency misses were kept as documented limitations, not "fixed" by relabeling

Two of the 18 triage scenarios still fail urgency classification after the substring fix, and
neither was patched over:

- *"AC not working, no cooling, no error, nothing urgent though"* — classified `HIGH` because
  "urgent" appears as a substring even though the sentence negates it. A keyword matcher has
  no concept of negation; only a real LLM call (already wired as the swap-in path in
  `llm_triage.py` behind `settings.LLM_API_KEY`) would get this right.
- *"Mera chiller thoda ajeeb awaaz kar raha hai but chal raha hai theek se"* — classified `LOW`
  because the urgency keyword list is English-only and this sentence has no English urgency
  word at all, despite describing a real (if minor) fault.

Both are genuine, inherent limits of the offline keyword-based fallback described in
`docs/PHASE_2_NOTES.md`, not implementation mistakes — they're left visible in the eval output
specifically so the "swap in a real LLM here" story in the interview has concrete, measured
before/after evidence to point to, rather than a vague claim.

---

## Interview Q&A to add to INTERVIEW_NOTES.md

Already added directly to `docs/INTERVIEW_NOTES.md` (section 3a and the technical Q&A list) —
see there for the ready-to-say version.

---

## Next

Per `docs/ROADMAP.md`, remaining work is entirely documentation polish: keep
`docs/INTERVIEW_NOTES.md` current as anything else changes. All 5 backend phases, the
frontend, and the evaluation harness are complete and verified.
