import asyncio
import io
import logging
from datetime import datetime
from pathlib import Path

import edge_tts
from edge_tts.exceptions import NoAudioReceived

logger = logging.getLogger(__name__)

_VOICES_CACHE: list[dict] | None = None


class EdgeTTSEngine:
    def __init__(
        self,
        audio_dir: str = "data/audio",
        default_voice: str = "zh-TW-HsiaoChenNeural",
        retry_count: int = 3,
        retry_delay_seconds: int = 2,
    ):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = default_voice
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds

    async def list_voices(self) -> list[dict]:
        global _VOICES_CACHE
        if _VOICES_CACHE is None:
            voices = await edge_tts.list_voices()
            _VOICES_CACHE = [
                {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
                for v in voices
            ]
        return _VOICES_CACHE

    async def synthesize(self, text: str, voice: str) -> tuple[str, str]:
        text = text.strip()

        audio_bytes = b""
        submaker = edge_tts.SubMaker()
        last_exc: Exception | None = None

        for attempt in range(self.retry_count):
            if attempt > 0:
                await asyncio.sleep(attempt * self.retry_delay_seconds)
                logger.warning(f"TTS retry {attempt}/{self.retry_count - 1} for voice={voice}")
            try:
                communicate = edge_tts.Communicate(text, voice)
                submaker = edge_tts.SubMaker()
                with io.BytesIO() as buf:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            buf.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            submaker.feed(chunk)
                    audio_bytes = buf.getvalue()
                break
            except NoAudioReceived as exc:
                last_exc = exc
        else:
            raise last_exc

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        audio_filename = f"tts_{timestamp}.wav"
        srt_filename = f"tts_{timestamp}.srt"

        (self.audio_dir / audio_filename).write_bytes(audio_bytes)
        (self.audio_dir / srt_filename).write_text(submaker.get_srt(), encoding="utf-8")

        logger.info(f"TTS 合成完成: {audio_filename}")
        return audio_filename, srt_filename

    def get_audio_path(self, filename: str) -> Path:
        return self.audio_dir / filename

    async def stream_audio(self, text: str, voice: str):
        text = text.strip()
        last_exc: Exception | None = None
        for attempt in range(self.retry_count):
            if attempt > 0:
                await asyncio.sleep(attempt * self.retry_delay_seconds)
                logger.warning(f"TTS stream retry {attempt}/{self.retry_count - 1} for voice={voice}")
            try:
                communicate = edge_tts.Communicate(text, voice)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]
                return
            except Exception as exc:
                last_exc = exc
        logger.error(f"TTS stream failed after {self.retry_count} attempts: {last_exc}")
