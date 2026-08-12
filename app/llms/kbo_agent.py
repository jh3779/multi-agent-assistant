import asyncio
import json
from typing import Any
from collections.abc import AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableLambda

from app.tools.web_search import WebSearchTool
from app.setting import settings


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
SYSTEM_PROMPT = """
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


# =========================================================
# Message
# =========================================================

def create_messages(
    query: str,
) -> list[BaseMessage]:

    return [
        SystemMessage(
            content=SYSTEM_PROMPT
        ),
        HumanMessage(
            content=query
        ),
    ]


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

        self.model_chain = RunnableLambda(
            self._call_model
        )


    async def _call_model(
        self,
        messages: list[BaseMessage],
    ) -> list[BaseMessage]:

        print("Calling model...")
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
            print(f"Executing tool ({tool_call['name']})...")
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
                return last_message.content

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

        messages = create_messages(query)

        for _ in range(MAX_TOOL_ITERATIONS):

            # 먼저 tool 사용 여부 판단
            response = await self.model_with_tools.ainvoke(
                messages
            )

            # tool call이 있으면 실행
            if response.tool_calls:
                messages.append(response)

                tool_messages = await self._execute_tools(
                    response.tool_calls
                )

                messages.extend(tool_messages)

                continue

            # tool call이 없으면 최종 답변을 streaming
            async for chunk in self.model.astream(
                messages
            ):
                if chunk.content:
                    yield chunk.content

            return

        raise RuntimeError(
            "Maximum tool iterations exceeded."
        )


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