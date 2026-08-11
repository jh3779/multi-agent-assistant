import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from app.llms.agent import MainLLM, SubLLM

_SYSTEM_PROMPT = (
    "너는 여러 서브 에이전트를 조율하는 메인 에이전트다. "
    "사용자 질문에 답하는 데 필요한 서브 에이전트를 도구로 선택해 호출하고, "
    "여러 서브 에이전트가 필요하면 동시에 호출한 뒤 결과를 종합해 답한다."
)


class MainAgent(MainLLM):
    def __init__(self, model: Any, sub_llms: list[SubLLM]) -> None:
        super().__init__(model, self.create_prompt(), sub_llms)
        # MainLLM.__init__이 Agent.__init__을 호출하지 않아 memory/database가
        # 세팅되지 않는 상태(app/llms/agent.py 쪽 이슈) — 여기서 직접 초기화.
        self.memory: dict[str, list[Any]] = {}
        self.database: dict[str, Any] = {}

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(_SYSTEM_PROMPT)

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template("{question}")

    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [self.create_system_prompt(), self.create_human_prompt()]
        )

    async def astream(self, inputs: dict[str, Any]) -> AsyncGenerator[dict[str, Any]]:
        user_id = inputs["user_id"]
        question = inputs["question"]
        history = self.memory.setdefault(user_id, [])

        new_messages = self.prompt.format_messages(question=question)
        bound_model = self.model.bind(tools=self.create_tools())
        response = await bound_model.ainvoke([*history, *new_messages])

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            history.extend([*new_messages, response])
            yield {"role": "assistant", "content": response.content}
            return

        async def run_sub(call: dict[str, Any]) -> tuple[str, str]:
            sub = self.sub_llms[call["name"]]
            answer = "".join(
                [chunk async for chunk in sub.astream(call["args"]["question"])]
            )
            return call["name"], answer

        results = await asyncio.gather(*(run_sub(call) for call in tool_calls))
        for name, answer in results:
            yield {"role": "tool", "name": name, "content": answer}

        combined = "\n\n".join(f"[{name}] {answer}" for name, answer in results)
        history.extend([*new_messages, {"role": "assistant", "content": combined}])
        yield {"role": "assistant", "content": combined}


# 실제 서브 에이전트(app/llms/sub_agents.py, 서브 에이전트 담당 3명)를 모아
# MainAgent(model, sub_llms)로 조립하는 코드는 이 파일 밖(예: app/main.py)에서
# 담당자가 완성하는 대로 연결한다 — main_agent.py는 MainLLM 계약만 구현한다.
