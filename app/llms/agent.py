from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, AsyncGenerator

from langchain_core.prompts import BasePromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.prompts.message import BaseMessagePromptTemplate

from app.setting import settings


class Agent:
    def __init__(self, model: Any):
        self.model = model
        self.settings = settings
        self.database: dict[str, Any] = {}
        self.memory: dict[str, Any] = {}

    @abstractmethod
    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        """메인 LLM이 서브 LLM을 선택할 수 있도록 도구 스키마를 만든다."""

    @abstractmethod
    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        """메인 LLM이 서브 LLM을 선택할 수 있도록 도구 스키마를 만든다."""

    @abstractmethod
    def create_prompt(self) -> BaseMessagePromptTemplate:
        """메인 LLM이 서브 LLM을 선택할 수 있도록 도구 스키마를 만든다."""



class SubLLM(Agent):
    """메인 LLM이 호출할 수 있는 서브 LLM의 최소 계약."""

    name = ""
    description = ""

    def __init__(self, model: Any, prompt: BasePromptTemplate) -> None:
        if not isinstance(prompt, BasePromptTemplate):
            raise TypeError("prompt must be a LangChain BasePromptTemplate")

        self.prompt = prompt
        super().__init__(model)

    @abstractmethod
    async def astream(self, question: str) -> AsyncIterator[str]:
        """구현 클래스에서 도구 실행, 스트리밍, 상태 저장을 직접 처리한다."""

    def as_tool(self) -> dict[str, Any]:
        """메인 LLM이 서브 LLM을 선택할 수 있도록 도구 스키마를 만든다."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                },
            },
        }


class MainLLM(Agent):
    def __init__(
        self,
        model: Any,
        prompt: BasePromptTemplate,
        sub_llms: list[SubLLM],
    ) -> None:
        if not isinstance(prompt, BasePromptTemplate):
            raise TypeError("prompt must be a LangChain BasePromptTemplate")
        if any(not isinstance(sub.name, str) or not sub.name.strip() for sub in sub_llms):
            raise ValueError("Sub LLM name must not be empty")
        self.model = model
        self.prompt = prompt
        self.sub_llms = {sub.name: sub for sub in sub_llms}
        if len(self.sub_llms) != len(sub_llms):
            raise ValueError("Duplicate sub LLM name")

    def create_tools(self) -> list[dict[str, Any]]:
        """등록된 서브 LLM을 LangChain에 전달할 도구 목록으로 만든다."""
        return [sub.as_tool() for sub in self.sub_llms.values()]

    @abstractmethod
    async def astream(self, inputs: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """메인 LLM이 서브 LLM을 선택할 수 있도록 도구 스키마를 만든다."""
