# FastAPI 진입점 — dotenv 로드, 라우터 등록
from fastapi import FastAPI

from app.api.kbo import router as kbo_router

app = FastAPI(title="LG CNS Project API")

app.include_router(kbo_router)
