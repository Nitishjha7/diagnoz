# Demo Script — Interview Me Live Kaise Dikhana Hai

Ye doc sirf ek cheez ke liye hai: **interview room me baithke poora DiagnoZ live demo karna**
— kya khol na hai, kis order me, kya click karna hai, aur har step pe kya bolna hai. Baaki
context (pitch, architecture, Q&A) [INTERVIEW_NOTES.md](INTERVIEW_NOTES.md) me hai — ye doc
sirf **hands-on walkthrough** hai.

**Golden rule:** Demo interview se pehle ek baar poora khud chala ke dekh le. Live me pehli
baar try mat kar.

---

## 0. Interview Se Pehle Taiyari (ghar pe, interview room me nahi)

Ye sab interview se **1 din pehle** kar aur confirm kar le sab kaam kar raha hai:

1. Repo latest hai: `git pull` (agar kahin aur se kaam kiya ho)
2. `.env` file exist karti hai (`.env.example` se copy, agar nayi machine hai)
3. Docker Desktop chalu hai
4. Ek dry-run kar le:
   ```bash
   docker compose up --build
   ```
   Pehli baar 3-5 min lagega (images download + build). Dobara chalane pe 10-15 sec.
5. Confirm kar sab kuch up hai:
   ```bash
   docker compose ps
   ```
   7 services `Up`/`healthy` dikhne chahiye: `db`, `redis`, `minio`, `backend`, `worker`,
   `beat`, `frontend`.
6. Do browser tabs khol ke rakh:
   - `http://localhost:8000/docs` (Swagger — backend proof)
   - `http://localhost:5173` (actual UI — customer/technician experience)
7. Ek baar poora flow khud chala (Section 2-6 niche) taaki interview me koi surprise na aaye.

**Interview room me (agar apna laptop use kar raha hai):**
- Interview shuru hone se 10 min pehle hi `docker compose up -d` chala de (background me),
  taaki jab dikhana ho tab turant ready ho, live wait na karna pade.
