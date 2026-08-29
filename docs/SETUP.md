# Project Setup Guide — DiagnoZ

Ye document project ko scratch se set up karne ke sare steps cover karta hai — git init se
lekar GitHub pe push karne tak. Jo commands actually chali thi wahi yahan documented hai.

## 1. Folder banao aur git init karo

```bash
cd ~/Music
mkdir diagnoz
cd diagnoz
git init
```

## 2. Folder structure banao

```bash
mkdir -p backend/app/websockets
mkdir -p backend/app/api/v1/endpoints
mkdir -p backend/workers/tasks
mkdir -p frontend/src

touch backend/requirements.txt
touch backend/Dockerfile
touch backend/app/__init__.py
touch backend/app/main.py
touch backend/app/websockets/audio_triage.py
touch backend/app/websockets/canvas_sync.py
touch backend/app/api/v1/endpoints/streaming.py
touch backend/app/api/v1/endpoints/dispatch.py
touch backend/workers/celery_app.py
touch backend/workers/tasks/media_transcode.py
touch frontend/Dockerfile
touch docker-compose.yml
touch README.md
touch .gitignore
```

## 3. .gitignore banao

```bash
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
node_modules/
dist/
.env
*.db
*.log
EOF
```

## 4. README likho

```bash
echo "# DiagnoZ — Real-Time Video Tele-Diagnostic, Voice AI Triage & Field Service Dispatch Platform" > README.md
```

## 5. Git user email set karo

Personal account ke liye email set karna zaroori hai (thinkcurve email se commit na chala jaye).

```bash
git config user.email "nitishkj5019@gmail.com"
```

## 6. Main branch rename + pehla commit

```bash
git branch -M main
git add .
git commit -m "Initial project scaffold - DiagnoZ"
```

## 7. GitHub pe naya empty repo banao

Browser me jaake `diagnoz` naam se naya empty repo banao — bina README/gitignore/license,
warna push ke time history clash hoga.

## 8. Remote add karo (SSH alias ke saath)

`~/.ssh/config` me multiple GitHub accounts ke liye alias set hai (`github-personal`),
isliye remote ko **SSH format** me set karo, `https://` mat use karo alias ke saath.

```bash
git remote add origin git@github-personal:Nitishjha7/diagnoz.git
git push -u origin main
```

## 9. Editor kholo

```bash
code .
```

---

## Common Error: "Port number was not a decimal number"

```
fatal: unable to access 'https://github-personal:Nitishjha7/...': URL rejected:
Port number was not a decimal number between 0 and 65535
```

SSH alias galti se `https://` ke saath mix ho gaya. Fix:

```bash
git remote remove origin
git remote add origin git@github-personal:Nitishjha7/diagnoz.git
git push -u origin main
```

## Common Error: "Repository not found"

GitHub pe repo abhi bana nahi hai ya SSH key register nahi hui. Pehle browser me empty repo
banao, phir dobara push.

---

## Phase-wise branches (optional, interview me acha dikhta hai)

```bash
git checkout -b feature/phase-1-models-auth
git checkout main

git checkout -b feature/phase-2-audio-triage
git checkout main

git checkout -b feature/phase-3-video-engine
git checkout main

git checkout -b feature/phase-4-dispatch-engine
git checkout main

git checkout -b feature/phase-5-media-workers
git checkout main
```

Commit message convention (conventional commits):

```
feat(db):        add sqlalchemy postgis models with spatial indexes
feat(auth):      implement jwt token issuance and rbac dependency guards
feat(websocket): implement 16khz binary pcm audio ingestion pipeline
feat(ai):        integrate streaming whisper stt with fast llm function calling
feat(webrtc):    setup async signaling server for sdp and ice exchange
feat(canvas):    implement normalized coordinate live annotation sync over ws
feat(streaming): build http 206 partial content byte-range video streaming
feat(spatial):   implement postgis knn nearest technician matching
feat(state-machine): enforce atomic dual-otp start and complete transitions
feat(celery):    setup distributed worker tasks with redis broker
feat(media):     build automated ffmpeg hls multi-bitrate transcoder
feat(report):    build automated inspection pdf invoice generation with weasyprint
```

---

## Local run (jab code ready ho)

```bash
cp .env.example .env      # fill LLM_API_KEY, TTS_API_KEY etc.
docker compose up --build
```

Containers: `db` (PostGIS), `redis`, `backend` (FastAPI), `worker` (Celery), `minio`,
`frontend` (React via Nginx).
