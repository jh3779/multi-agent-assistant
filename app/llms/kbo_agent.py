import asyncio
import json
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from app.schemas.kbo import ValidationResult
from app.setting import settings
from app.tools.date_time import DateTimeTool
from app.tools.web_search import WebSearchTool

# =========================================================
# Config
# =========================================================

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0

MAX_TOOL_ITERATIONS = 5

MAX_SEARCH_RESULTS = 5
SEARCH_DEPTH = "advanced"

TIMEZONE = "Asia/Seoul"

PROMPT_PATH = Path(__file__).parent.parent / "resources" / "kbo.yaml"
with PROMPT_PATH.open(encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)
    MAIN_PROMPT, VALIDATION_PROMPT = (
        PROMPTS["main_prompt"],
        PROMPTS["validation_prompt"],
    )

# =========================================================
# Message Helpers
# =========================================================


def create_messages(
    query: str,
) -> list[BaseMessage]:
    """
    Create initial messages for the KBO agent.
    """

    return [
        SystemMessage(content=MAIN_PROMPT),
        HumanMessage(content=query),
    ]


def collect_evidence(
    messages: list[BaseMessage],
) -> str:
    """
    Collect tool outputs used as evidence.
    """

    evidence = [
        message.content for message in messages if isinstance(message, ToolMessage)
    ]

    return "\n\n".join(evidence)


# =========================================================
# Agent
# =========================================================


class KBOAgent:
    def __init__(self):

        # -------------------------------------------------
        # Tools
        # -------------------------------------------------

        self.tools = [
            WebSearchTool(
                max_results=MAX_SEARCH_RESULTS,
                search_depth=SEARCH_DEPTH,
            ),
            DateTimeTool(),
        ]

        self.tool_map = {tool.name: tool for tool in self.tools}

        # -------------------------------------------------
        # Model
        # -------------------------------------------------

        self.model = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=MODEL_NAME,
            temperature=TEMPERATURE,
        )

        self.model_with_tools = self.model.bind_tools(self.tools)

        self.validator = self.model.with_structured_output(ValidationResult)

    # =====================================================
    # Answer Generation
    # =====================================================

    async def _generate_answer(
        self,
        query: str,
    ) -> tuple[str, str]:
        """
        Generate a draft answer.
        """

        messages = create_messages(query)

        for _ in range(MAX_TOOL_ITERATIONS):
            print("\n[MODEL] Calling model...")

            response = await self.model_with_tools.ainvoke(messages)

            messages.append(response)

            if not response.tool_calls:
                answer = response.content
                evidence = collect_evidence(messages)

                print("\n[DRAFT] Generated answer:")
                print(answer)

                print("\n[EVIDENCE] Collected tool results:")
                print(evidence)

                return answer, evidence

            tool_messages = await self._execute_tools(response.tool_calls)

            messages.extend(tool_messages)

        raise RuntimeError("Maximum tool iterations exceeded.")

    # =====================================================
    # Tool Execution
    # =====================================================

    async def _execute_tool(
        self,
        tool_call: dict[str, Any],
    ) -> ToolMessage:
        """
        Execute a single tool call.
        """

        tool = self.tool_map.get(tool_call["name"])

        if tool is None:
            return ToolMessage(
                content=f"Unknown tool: {tool_call['name']}",
                tool_call_id=tool_call["id"],
            )

        try:
            print(f"\n[TOOL] Executing {tool_call['name']}...")

            result = await tool.ainvoke(tool_call["args"])

            return ToolMessage(
                content=json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                ),
                tool_call_id=tool_call["id"],
            )

        except (ValueError, TypeError) as e:
            return ToolMessage(
                content=f"Tool execution error: {e}",
                tool_call_id=tool_call["id"],
            )

    async def _execute_tools(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolMessage]:
        """
        Execute multiple tool calls concurrently.
        """

        return list(
            await asyncio.gather(
                *[self._execute_tool(tool_call) for tool_call in tool_calls]
            )
        )

    # =====================================================
    # Validation
    # =====================================================

    async def _validate(
        self,
        query: str,
        answer: str,
        evidence: str,
    ) -> ValidationResult:
        """
        Validate the draft answer using collected evidence.
        """

        print("\n[VALIDATION] Validating answer...")

        messages = [
            SystemMessage(content=VALIDATION_PROMPT),
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

        return await self.validator.ainvoke(messages)

    # =====================================================
    # Correction
    # =====================================================

    async def _correct(
        self,
        query: str,
        answer: str,
        evidence: str,
        validation: ValidationResult,
    ) -> str:
        """
        Correct an invalid answer using validation feedback.
        """

        print("\n[CORRECTION] Correcting answer...")

        messages = [
            SystemMessage(content=MAIN_PROMPT),
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

        response = await self.model.ainvoke(messages)

        return response.content

    # =====================================================
    # Public Interface
    # =====================================================

    async def ainvoke(
        self,
        query: str,
    ) -> str:
        """
        Generate, validate, and if necessary correct
        the final answer.
        """

        # 1. Generate draft answer
        answer, evidence = await self._generate_answer(query)

        # 2. Validate draft answer
        validation = await self._validate(
            query=query,
            answer=answer,
            evidence=evidence,
        )

        # 3. Return immediately if validation passes
        if validation.is_valid:
            print("\n[VALIDATION] Passed")
            return answer

        print("\n[VALIDATION] Failed")
        print(f"[VALIDATION] Reason: {validation.reason}")
        print(f"[VALIDATION] Correction: {validation.correction}")

        # 4. Correct invalid answer
        corrected_answer = await self._correct(
            query=query,
            answer=answer,
            evidence=evidence,
            validation=validation,
        )

        print("\n[CORRECTION] Corrected answer:")
        print(corrected_answer)

        return corrected_answer


# =========================================================
# Test
# =========================================================


async def main():

    agent = KBOAgent()

    result = await agent.ainvoke(
        "KBO 순위를 찾고, 그 순위에서 1위인 구단에 대해 설명해줘."
    )

    print("\n[FINAL] Answer:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
