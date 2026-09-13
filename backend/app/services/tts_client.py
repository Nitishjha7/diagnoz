"""Streaming TTS. Real backend (Piper/ElevenLabs) plugs in behind synthesize_speech_stream;
without TTS_API_KEY configured, yields a synthetic PCM tone per chunk of text so downstream
WebSocket framing/timing can be exercised without a real voice model.
"""
import math
import struct
from typing import AsyncIterator

from app.core.config import settings
from app.services.whisper_client import SAMPLE_RATE_HZ

CHUNK_DURATION_S = 0.2
TONE_HZ = 440


def _generate_tone_chunk(duration_s: float) -> bytes:
    num_samples = int(SAMPLE_RATE_HZ * duration_s)
    samples = [
        int(3000 * math.sin(2 * math.pi * TONE_HZ * i / SAMPLE_RATE_HZ))
        for i in range(num_samples)
    ]
    return struct.pack(f"<{num_samples}h", *samples)


async def synthesize_speech_stream(text: str) -> AsyncIterator[bytes]:
    if not text:
        return

    if settings.TTS_API_KEY:
        # Real provider streaming call would go here.
        pass

    word_count = max(len(text.split()), 1)
    num_chunks = min(max(word_count // 3, 1), 10)
    for _ in range(num_chunks):
        yield _generate_tone_chunk(CHUNK_DURATION_S)
