import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routers import history, stt, tts
from .routers import settings as settings_router
from .services.engine_factory import get_stt_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.ensure_dirs()
    await init_db()
    engine = get_stt_engine()
    await engine.load_model(settings.stt.whisper.model)
    logger.info("STT-TTS Unified ready")
    yield
    # Shutdown (nothing needed)


app = FastAPI(title="STT-TTS Unified", version="1.0.0", lifespan=lifespan)

if settings.server.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API routers
app.include_router(tts.router, prefix="/api/tts", tags=["TTS"])
app.include_router(stt.router, prefix="/api/stt", tags=["STT"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])

# Serve React build — MUST be last
_frontend = Path(settings.frontend_build_dir)
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
else:
    logger.warning(f"Frontend build not found at {_frontend}. Run `npm run build` in frontend/.")
