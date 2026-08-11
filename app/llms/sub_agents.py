from collections.abc import AsyncIterator
from typing import Any

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from app.llms.agent import SubLLM


class _PlaceholderSubAgent(SubLLM):
    category = "카테고리"

    def __init__(self, model: Any) -> None:
        super().__init__(model, self.create_prompt())

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(
            f"너는 {self.category} 카테고리 뉴스를 처리하는 서브 에이전트다. (자리표시자 — 담당자 구현 예정)"
        )

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template("{question}")

    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [self.create_system_prompt(), self.create_human_prompt()]
        )

    async def astream(self, question: str) -> AsyncIterator[str]:
        yield f"[{self.category} 서브 에이전트 자리표시자] question={question!r}"


class BusinessAgent(_PlaceholderSubAgent):
    name = "business_news_agent"
    description = "경제 카테고리 뉴스 관련 질문에 답한다 (business_agent 브랜치에서 실제 구현 예정)"
    category = "경제"


# 야구/건강은 같은 슬롯(담당자 한 명)의 택1 후보 — 담당자가 결정하면
# main_agent.py의 SPORTS_OR_HEALTH_AGENT를 해당 클래스로 바꾸면 됨.


class BaseballAgent(_PlaceholderSubAgent):
    name = "baseball_news_agent"
    description = "야구 카테고리 뉴스 관련 질문에 답한다"
    category = "야구"


class HealthAgent(_PlaceholderSubAgent):
    name = "health_news_agent"
    description = "건강 카테고리 뉴스 관련 질문에 답한다"
    category = "건강"


class DevelopmentAgent(_PlaceholderSubAgent):
    name = "development_news_agent"
    description = "개발 카테고리 뉴스 관련 질문에 답한다"
    category = "개발"
