import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..config import get_settings
from ..services.engine_factory import get_tts_engine
from ..services.history_service import history_service
from ..services.settings_service import settings_service

logger = logging.getLogger(__name__)
router = APIRouter()
_config = get_settings()


class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str


class SynthesizeRequest(BaseModel):
    text: str
    voice: VoiceInfo | str | None = None


@router.get("/voices")
async def list_voices():
    voices = await get_tts_engine().list_voices()
    return JSONResponse(content=voices)


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="請提供文本內容")

    engine = get_tts_engine()

    if req.voice is None:
        voice_name = await settings_service.get(
            "default_tts_voice", _config.tts.edge_tts.default_voice
        )
    elif isinstance(req.voice, VoiceInfo):
        voice_name = req.voice.name
    else:
        voice_name = req.voice

    audio_filename, srt_filename = await engine.synthesize(req.text, voice_name)

    history_id = await history_service.add_tts(
        text=req.text,
        voice=voice_name,
        audio_filename=audio_filename,
        srt_filename=srt_filename,
    )

    return {
        "audio_url": f"/api/tts/audio/{audio_filename}",
        "srt_url": f"/api/tts/audio/{srt_filename}",
        "history_id": history_id,
    }


@router.post("/stream")
async def stream(req: SynthesizeRequest):
    """Stream audio chunks directly as audio/mpeg for real-time playback."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="請提供文本內容")

    engine = get_tts_engine()

    if req.voice is None:
        voice_name = await settings_service.get(
            "default_tts_voice", _config.tts.edge_tts.default_voice
        )
    elif isinstance(req.voice, VoiceInfo):
        voice_name = req.voice.name
    else:
        voice_name = req.voice

    return StreamingResponse(
        engine.stream_audio(req.text, voice_name),
        media_type="audio/mpeg",
    )


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    path = get_tts_engine().get_audio_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="音檔不存在")

    media_type = "audio/wav" if filename.endswith(".wav") else "text/plain"
    return FileResponse(str(path), media_type=media_type)
