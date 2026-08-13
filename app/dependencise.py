from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langchain_openai import ChatOpenAI

from app.llms.file_converter_agent import FileConverterAgent
from app.llms.tech import TechAgent
from app.services.chat import ChatService
from app.services.tech import TechService
from app.setting import settings


@lru_cache
def get_tech_agent() -> TechAgent:
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=settings.openai_api_key,
    )
    return TechAgent(model)


def get_tech_service(
    agent: Annotated[TechAgent, Depends(get_tech_agent)],
) -> TechService:
    return TechService(
        agent,
        chunk_delay=0.1,
    )


# FileConverterAgent는 tech_agent와 달리 @lru_cache로 공유하지 않는다 —
# 실행 결과(도구 산출물, 검증 결과)를 self.memory에 담아두고 요청 하나가 끝날
# 때까지 그대로 읽어 쓰는 구조라, 인스턴스를 여러 요청이 동시에 공유하면
# 동시 요청끼리 서로의 memory를 덮어쓸 수 있다. 매 요청 새 인스턴스를 만들어야
# 안전하다(기존 라우터가 하던 방식과 동일).
def get_file_converter_agent() -> FileConverterAgent:
    return FileConverterAgent()


def get_chat_service(
    agent: Annotated[FileConverterAgent, Depends(get_file_converter_agent)],
) -> ChatService:
    return ChatService(agent)
