from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.setting import settings


class Agent(ABC):
    def __init__(self, model: Any):
        self.model = model
        self.settings = settings
        self.memory: dict[str, Any] = {}

    @abstractmethod
    def create_system_prompt(
        self,
        *args,
        **kwargs,
    ) -> SystemMessagePromptTemplate:
        """LLM의 역할과 답변 기준을 정의한다."""

    @abstractmethod
    def create_human_prompt(
        self,
        *args,
        **kwargs,
    ) -> HumanMessagePromptTemplate:
        """사용자 질문의 입력 형식을 정의한다."""

    @abstractmethod
    def create_workflow(
        self,
        *args,
        **kwargs,
    ) -> Runnable[Any, Any]:
        """
        프롬프트, 모델, 도구 실행, 결과 검증, 답변 검증을 조합해
        구현 클래스만의 LLM 실행 파이프라인을 만든다.
        """

    @abstractmethod
    async def answer_validation(
        self,
        question: str,
        answer: str,
        *args,
        **kwargs,
    ) -> BaseModel:
        """LLM의 최종 답변을 평가한다."""

    @abstractmethod
    # 구현체는 async generator이므로 반환형이 AsyncIterator 자체다.
    # `async def`로 선언하면 Coroutine[..., AsyncIterator]가 되어 모든 구현
    # 클래스에서 시그니처 불일치가 난다.
    def astream(self, question: str, *args, **kwargs) -> AsyncIterator[Any]:
        """도구 실행과 답변 생성을 처리하며 진행 상황을 스트리밍한다.

        전송 형식(SSE 등) 변환은 이 결과를 사용하는 쪽에서 담당한다.
        """