- Agar interviewer ka laptop / remote screen-share hai jahan Docker nahi hai, [Section 8](#8-agar-docker-nahi-chal-sakta-fallback-options) dekh.

---

## 1. Opening — Pitch Pehle, Code Baad Me (30 sec)

Screen kuch mat dikhao abhi. Sirf bol:

> "DiagnoZ ek video tele-diagnostic aur field service dispatch platform hai appliance repair
> ke liye — AC, washing machine, fridge. Problem ye hai ki 35-40% technician visits waste
> jaati hain chhoti si cheez ke liye — tripped breaker, loose connector, wrong setting.
> DiagnoZ voice AI se turant triage karta hai, agar chhota issue hai to wahi resolve ho jaata
> hai call pe, warna nearest available technician automatically dispatch hota hai — sahi
> spare part ke saath already identified."

Ab screen share/laptop dikhana shuru kar.

---

## 2. Swagger Se Shuru Kar — "Ye Backend Hai, Ye Real Hai" (1-2 min)

`http://localhost:8000/docs` khol.

**Bol:** "Ye FastAPI ka auto-generated API documentation hai — har endpoint yahin test kar
sakte hain, koi Postman collection alag se nahi chahiye."

Scroll karke dikhao — sections: `auth`, `sessions`, `technicians`, `dispatch`, `streaming`.
Har section ka naam bol de taaki interviewer ko system ka scope samajh aaye.

### 2a. Register + Login (yahin Swagger se)

1. `POST /api/v1/auth/register` expand karo → "Try it out" → body me:
   ```json
   {
     "full_name": "Demo Customer",
     "email": "democustomer@example.com",
     "phone_number": "9999900001",
     "password": "demopass123",
     "role": "CUSTOMER"
   }
   ```
   Execute karo — 201 response dikhao.

2. `POST /api/v1/auth/login` → form fields me email/password bharo → Execute → `access_token`
   copy karo.

3. Top-right **Authorize** button dabao, `Bearer <token>` paste karo (ya sirf token, Swagger
   khud "Bearer" laga dega depending on setup).

**Bol:** "JWT-based auth hai, RBAC ke saath — CUSTOMER, TECHNICIAN, ADMIN roles alag
permissions rakhte hain. Password aur OTP dono bcrypt se hash hote hain, kabhi plaintext
store nahi hota."

### 2b. Session Create Karo

`POST /api/v1/sessions` → Execute → response me `id` milega (UUID). **Ye copy kar lo**, agle
step me chahiye.

---

## 3. Voice Triage — Asli "Wow" Moment (2 min)

Ab dusre tab pe jao: `http://localhost:5173`.

1. Login karo (wahi email/password jo Swagger se register kiya).
2. **Customer Room** click karo — ye automatically ek naya session bana dega (ya tu apna wala
   URL me daal sakta hai agar specific session dikhana hai).
3. "Connect" button dabao — WebSocket connect hoga, button "Start Talking" ban jaayega.
4. **Bol:** "Ye `/ws/audio/triage` WebSocket hai — browser raw 16kHz PCM audio bhejta hai,
   base64 nahi, isse 33% bandwidth aur encode/decode overhead bachta hai."
5. "Start Talking" dabao, kuch bolo (mic permission browser maangega, allow karo) — jaise
   "Mera AC cooling nahi kar raha aur awaaz aa rahi hai compressor se".
6. "Finish Speaking" dabao.
7. Live transcript chunk aur phir **Diagnosis card** dikhega: appliance_type, suspected_issue,
   urgency.

**Bol:** "Ye pipeline hai: audio → Speech-to-Text → LLM function calling se structured data
nikalta hai (appliance type, issue, urgency) → Text-to-Speech se wapas bolke batata hai —
poora loop 500ms ke andar. Abhi maine offline/deterministic fallback rakha hai bina kisi paid
API key ke, taaki demo hamesha chale — real Whisper/GPT/ElevenLabs plug karna sirf ek config
badalna hai, poora contract wahi rehta hai."

**Agar interviewer poochein "ye real AI hai ya scripted":** Honestly bol do — "Abhi keyword-
based deterministic extractor hai jo offline chalta hai demo ke liye reliable rehne ke liye.
Maine ise measure bhi kiya hai — 100% appliance accuracy, 88.9% urgency accuracy [Section 6
dekh]. Real LLM call wahi function ke andar jaani hai, architecture already us hisaab se bana
hai (`FUNCTION_SCHEMA` already defined hai LLM function-calling ke liye)."

---

## 4. Live Annotation Canvas (1 min, optional agar time kam ho)

Same Customer Room page pe, "Live Annotation" section me canvas pe click karo — ek dot ban
jaayega.

**Bol:** "Ye WebRTC video room ka annotation layer hai — remote engineer customer ki live
video pe arrow/circle draw kar sakta hai. Coordinates `[0,1]` range me normalize hote hain
taaki chahe customer 4K monitor pe ho ya phone pe, drawing sahi jagah lande. Redis Pub/Sub se
broadcast hota hai, isliye multiple backend instances ke beech bhi sync rehta."

Agar time ho to Technician Console bhi ek tab me khol ke same session ID daal, dono canvas pe
sync hote dikha sakta hai (2 browser windows side-by-side).

---

## 5. Geospatial Dispatch + Dual-OTP (2 min — dusra strong technical point)

### 5a. Technician Setup

1. Ek naya tab/incognito window me `localhost:5173/register` — TECHNICIAN role se register
   karo.
2. Login karo, **Technician Console** khol.
3. "My Location" me lat/long daal (default Delhi coords already bhare hain) → "Save Location".

**Bol:** "Ye PostGIS `GEOMETRY(Point, 4326)` column me store hota hai, GIST spatial index ke
saath."

### 5b. Dispatch Request (Customer side)

1. Customer wale tab me **Dispatch Tracker** khol.
2. Coordinates daal (technician ke paas wale — demo ke liye pehle se bhare hain) → "Request
   Technician".
3. Response me Dispatch ID + Start OTP + End OTP dikhega.

**Bol:** "Backend ne PostGIS KNN query chalayi — `ST_DWithin` se 5km radius filter, `<->`
operator se nearest-neighbor ordering, GIST index ki wajah se ye O(log N) hai, na ki full
table scan. Isi ke saath Redis distributed lock lagta hai taaki do dispatch requests ek hi
technician ko double-book na kar sakein."

### 5c. Dual-OTP Lifecycle (Technician side)

1. Technician Console me "Dispatch Lifecycle" section me Dispatch ID paste karo → "Load".
2. "Accept" dabao — status `PENDING → ACCEPTED`.
3. Start OTP daal ke verify karo — status `ACCEPTED → IN_PROGRESS`.
4. End OTP daal ke verify karo — status `IN_PROGRESS → COMPLETED`.

**Bol:** "Ye dual-OTP fraud-proof state machine hai — technician bina customer se OTP liye na
job start dikha sakta hai na complete. Completion pe automatically 15% platform commission
aur 85% minus 1% TDS technician payout calculate hota hai."

---

## 6. Numbers Bol — Closing Se Pehle (1 min, bahut strong hai)

Ye section skip mat karna — yahi "junior vs senior" wala differentiator hai.

**Bol:** "Maine ye sab sirf bana ke nahi chhoda — measure bhi kiya hai. `eval/run_eval.py`
naam ka script hai jo 18 labeled voice-triage transcripts aur 4 labeled dispatch scenarios
real system ke against chalata hai — mock nahi, real DB, real PostGIS query."

Numbers bol (yaad rakh, cold bolna hai):
- **Appliance-type extraction accuracy: 100%**
- **Urgency-level accuracy: 88.9%**
- **Dispatch KNN precision: 100%**

**Agar poochein "baaki 11% kyun miss hua":** "Do genuine cases hain jahan keyword-based
matcher fail hota hai — ek me sentence negation hai ('nothing urgent though' — 'urgent' word
match ho gaya but matlab ulta tha), doosre me Hindi sentence me koi English urgency keyword
hi nahi tha. Ye exactly wahi gap hai jo real LLM call band karega — maine ise chhupaya nahi,
documented rakha hai [docs/PHASE_EVAL_NOTES.md](PHASE_EVAL_NOTES.md) me."

**Bonus point agar pooche "koi bug mila is process me":** "Haan — eval chalane se ek real
substring-matching bug pakda: keyword 'ac' 'machine' word ke andar bhi match ho raha tha
('m**ac**hine'), isliye washing-machine transcripts galat AC classify ho rahe the. Word-
boundary regex se fix kiya, accuracy 83% se 100% pahunchi."

---

## 7. Closing Line

> "Agar ise aage le jaata to poora product launch nahi karta — ek city, ek appliance category
> (jaise sirf AC) me ek existing service company ke saath pilot karta, real remote-resolution
> rate aur cost savings prove karta, phir generalize karta."

---

## 8. Agar Docker Nahi Chal Sakta — Fallback Options

Interview room me kabhi Docker na chale ya internet slow ho, to ye backup plan:

1. **Screenshots/recording le rakh pehle se** — is session me maine already Playwright se
   screenshots liye the (register, login, home, customer room, dispatch, technician console).
   Wahi ek chhota recording/GIF bana ke apne paas rakh — agar live demo fail ho jaye to
   "dekho ye maine already chala ke test kiya tha" bol ke dikha sakta hai.
2. **Sirf terminal se curl commands** — agar UI na chale bhi to backend akela curl se demo ho
   sakta hai. [PHASE_1_NOTES.md](PHASE_1_NOTES.md) se [PHASE_5_NOTES.md](PHASE_5_NOTES.md)
   tak har phase doc me exact curl commands hain jo maine khud test kiye the — unhi ko copy-
   paste kar sakta hai.
3. **Code walkthrough as backup** — agar kuch bhi live na chale, seedha code khol ke
   [CODE_NOTES.md](CODE_NOTES.md) follow kar — har file ka "kya/kyun" already likha hai,
   confidently explain kar sakta hai bina live demo ke bhi.

**Sabse important:** Agar live demo fail ho jaye, ghabrana mat. Bol de "Local pe already test
kiya hai, abhi environment issue hai" aur code/architecture explain karne pe switch kar jaa —
interviewer zyada dhyaan isi baat pe deta hai ki tu system samajhta hai ki nahi, live demo
sirf bonus hai.

---

## Quick Reference — Sab Commands Ek Jagah

```bash
# Setup (ek baar)
cp .env.example .env

# Start everything
docker compose up -d

# Check status
docker compose ps

# Logs agar kuch atke
docker compose logs backend --tail=50
docker compose logs frontend --tail=50

# Stop everything (demo khatam hone ke baad)
docker compose down
```

| URL | Kya hai |
|---|---|
| http://localhost:5173 | Frontend (asli demo yahin) |
| http://localhost:8000/docs | Swagger — backend proof |
| http://localhost:9003 | MinIO console (agar object storage dikhana ho) |
