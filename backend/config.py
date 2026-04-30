from functools import lru_cache
from pathlib import Path
from typing import Tuple, Type

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class ServerSettings(BaseModel):
    cors_origins: list[str] = ["*"]
    log_level: str = "info"


class StorageSettings(BaseModel):
    upload_dir: str = "data/uploads"
    result_dir: str = "data/results"
    audio_dir: str = "data/audio"
    db_path: str = "data/history.db"
    max_file_size_mb: int = 500


class WhisperEngineSettings(BaseModel):
    model: str = "base"
    device: str = "cpu"
    language: str = "auto"


class STTSettings(BaseModel):
    engine: str = "whisper"
    whisper: WhisperEngineSettings = WhisperEngineSettings()


class EdgeTTSEngineSettings(BaseModel):
    default_voice: str = "zh-TW-HsiaoChenNeural"
    retry_count: int = 3
    retry_delay_seconds: int = 2


class KokoroEngineSettings(BaseModel):
    model_path: str = "models/kokoro-v1.0.onnx"
    voices_path: str = "models/voices-v1.0.bin"
    voice: str = "af_heart"


class TTSSettings(BaseModel):
    engine: str = "edge-tts"
    edge_tts: EdgeTTSEngineSettings = EdgeTTSEngineSettings()
    kokoro: KokoroEngineSettings = KokoroEngineSettings()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    server: ServerSettings = ServerSettings()
    storage: StorageSettings = StorageSettings()
    stt: STTSettings = STTSettings()
    tts: TTSSettings = TTSSettings()
    frontend_build_dir: str = "frontend/dist"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file="config.yaml"),
            file_secret_settings,
        )

    def ensure_dirs(self) -> None:
        for d in [self.storage.upload_dir, self.storage.result_dir, self.storage.audio_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
