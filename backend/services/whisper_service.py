import asyncio
import logging
from typing import Optional

import whisper

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]


class WhisperEngine:
    def __init__(self, model: str = "base", device: str = "cpu", language: str = "auto"):
        self._models: dict[str, whisper.Whisper] = {}
        self.default_model = model
        self.device = device
        self.default_language = language

    async def load_model(self, model_size: str) -> whisper.Whisper:
        if model_size in self._models:
            return self._models[model_size]

        logger.info(f"載入 Whisper 模型: {model_size} (device={self.device})")
        loop = asyncio.get_event_loop()
        model = await loop.run_in_executor(
            None, lambda: whisper.load_model(model_size, device=self.device)
        )
        self._models[model_size] = model
        logger.info(f"模型 {model_size} 載入完成")
        return model

    async def transcribe(
        self,
        file_path: str,
        model_size: str = "base",
        language: str = "auto",
        include_timestamps: bool = False,
    ) -> dict:
        model = await self.load_model(model_size)

        language_param: Optional[str] = None if language == "auto" else language
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(file_path, language=language_param),
        )

        if include_timestamps and "segments" in result:
            lines = [
                f"[{self._fmt(seg['start'])} - {self._fmt(seg['end'])}] {seg['text'].strip()}"
                for seg in result["segments"]
            ]
            text = "\n".join(lines)
        else:
            text = result["text"].strip()

        return {
            "text": text,
            "segments": result.get("segments", []) if include_timestamps else [],
        }

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"
