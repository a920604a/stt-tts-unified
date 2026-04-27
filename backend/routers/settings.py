from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_settings
from ..services.settings_service import settings_service

router = APIRouter()
_config = get_settings()


class SettingsPatch(BaseModel):
    default_tts_voice: str | None = None


async def _current() -> dict:
    saved = await settings_service.get_all()
    return {
        "default_tts_voice": saved.get("default_tts_voice", _config.default_tts_voice),
    }


@router.get("")
async def get_settings():
    return await _current()


@router.patch("")
async def patch_settings(body: SettingsPatch):
    if body.default_tts_voice is not None:
        await settings_service.set("default_tts_voice", body.default_tts_voice)
    return await _current()
