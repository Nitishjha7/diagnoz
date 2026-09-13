from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.websockets.audio_triage import router as audio_triage_router
from app.websockets.canvas_sync import router as canvas_sync_router
from app.websockets.webrtc_signaling import router as webrtc_signaling_router

app = FastAPI(title="DiagnoZ", version="0.1.0")

# Dev-friendly wildcard - restrict to the deployed frontend origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(audio_triage_router)
app.include_router(canvas_sync_router)
app.include_router(webrtc_signaling_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
