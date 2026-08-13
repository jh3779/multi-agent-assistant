from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_openai import ChatOpenAI

from app.log_stream import setup_log_capture
from app.routers.chat import router as chat_router
from app.routers.file_converter import router as file_converter_router
from app.routers.finance import router as finance_router
from app.routers.kbo import router as kbo_router
from app.routers.logs import router as logs_router
from app.routers.tech import router as tech_router
from app.setting import settings

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작 시 금융 에이전트가 쓸 모델을 한 번만 만들어 공유한다.

    ChatOpenAI는 무상태라 공유해도 안전하고, 매 요청 새로 만들면 HTTP 커넥션
    풀을 다시 여는 셈이라 손해다. 반면 BusinessAgent는 질문·도구 결과를
    인스턴스에 들고 있어서 요청마다 새로 만든다
    (app/routers/finance.py의 create_agent 참고).
    """

    app.state.model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )

    yield


app = FastAPI(title="LG CNS AI 캠퍼스 — 어시스턴트", lifespan=lifespan)

setup_log_capture()

app.include_router(chat_router)
app.include_router(file_converter_router)
app.include_router(finance_router)
app.include_router(kbo_router)
app.include_router(logs_router)
app.include_router(tech_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
