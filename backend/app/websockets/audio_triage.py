import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import SessionLocal
from app.models.session import DiagnosticSession
from app.services.llm_triage import analyze_appliance_issue
from app.services.tts_client import synthesize_speech_stream
from app.services.whisper_client import transcribe_audio_chunk

router = APIRouter()

# ~1.5s of audio at 16kHz 16-bit mono PCM = 48,000 bytes
TRIAGE_BUFFER_THRESHOLD_BYTES = 48_000


@router.websocket("/ws/audio/triage/{session_id}")
async def audio_triage_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    audio_buffer = bytearray()
    full_transcript_parts: list[str] = []

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                audio_buffer.extend(message["bytes"])
                if len(audio_buffer) >= TRIAGE_BUFFER_THRESHOLD_BYTES:
                    current_pcm = bytes(audio_buffer)
                    audio_buffer.clear()
                    partial = await transcribe_audio_chunk(current_pcm)
                    if partial.strip():
                        full_transcript_parts.append(partial)
                        await websocket.send_json({"type": "TRANSCRIPT_CHUNK", "text": partial})

            elif message.get("text") is not None:
                spoken_text = message["text"] or " ".join(full_transcript_parts)
                diagnosis = await analyze_appliance_issue(spoken_text)

                db = SessionLocal()
                try:
                    try:
                        session_uuid = uuid.UUID(session_id)
                    except ValueError:
                        session_uuid = None

                    session = db.get(DiagnosticSession, session_uuid) if session_uuid else None
                    if session is not None:
                        session.voice_transcript = spoken_text
                        session.ai_structured_summary = {
                            "appliance_type": diagnosis["appliance_type"],
                            "suspected_issue": diagnosis["suspected_issue"],
                            "urgency": diagnosis["urgency"],
                        }
                        db.add(session)
                        db.commit()
                finally:
                    db.close()

                await websocket.send_json({"type": "DIAGNOSIS_COMPLETE", "payload": diagnosis})

                async for audio_packet in synthesize_speech_stream(diagnosis["voice_summary"]):
                    await websocket.send_bytes(audio_packet)

    except WebSocketDisconnect:
        pass
