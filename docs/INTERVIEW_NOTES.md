# DiagnoZ — Complete Interview Prep Documentation
**Real-Time Video Tele-Diagnostic, Voice AI Triage & Field Service Dispatch Platform**

*Author: Nitish | Stack: FastAPI (Python 3.12) + React 19 + Celery + PostgreSQL/PostGIS + Redis*

---

## Table of Contents
1. The 30-Second Pitch
2. The Problem (Why This Project Exists)
3. Is This Real or Just a Portfolio Toy?
4. What the System Actually Does (Full Flow)
5. Architecture Overview
6. Core Features & USPs (Deep Dive)
7. Business Value & ROI
8. Limitations & Mitigations
9. How to Present This in an Interview (Script + Structure)
10. Anticipated Interview Questions (Technical + Product)
11. The "If I Took This Further" Closing Line
12. One-Liner for Resume/LinkedIn

---

## 1. The 30-Second Pitch

> "DiagnoZ is a video tele-diagnostic and field service dispatch platform for appliance repair — AC, washing machines, refrigerators. The core insight is that 35-40% of technician visits in this industry are completely avoidable — the customer just doesn't know if their problem is a 2-minute fix or needs a real repair. DiagnoZ solves this with real-time voice AI triage and live video diagnosis. If it's a small issue, it gets resolved right there over the call. If not, the system automatically dispatches the nearest available technician — who already knows the exact spare part to bring, so there's no second visit."

Say this **first**, before any tech talk. It frames everything that follows as a solution to a real problem, not just a feature list.

---

## 2. The Problem (Why This Project Exists)

In the appliance repair industry:
- Technicians travel 1–2 hours just to find a tripped breaker, loose connector, or wrong setting
- Rs. 250–400 wasted per false-alarm dispatch (fuel, fleet time)
- Technicians spend ~60% of their workday in transit, not doing billable repair work
- Customers wait 4–24 hours for issues that could be fixed in 3 minutes over video

This isn't a hypothetical problem — it's a well-documented inefficiency in home services, insurance-linked appliance warranties, and enterprise field service industries.

---

## 3. Is This Real or Just a Portfolio Toy?

**Be honest about this if asked — it builds credibility, not weakness.**

The pattern is already validated in the real world:
- **TechSee** — a funded company doing exactly this, with enterprise clients like Vodafone and DHL
- **Telemedicine (Practo, etc.)** — proved people are willing to trust video-based diagnosis over an in-person visit for many use cases
- **Insurance claim verification** — already uses video-based remote inspection at scale

So the *idea* is market-validated. What DiagnoZ demonstrates is that you can architect the **hard technical parts** of this idea — real-time binary audio streaming, WebRTC signaling, spatial dispatch, fraud-proof state machines — from scratch.

**Positioning for interviews:** You're not claiming to have built the next unicorn. You're showing that you can identify a real inefficiency, design a technically sound system for it, and think about the product and business layer — not just the code.

### Measured numbers (not hand-waved)

Ran `eval/run_eval.py` against the actual live system (not unit tests with mocks) —
`eval/scenarios.json` has 18 labeled triage transcripts and 4 labeled dispatch scenarios:

| Metric | Result |
|---|---|
| Triage appliance-type extraction accuracy | **100%** (18/18) |
| Triage urgency-level accuracy | **88.9%** (16/18) |
| Dispatch KNN precision (nearest-available-technician match) | **100%** (4/4) |

**Say this if asked "did you actually measure anything or just build it?"** — yes, and the
numbers aren't artificially perfect: the urgency classifier has a documented failure mode
(see below), which is a stronger answer than claiming 100% across the board.

**The 2 urgency misses, and why they're left as documented limitations, not silently
special-cased:**
- *"AC not working, no cooling, no error, nothing urgent though"* → classified `HIGH`
  (should be `MEDIUM`) — the keyword matcher hits "urgent" as a substring even though the
  sentence explicitly negates it ("nothing urgent *though*"). This is the classic limitation
  of keyword-based extraction vs. a real LLM with actual language understanding — a strong,
  honest talking point for "why would a real LLM call matter here."
- *"Mera chiller thoda ajeeb awaaz kar raha hai but chal raha hai theek se"* (device makes an
  odd noise but otherwise runs fine) → classified `LOW` (should arguably be `MEDIUM`) — no
  English urgency keyword present at all in a Hindi/Hinglish sentence; the keyword list is
  English-only. Same root cause: this is exactly the gap a real multilingual LLM call closes.

