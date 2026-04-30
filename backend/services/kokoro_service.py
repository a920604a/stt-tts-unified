import asyncio
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import numpy as np
import scipy.io.wavfile as wavfile

logger = logging.getLogger(__name__)

_KOKORO_VOICES = [
    {"name": "af_heart", "gender": "Female", "locale": "en-US"},
    {"name": "af_bella", "gender": "Female", "locale": "en-US"},
    {"name": "am_michael", "gender": "Male", "locale": "en-US"},
    {"name": "bf_emma", "gender": "Female", "locale": "en-GB"},
    {"name": "bm_george", "gender": "Male", "locale": "en-GB"},
]


class KokoroEngine:
    def __init__(
        self,
        model_path: str,
        voices_path: str,
        audio_dir: str = "data/audio",
        default_voice: str = "af_heart",
    ):
        try:
            from kokoro_onnx import Kokoro  # noqa: F401
        except ImportError:
            raise RuntimeError("kokoro-onnx not installed. Run: pip install kokoro-onnx")

        from kokoro_onnx import Kokoro

        self.kokoro = Kokoro(model_path, voices_path)
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = default_voice

    async def list_voices(self) -> list[dict]:
        return list(_KOKORO_VOICES)

    def _run_inference(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        """Blocking Kokoro inference — must be called via run_in_executor."""
        samples, sample_rate = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        return samples, sample_rate

    @staticmethod
    def _samples_to_pcm_int16(samples: np.ndarray) -> bytes:
        """Convert float32 normalised [-1, 1] samples to raw PCM int16 bytes."""
        pcm = np.clip(samples, -1.0, 1.0)
        pcm_int16 = (pcm * 32767).astype(np.int16)
        return pcm_int16.tobytes()

    async def synthesize(self, text: str, voice: str) -> tuple[str, str]:
        text = text.strip()
        loop = asyncio.get_event_loop()
        samples, sample_rate = await loop.run_in_executor(
            None, self._run_inference, text, voice
        )

        pcm_int16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, pcm_int16)
        wav_bytes = buf.getvalue()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        audio_filename = f"tts_{timestamp}.wav"
        (self.audio_dir / audio_filename).write_bytes(wav_bytes)

        logger.info(f"Kokoro TTS synthesis complete: {audio_filename}")
        return audio_filename, ""

    async def stream_audio(self, text: str, voice: str) -> AsyncGenerator[bytes, None]:
        text = text.strip()
        loop = asyncio.get_event_loop()
        samples, _sample_rate = await loop.run_in_executor(
            None, self._run_inference, text, voice
        )
        yield self._samples_to_pcm_int16(samples)
