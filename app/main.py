# FastAPI 진입점 — dotenv 로드, 라우터 등록
from fastapi import FastAPI

from app.api.kbo import router as kbo_router

# TODO: 서비스 명칭 결정 후, title 수정
app = FastAPI(title="LG CNS Project API")

app.include_router(kbo_router)
