"""Streaming STT. Real backend (faster-whisper) plugs in behind transcribe_audio_chunk;
without WHISPER_MODEL configured for a real engine, falls back to a stub so the pipeline
is runnable and testable without a GPU / model download.
"""
import audioop

SAMPLE_RATE_HZ = 16_000
SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM


async def transcribe_audio_chunk(pcm_bytes: bytes) -> str:
    if not pcm_bytes:
        return ""

    rms = audioop.rms(pcm_bytes, SAMPLE_WIDTH_BYTES)
    if rms < 50:
        return ""

    duration_s = len(pcm_bytes) / (SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES)
    return f"[{duration_s:.1f}s of audio detected, rms={rms}]"
