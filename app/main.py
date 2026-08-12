# FastAPI 진입점 — dotenv 로드, 라우터 등록
from fastapi import FastAPI

from app.api.kbo import router as kbo_router

# TODO: 수정 필요 (테스트 목적으로 생성)
app = FastAPI(title="KBO Agent API")
app.include_router(kbo_router)