from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.log_stream import setup_log_capture
from app.routers.chat import router as chat_router
from app.routers.file_converter import router as file_converter_router
from app.routers.kbo import router as kbo_router
from app.routers.logs import router as logs_router

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="LG CNS AI 캠퍼스 — 어시스턴트")

setup_log_capture()

app.include_router(chat_router)
app.include_router(file_converter_router)
app.include_router(kbo_router)
app.include_router(logs_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")
