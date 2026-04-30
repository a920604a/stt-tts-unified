from functools import lru_cache
from typing import Union

from ..config import get_settings
from .whisper_service import WhisperEngine
from .tts_service import EdgeTTSEngine
from .kokoro_service import KokoroEngine


@lru_cache
def get_stt_engine() -> WhisperEngine:
    settings = get_settings()
    engine = settings.stt.engine
    if engine == "whisper":
        return WhisperEngine(
            model=settings.stt.whisper.model,
            device=settings.stt.whisper.device,
            language=settings.stt.whisper.language,
        )
    raise ValueError(f"Unknown STT engine: '{engine}'. Available: whisper")


@lru_cache
def get_tts_engine() -> Union[EdgeTTSEngine, KokoroEngine]:
    settings = get_settings()
    engine = settings.tts.engine
    if engine == "edge-tts":
        return EdgeTTSEngine(
            audio_dir=settings.storage.audio_dir,
            default_voice=settings.tts.edge_tts.default_voice,
            retry_count=settings.tts.edge_tts.retry_count,
            retry_delay_seconds=settings.tts.edge_tts.retry_delay_seconds,
        )
    if engine == "kokoro":
        return KokoroEngine(
            model_path=settings.tts.kokoro.model_path,
            voices_path=settings.tts.kokoro.voices_path,
            audio_dir=settings.storage.audio_dir,
            default_voice=settings.tts.kokoro.voice,
        )
    raise ValueError(f"Unknown TTS engine: '{engine}'. Available: edge-tts, kokoro")
