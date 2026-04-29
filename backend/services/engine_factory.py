from functools import lru_cache

from ..config import get_settings
from .whisper_service import WhisperEngine
from .tts_service import EdgeTTSEngine


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
def get_tts_engine() -> EdgeTTSEngine:
    settings = get_settings()
    engine = settings.tts.engine
    if engine == "edge-tts":
        return EdgeTTSEngine(
            audio_dir=settings.storage.audio_dir,
            default_voice=settings.tts.edge_tts.default_voice,
            retry_count=settings.tts.edge_tts.retry_count,
            retry_delay_seconds=settings.tts.edge_tts.retry_delay_seconds,
        )
    raise ValueError(f"Unknown TTS engine: '{engine}'. Available: edge-tts")
