"""
Handles WebRTC signaling and audio ingest from the church admin.
Admin browser sends an SDP offer; we return an answer.
The resulting audio track feeds directly into the STT pipeline.
"""
import asyncio
import logging

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription
from av import AudioFrame

from app.pipeline.hub import hub
from app.pipeline.stt import STTPipeline
from app.pipeline.translate import LANG_CODES, NLLBTranslator
from app.pipeline.verses import get_verse

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHUNK_SECONDS = 4


class AudioProcessor:
    """Accumulates PCM frames and dispatches to STT+translate pipeline."""

    def __init__(self, session_code: str, source_lang: str, stt: STTPipeline, translator: NLLBTranslator) -> None:
        self.code = session_code
        self.source_lang = source_lang
        self._stt = stt
        self._translator = translator
        self._buffer = np.zeros(0, dtype=np.float32)

    def add_frame(self, frame: AudioFrame) -> None:
        pcm = frame.to_ndarray().astype(np.float32) / 32768.0
        if pcm.ndim > 1:
            pcm = pcm.mean(axis=0)
        self._buffer = np.concatenate([self._buffer, pcm])

        if len(self._buffer) >= SAMPLE_RATE * CHUNK_SECONDS:
            chunk = self._buffer[: SAMPLE_RATE * CHUNK_SECONDS]
            self._buffer = self._buffer[SAMPLE_RATE * CHUNK_SECONDS :]
            asyncio.create_task(self._process(chunk))

    async def _process(self, audio: np.ndarray) -> None:
        try:
            text = await self._stt.transcribe(audio, language=self.source_lang)
            if not text:
                return

            verse = await get_verse(text)

            tasks = {
                lang: self._translator.translate(text, self.source_lang, lang)
                for lang in LANG_CODES
                if lang != self.source_lang
            }
            translations = {self.source_lang: text}
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for lang, result in zip(tasks.keys(), results):
                if isinstance(result, str):
                    translations[lang] = result

            await hub.broadcast(
                self.code,
                {"type": "caption", "translations": translations, "source_lang": self.source_lang, "verse": verse},
            )
        except Exception:
            logger.exception("Error in audio processing for session %s", self.code)


async def handle_offer(
    sdp: str,
    sdp_type: str,
    session_code: str,
    source_lang: str,
    stt: STTPipeline,
    translator: NLLBTranslator,
) -> dict:
    pc = RTCPeerConnection()
    processor = AudioProcessor(session_code, source_lang, stt, translator)

    @pc.on("track")
    def on_track(track):
        if track.kind != "audio":
            return

        @track.on("ended")
        def on_ended():
            logger.info("Audio track ended for session %s", session_code)

        async def recv_loop():
            while True:
                try:
                    frame = await track.recv()
                    processor.add_frame(frame)
                except Exception:
                    break

        asyncio.create_task(recv_loop())

    offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
