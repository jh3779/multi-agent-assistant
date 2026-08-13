# FastAPI 진입점 — dotenv 로드, 라우터 등록
from fastapi import FastAPI

from app.routers.tech import router as tech_router

app = FastAPI()

app.include_router(tech_router)
