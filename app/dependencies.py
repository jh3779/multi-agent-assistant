from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langchain_openai import ChatOpenAI

from app.llms.file_converter_agent import FileConverterAgent
from app.llms.kbo import KBOAgent
from app.llms.tech import TechAgent
from app.services.chat import ChatService
from app.services.finance import FinanceService
from app.services.kbo import KBOService
from app.services.tech import TechService
from app.setting import settings
from business_agent import BusinessAgent


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


@lru_cache
def get_finance_model() -> ChatOpenAI:
    """모델은 무상태라 앱 전체가 공유한다.

    매 요청 새로 만들면 HTTP 커넥션 풀을 다시 여는 셈이라 손해다.
    """

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=settings.openai_api_key,
    )


def get_finance_agent(
    model: Annotated[ChatOpenAI, Depends(get_finance_model)],
) -> BusinessAgent:
    """에이전트는 요청마다 새로 만든다. lru_cache를 붙이면 안 된다.

    BusinessAgent는 question/tool_results를 인스턴스에 들고 있어서 공유하면
    동시 요청끼리 값이 섞인다(위 FileConverterAgent와 같은 이유). 생성 비용은
    프롬프트 조립과 bind_tools 정도라 네트워크 호출이 없다.
    """

    return BusinessAgent(model)


def get_finance_service(
    agent: Annotated[BusinessAgent, Depends(get_finance_agent)],
) -> FinanceService:
    return FinanceService(agent)


@lru_cache
def get_kbo_agent() -> KBOAgent:
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=settings.openai_api_key,
    )
    return KBOAgent(model)


def get_kbo_service(
    agent: Annotated[KBOAgent, Depends(get_kbo_agent)],
) -> KBOService:
    return KBOService(agent)
