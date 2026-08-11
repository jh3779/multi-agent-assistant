from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.chat_mock import router as chat_router
from app.tools.file_converter.router import router as file_converter_router

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="LG CNS AI 캠퍼스 — 어시스턴트")

app.include_router(chat_router)
app.include_router(file_converter_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")
