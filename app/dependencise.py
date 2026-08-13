from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langchain_openai import ChatOpenAI

from app.llms.tech import TechAgent
from app.services.finance import FinanceService
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
    동시 요청끼리 값이 섞인다. 생성 비용은 프롬프트 조립과 bind_tools 정도라
    네트워크 호출이 없다.
    """

    return BusinessAgent(model)


def get_finance_service(
    agent: Annotated[BusinessAgent, Depends(get_finance_agent)],
) -> FinanceService:
    return FinanceService(agent)
