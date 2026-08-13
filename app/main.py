"""FastAPI 진입점 — 모델 준비, 라우터 등록."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_openai import ChatOpenAI

from app.routers import finance
from app.setting import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작 시 모델을 한 번만 만들어 공유한다.

    ChatOpenAI는 무상태라 공유해도 안전하고, 매 요청 새로 만들면 HTTP 커넥션
    풀을 다시 여는 셈이라 손해다. 반면 에이전트는 요청마다 새로 만든다.
    ChatOpenAI는 os.environ만 보므로 .env를 읽은 settings에서 키를 직접 넘긴다.
    """

    app.state.model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )

    yield


app = FastAPI(
    title="금융 에이전트 API",
    description="도구 조회 -> 답변 작성 -> 품질 평가 파이프라인을 HTTP로 노출한다.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(finance.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
