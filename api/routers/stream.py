"""WebSocket stream for audio transcription and code suggestions."""
from __future__ import annotations

import json
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..schemas import WsCodesUpdate, WsSttFinal, WsSttPartial
from ..services.stt import mock_stt, openai_stt
from .llm_codes import suggest_for_ws

router = APIRouter(prefix="", tags=["stream"])


@router.websocket("/stream")
async def stream_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    audio_chunks: list[bytes] = []
    sample_rate = 16000
    encoding = "opus"
    session_start = time.perf_counter()
    transcript_accum = []

    try:
        while True:
            message = await websocket.receive()
            if "type" in message and message["type"] == "websocket.disconnect":
                break
            if message.get("text"):
                payload = json.loads(message["text"])
                event_type = payload.get("type")
                if event_type == "audio_start":
                    sample_rate = payload.get("sampleRate", sample_rate)
                    encoding = payload.get("encoding", encoding)
                    audio_chunks.clear()
                elif event_type == "audio_stop":
                    audio_bytes = b"".join(audio_chunks)
                    start = time.perf_counter()
                    transcriber = mock_stt if settings.stt_provider.lower() == "mock" else openai_stt
                    stt_response = await transcriber.transcribe(audio_bytes, sample_rate, encoding)
                    text = stt_response.get("text", "")
                    transcript_accum.append(text)
                    elapsed = int((time.perf_counter() - session_start) * 1000)
                    stt_final = WsSttFinal(text=text, startMs=0, endMs=elapsed)
                    await websocket.send_json({"type": "stt_final", "payload": stt_final.model_dump()})
                    suggestion_start = time.perf_counter()
                    suggestions = await suggest_for_ws("\n".join(transcript_accum))
                    latency = int((time.perf_counter() - suggestion_start) * 1000)
                    update = WsCodesUpdate(
                        candidates=suggestions.candidates,
                        rationale="LLM + rules",
                        latencyMs=latency,
                    )
                    await websocket.send_json({"type": "codes_update", "payload": update.model_dump()})
                elif event_type == "ping":
                    await websocket.send_json({"type": "pong"})
            elif message.get("bytes"):
                audio_chunks.append(message["bytes"])
                if len(audio_chunks) % 10 == 0:
                    partial_text = ""  # optionally send partials when available
                    elapsed = int((time.perf_counter() - session_start) * 1000)
                    partial = WsSttPartial(text=partial_text, startMs=0, endMs=elapsed)
                    await websocket.send_json({"type": "stt_partial", "payload": partial.model_dump()})
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
        except Exception:  # pragma: no cover - defensive cleanup
            pass
