import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.setting import settings
from app.tools.web_search import WebSearchTool

# =========================================================
# Config
# =========================================================

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0
MAX_TOOL_ITERATIONS = 5

MAX_SEARCH_RESULTS = 5
SEARCH_DEPTH = "advanced"


# =========================================================
# Prompt
# =========================================================

# TODO: 시스템 프롬프트 수정하기
MAIN_PROMPT = """
You are an agent specialized in KBO baseball.

Your task is to:
1. Understand the KBO baseball-related request.
2. Use web search when external information is needed.
3. Search enough information to answer accurately.
4. Synthesize the search results into a concise answer.
5. Do not fabricate facts.
6. If reliable information cannot be found, clearly say so.

Use tools autonomously when needed.

Answer in Korean unless otherwise requested.
"""

VALIDATION_PROMPT = """
You are a validator for a KBO baseball agent.

Evaluate whether the draft answer correctly answers the user's question.

Check:
1. Whether the answer directly addresses the question.
2. Whether factual claims are supported by the provided evidence.
3. Whether names, dates, rankings, scores, and statistics are accurate.
4. Whether the answer contains unsupported or fabricated information.

If the answer is correct:
- set is_valid to true

If the answer is incorrect or unsupported:
- set is_valid to false
- explain the problem in reason
- provide correction instructions

Do not rewrite the answer yourself.
"""


# =========================================================
# Response
# =========================================================
class ValidationResult(BaseModel):
    is_valid: bool = Field(
        description="Whether the answer is factually correct and supported."
    )

    reason: str = Field(
        description="Reason for the validation result."
    )

    correction: str | None = Field(
        default=None,
        description="Correction instructions if the answer is invalid."
    )


# =========================================================
# Message
# =========================================================

def create_messages(
    query: str,
) -> list[BaseMessage]:

    return [
        SystemMessage(
            content=MAIN_PROMPT
        ),
        HumanMessage(
            content=query
        ),
    ]

def collect_evidence(
    messages: list[BaseMessage],
) -> str:

    evidence = [
        message.content
        for message in messages
        if isinstance(message, ToolMessage)
    ]

    return "\n\n".join(evidence)

# =========================================================
# Agent
# =========================================================

class BaseballAgent:

    def __init__(self):

        self.tools = [
            WebSearchTool(
                max_results=MAX_SEARCH_RESULTS,
                search_depth=SEARCH_DEPTH
            ),
        ]

        self.tool_map = {
            tool.name: tool
            for tool in self.tools
        }

        self.model = ChatOpenAI(            
            api_key=settings.openai_api_key,
            model=MODEL_NAME,
            temperature=TEMPERATURE,
        )

        self.model_with_tools = (
            self.model.bind_tools(
                self.tools
            )
        )

        self.validator = (
            self.model.with_structured_output(
                ValidationResult
            )
        )

        self.model_chain = RunnableLambda(
            self._call_model
        )


    async def _call_model(
        self,
        messages: list[BaseMessage],
    ) -> list[BaseMessage]:

        print("\n[MODEL] Calling model...")
        response = (
            await self.model_with_tools.ainvoke(
                messages
            )
        )

        return messages + [response]


    async def _execute_tool(
        self,
        tool_call: dict[str, Any],
    ) -> ToolMessage:

        tool = self.tool_map.get(
            tool_call["name"]
        )

        if tool is None:
            return ToolMessage(
                content=f"Unknown tool: {tool_call['name']}",
                tool_call_id=tool_call["id"],
            )

        try:
            print(f"\n[TOOL] Executing {tool_call['name']}...")
            result = await tool.ainvoke(
                tool_call["args"]
            )

            return ToolMessage(
                content=json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                ),
                tool_call_id=tool_call["id"],
            )

        except Exception as e:
            return ToolMessage(
                content=f"Tool execution error: {e}",
                tool_call_id=tool_call["id"],
            )


    async def _execute_tools(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolMessage]:

        return list(
            await asyncio.gather(
                *[
                    self._execute_tool(tool_call)
                    for tool_call in tool_calls
                ]
            )
        )


    async def _validate(
        self,
        query: str,
        answer: str,
        evidence: str,
    ) -> ValidationResult:

        print("\n[VALIDATION] Validating response...")

        messages = [
            SystemMessage(
                content=VALIDATION_PROMPT
            ),
            HumanMessage(
                content=f"""
    Question:
    {query}

    Draft answer:
    {answer}

    Evidence:
    {evidence}
    """
            ),
        ]

        return await self.validator.ainvoke(
            messages
        )

    async def _correct(
        self,
        query: str,
        answer: str,
        evidence: str,
        validation: ValidationResult,
    ) -> str:

        print("\n[CORRECTION] Correcting response...")

        messages = [
            SystemMessage(
                content=MAIN_PROMPT
            ),
            HumanMessage(
                content=f"""
    Original question:
    {query}

    Previous answer:
    {answer}

    Validation feedback:
    {validation.reason}

    Correction instructions:
    {validation.correction}

    Evidence:
    {evidence}

    Rewrite the answer so that it is accurate
    and supported by the evidence.
    """
            ),
        ]

        response = await self.model.ainvoke(
            messages
        )

        return response.content
    

    async def ainvoke(
        self,
        query: str,
    ) -> str:

        messages = create_messages(query)

        for _ in range(MAX_TOOL_ITERATIONS):
            messages = (
                await self.model_chain.ainvoke(
                    messages
                )
            )

            last_message = messages[-1]

            # Tool call 없음 → 최종 응답
            if not last_message.tool_calls:

                answer = last_message.content
                print("\n[DRAFT] Generated response:")
                print(answer)

                evidence = collect_evidence(messages)
                print("\n[EVIDENCE] Collected tool results:")
                print(evidence)

                validation = await self._validate(
                    query=query,
                    answer=answer,
                    evidence=evidence,
                )

                if validation.is_valid:
                    print("\n[VALIDATION] Passed")
                    return answer

                print("\n[VALIDATION] Failed")
                print(f"[VALIDATION] Reason: {validation.reason}")
                print(f"[VALIDATION] Correction: {validation.correction}")

                corrected_answer = await self._correct(
                    query=query,
                    answer=answer,
                    evidence=evidence,
                    validation=validation,
                )
                print("\n[CORRECTION] Corrected response:")
                print(corrected_answer)

                return corrected_answer

            # Tool 병렬 실행
            tool_messages = (
                await self._execute_tools(
                    last_message.tool_calls
                )
            )

            messages.extend(tool_messages)

        raise RuntimeError(
            "Maximum tool iterations exceeded."
        )


    async def astream(
        self,
        query: str,
    ) -> AsyncIterator[str]:

        final_answer = await self.ainvoke(
            query
        )

        for chunk in final_answer.split():
            yield chunk + " "


async def main():
    agent = BaseballAgent()

    async for chunk in agent.astream(
        "26년 8월 11일 현재 KBO 순위를 찾고, "
        "그 순위에서 1위인 구단에 대해 설명해줘."
    ):
        print(
            chunk,
            end="",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())