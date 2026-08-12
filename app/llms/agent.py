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
    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        """LLM의 역할과 답변 기준을 정의한다."""

    @abstractmethod
    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        """사용자 질문의 입력 형식을 정의한다."""

    @abstractmethod
    def create_workflow(self) -> Runnable[Any, Any]:
        """
        프롬프트, 모델, 도구 실행, 결과 검증, 답변 검증을 조합해
        구현 클래스만의 LLM 실행 파이프라인을 만든다.
        """

    @abstractmethod
    async def validate_tool_result(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: Any,
    ) -> BaseModel:
        """도구 실행 결과가 요청에 적합하고 신뢰할 수 있는지 검증한다."""

    @abstractmethod
    async def answer_validation(self, answer: str) -> BaseModel:
        """LLM의 최종 답변을 평가한다."""

    @abstractmethod
    async def astream(self, question: str) -> AsyncIterator[str]:
        """도구 실행과 답변 생성을 처리하며 결과를 스트리밍한다."""
