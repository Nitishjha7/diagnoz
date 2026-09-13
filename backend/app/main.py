from fastapi import FastAPI

from app.api.v1.router import api_router
from app.websockets.audio_triage import router as audio_triage_router

app = FastAPI(title="DiagnoZ", version="0.1.0")

app.include_router(api_router, prefix="/api/v1")
app.include_router(audio_triage_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