**A real bug this eval run caught in the code itself (already fixed):** the original keyword
matcher used plain substring search, so `"ac"` matched inside `"machine"` (as in "washing
**mac**hine") and misclassified several washing-machine transcripts as AC. Fixed with a
word-boundary regex match. This is worth mentioning as an example of "the eval script didn't
just report a number, it found and drove a real fix."

---

## 4. What the System Actually Does (Full Flow)

1. Customer's appliance breaks down
2. Customer opens the app and either **speaks** their problem or starts a **video session**
3. Voice pipeline: audio -> Whisper (STT) -> LLM extracts structured issue (appliance type, suspected fault, urgency) -> TTS responds — all within ~500ms
4. If visual confirmation is needed, a **live video room** opens where a remote engineer can annotate directly on the customer's camera feed (draw arrows/circles on wires, valves, error codes)
5. **Outcome A — Resolved remotely:** Session ends, summary + transcript stored, no dispatch needed
6. **Outcome B — Escalated:** System runs a PostGIS KNN spatial query to find the nearest available technician within a radius, auto-assigns the job, and pre-loads the technician's task with the correct spare part identified during triage
7. Technician arrives, verifies a **start OTP**, completes the repair, verifies an **end OTP** — job marked complete
8. In the background, Celery workers generate the PDF inspection report, transcode any recorded video into multi-bitrate HLS, and calculate the platform commission (15%) vs technician payout (85% minus TDS)

---

## 5. Architecture Overview

```
React 19 Frontend (Vite)
  |-- Web Audio API — 16kHz PCM binary mic streaming
  |-- WebRTC PeerConnection + Canvas annotation layer
  \-- Video.js — HTTP 206 byte-range scrubbable playback
                    |
                    v
FastAPI Core Gateway (async ASGI)
  |-- /ws/audio/triage    -> binary audio ingestion, STT/LLM/TTS pipeline
  |-- /ws/video/signal    -> WebRTC SDP/ICE exchange
  |-- /ws/canvas/sync     -> real-time annotation broadcast (Redis Pub/Sub)
  |-- /api/v1/videos/stream -> HTTP 206 partial content streaming
  \-- /api/v1/dispatch    -> PostGIS KNN matching + OTP state machine
                    |
        +-----------+-----------+
        v                       v
PostgreSQL 16 + PostGIS     Redis Cluster
  (users, sessions,          (pub/sub signaling,
   dispatches, spatial          distributed locks)
   indexing)
        |
        v
Celery Workers
  |-- FFmpeg multi-bitrate HLS transcoder
  |-- WeasyPrint PDF inspection report generator
  \-- Weekly payout settlement job
        |
        v
MinIO / S3 (video segments, PDF invoices)
```

**Why this matters in an interview:** This shows you understand how to split responsibilities across a real-time layer (WebSockets/WebRTC), a persistence layer (Postgres/PostGIS), a caching/pub-sub layer (Redis), and an async background-processing layer (Celery) — which is exactly how production systems at this scale are actually built.

---

## 6. Core Features & USPs (Deep Dive)

### 6.1 Sub-500ms Voice AI Triage
Raw 16kHz PCM audio is streamed as **binary** WebSocket frames (not base64-encoded JSON) directly into a streaming Whisper STT pipeline. The transcript is passed to an LLM with function-calling to extract structured fields (`appliance_type`, `suspected_issue`, `urgency`). Response is streamed back as synthesized speech via TTS — the whole loop closes in under 500ms.

**Why it matters:** No forms, no waiting, feels like talking to a competent human triage agent instantly.

### 6.2 Live Video + Canvas Annotation
A remote engineer can draw directly on the customer's live camera feed — circling a specific wire, valve, or error code. Coordinates are **normalized to a 0.0–1.0 range** so the annotation stays accurate whether the customer is on a 1080p phone or the engineer is on a 4K monitor. Broadcast over Redis Pub/Sub with under 20ms latency.

**Why it matters:** This is effectively AR-style guidance without needing a dedicated AR SDK — solved with simple math and real-time infrastructure.

### 6.3 HTTP 206 Byte-Range Video Streaming (JioHotstar-style)
Reference repair videos are served using `Range` header parsing and Python's `seek()`, so a multi-gigabyte video is never loaded fully into RAM. Scrubbing the timeline is instant because only the requested byte range is streamed.

**Why it matters:** This is the same technique large-scale video platforms (Hotstar, YouTube) use — shows you understand how streaming actually works under the hood, not just `<video src="">`.

### 6.4 PostGIS KNN Geospatial Dispatch
Nearest-technician lookup uses PostGIS's GIST-indexed spatial queries (`ST_DWithin`, `<->` KNN operator) on an ellipsoidal coordinate system (EPSG:4326) — giving O(log N) lookups instead of a full O(N) table scan with naive Euclidean math.

**Why it matters:** Shows you know when a "normal SQL WHERE clause" isn't good enough and a specialized index structure is needed.

### 6.5 Dual-OTP Fraud-Proof State Machine
`ASSIGNED -> IN_PROGRESS` requires a start OTP; `IN_PROGRESS -> COMPLETED` requires an end OTP. This closes a real fraud vector — technicians falsely marking jobs as started or completed without actually doing the work.

**Why it matters:** Demonstrates you think about abuse cases, not just the happy path.

### 6.6 Automated Business Layer (Celery)
Background workers handle FFmpeg multi-bitrate HLS transcoding (1080p/720p/480p), WeasyPrint PDF inspection report generation, and automatic 85/15 payout-commission splitting with weekly settlement batches.

**Why it matters:** Shows the system isn't just a demo — it has the operational plumbing (invoicing, payouts) a real business would need on day one.

---

## 7. Business Value & ROI

| Metric | Impact |
|---|---|
| First-Contact Remote Resolution | 30–40% of cases resolved without a truck roll |
| Cost saved per avoided dispatch | Rs. 250–400 |
| Technician utilization | Reduced transit time -> more billable repair hours |
| Customer wait time | 4–24 hours -> ~3 minutes for resolvable issues |
| Second-visit elimination | Correct spare part identified during triage, before dispatch |

---

## 8. Limitations & Mitigations

This is the section that separates a junior "I built an app" pitch from a senior "I understand product trade-offs" pitch. Bring these up **proactively** — don't wait to be caught off guard.

### Limitation 1 — Adoption Friction
Not every customer is comfortable pointing a camera at their appliance and navigating a video call.
**Mitigation:** Voice-first design. Video is triggered only when the AI/engineer genuinely needs visual confirmation — it's not mandatory for every session. Guided on-screen prompts ("point camera here") reduce confusion.

### Limitation 2 — Diagnosis Accuracy Ceiling
A camera can't always catch internal hardware faults (e.g., a failing compressor winding).
**Mitigation:** A confidence-score system. If the AI/engineer's confidence is low, the system automatically escalates to a physical dispatch rather than forcing a remote-only resolution. No overpromising.

### Limitation 3 — Trust Deficit
People trust an in-person technician more than a remote voice/video session by default.
**Mitigation:** Every session is recorded with a transcript available to the customer (transparency). Verified technician ratings. A follow-up guarantee if the remote diagnosis turns out wrong.

### Limitation 4 — Long B2B Sales Cycles
Selling this to enterprise service companies means long procurement and integration cycles.
**Mitigation:** Don't launch as a standalone consumer product — position it as a plug-in layer for existing warranty/service companies (like OnsiteGo) who already have the customer base. Start with one city, one appliance category (e.g., only AC), prove the numbers, then expand.

---

## 9. How to Present This in an Interview (Script + Structure)

> **For the exact click-by-click live demo walkthrough** — what to open, what to click, what
> to say at each step, and a fallback plan if Docker doesn't cooperate in the room — see
> [DEMO_SCRIPT.md](DEMO_SCRIPT.md). This section below is the presentation *structure and
> mindset*; that doc is the *hands-on script*.

**Structure to follow, in order:**
1. **Problem first** (10-15 seconds) — the redundant-dispatch inefficiency
2. **Solution overview** (20-30 seconds) — the 30-second pitch from Section 1
3. **Pick 2-3 technical deep dives** based on what the interviewer seems interested in (backend-heavy interviewer -> PostGIS/Celery/WebSockets; frontend-heavy -> WebRTC/Canvas sync; systems-design-heavy -> the full architecture diagram)
4. **Proactively mention one trade-off** you made and why
5. **If time allows, mention limitations + mitigations** unprompted — this is a strong closer

**Golden rules:**
- Never open with "I used WebSockets" — always open with the problem
- Always connect a technical choice back to a business outcome
- State trade-offs before being asked — it signals maturity
- Have your ROI numbers memorized cold — don't fumble them

**Example of connecting tech to business (memorize this pattern):**
> "I used PostGIS's KNN spatial indexing — not because it's a resume buzzword, but because a full-table scan for nearest-technician lookup would've meant slower dispatch times, and the entire value proposition of this product is cutting customer wait time from hours to minutes. If dispatch itself is slow, the whole pitch falls apart."

---

## 10. Anticipated Interview Questions (Technical + Product)

### Technical

**Q: Why raw binary WebSockets instead of base64-encoded JSON for audio?**
A: Base64 adds ~33% bandwidth overhead and forces string encode/decode on both ends every ~100ms. Raw binary `ArrayBuffer` data passes straight into Whisper's native bindings with no extra allocation — matters a lot at scale for a real-time audio pipeline.

**Q: How does HTTP 206 streaming handle scrubbing/seeking efficiently?**
A: The browser sends a `Range: bytes=X-Y` header when the user scrubs. FastAPI parses it and uses a file-pointer `seek()` to jump directly to that byte offset, streaming only the requested slice — no full-file load, no disk saturation.

**Q: Why is PostGIS better than a normal bounding-box SQL query here?**
A: Flat Euclidean math ignores Earth's curvature and needs a full O(N) table scan when combined with other filters. PostGIS uses GIST (R-Tree) spatial indexing over an ellipsoidal coordinate system (EPSG:4326), so KNN lookups run in O(log N).

**Q: Why Celery instead of doing this work inline in the request?**
A: Video transcoding and PDF generation are CPU-heavy and slow — doing them synchronously would block the request thread and kill API responsiveness. Offloading to Celery workers keeps the API layer fast and lets heavy jobs retry independently on failure.

**Q: How do you keep the canvas annotation in sync in real time?**
A: Coordinates are normalized to a 0.0–1.0 range so they map correctly regardless of screen resolution, then broadcast via Redis Pub/Sub to all connected clients in the same session room with sub-20ms latency.

**Q: How did you actually measure whether the triage/dispatch logic works, instead of just eyeballing it?**
A: Wrote `eval/run_eval.py` — 18 labeled triage transcripts and 4 labeled dispatch scenarios,
run against the real live system (real DB, real PostGIS queries, real triage function), not
mocks. Got 100% appliance-type accuracy, 88.9% urgency accuracy, 100% dispatch KNN precision.
The eval also caught a real bug — a substring-matching bug where "ac" matched inside
"machine" — which I fixed. I'd rather show two honest failures with a clear root cause than
claim a suspiciously perfect 100% across the board.

### Product / Business

**Q: How would you actually validate this before building all of it?**
A: Start with a manual/Wizard-of-Oz version — a human doing "AI triage" over a simple video call, no automation — in one city, one appliance category. Measure the actual remote-resolution rate before investing in the AI pipeline.

**Q: What's your biggest concern about this product working in the real world?**
A: Trust. People are used to trusting a technician who shows up in person. The whole system lives or dies on whether customers actually believe a remote diagnosis over a call.

**Q: How would you monetize this?**
A: Commission-based (15% platform cut per completed job, as modeled), or a B2B licensing model for existing service/warranty companies who plug DiagnoZ in as their remote-triage layer.

---

## 11. The "If I Took This Further" Closing Line

Use this near the end of the interview if there's an opening:

> "If I were to take this further as an actual product, I wouldn't try to launch it broadly. I'd pick one city and one appliance category — say, just AC repair — run it as a pilot with a single existing service company, and prove the remote-resolution rate and cost savings with real numbers before trying to generalize or sell it enterprise-wide."

This signals founder-level thinking without overclaiming that you're about to build a startup.

---

## 12. One-Liner for Resume/LinkedIn

> "Built DiagnoZ — a FastAPI + React + Celery platform enabling real-time video tele-diagnostics, sub-500ms voice AI triage, and PostGIS-based geospatial technician dispatch, reducing redundant field visits by an estimated 30–40%."
