"""Mock transcription service for offline development."""
from __future__ import annotations

from typing import Any, Dict


async def transcribe(audio_bytes: bytes, sample_rate: int, encoding: str) -> Dict[str, Any]:
    """Return a deterministic transcript for testing without hitting an API."""
    text = "Simulated encounter captured offline."
    return {
        "text": text,
        "segments": [
            {
                "text": text,
                "avg_logprob": 0.0,
                "compression_ratio": 0.0,
                "no_speech_prob": 0.0,
            }
        ],
    }
