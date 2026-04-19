"""
Wraps faster-whisper for async streaming transcription.
Audio chunks arrive as float32 numpy arrays at 16 kHz mono.
"""
import asyncio
from collections.abc import AsyncIterator

import numpy as np
from faster_whisper import WhisperModel


class STTPipeline:
    def __init__(self, model_size: str = "medium", device: str = "cuda") -> None:
        self._model = WhisperModel(model_size, device=device, compute_type="float16" if device == "cuda" else "int8")

    async def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        """Transcribe a single audio chunk. Runs in thread pool to avoid blocking."""
        loop = asyncio.get_running_loop()
        segments, _ = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                audio,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            ),
        )
        return " ".join(seg.text.strip() for seg in segments if seg.text.strip())
