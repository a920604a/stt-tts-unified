from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class STTEngine(Protocol):
    async def transcribe(
        self,
        file_path: str,
        model_size: str,
        language: str,
        include_timestamps: bool,
    ) -> dict: ...


@runtime_checkable
class TTSEngine(Protocol):
    async def list_voices(self) -> list[dict]: ...

    async def synthesize(self, text: str, voice: str) -> tuple[str, str]: ...

    async def stream_audio(self, text: str, voice: str) -> AsyncGenerator[bytes, None]: ...
