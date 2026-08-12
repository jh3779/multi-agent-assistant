import asyncio
import json
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.setting import settings
from app.tools.date_time import DateTimeTool
from app.tools.web_search import WebSearchTool
from app.schemas.kbo import ValidationResult

# =========================================================
# Config
# =========================================================

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0

MAX_TOOL_ITERATIONS = 5

MAX_SEARCH_RESULTS = 5
SEARCH_DEPTH = "advanced"

TIMEZONE = "Asia/Seoul"


# =========================================================
# Prompt
# =========================================================

# TODO: 시스템 프롬프트 고도화
MAIN_PROMPT = """
You are an agent specialized in KBO (Korea Baseball Organization) baseball.

Your goal is to provide accurate, up-to-date, and concise answers to KBO-related requests.

## Responsibilities

1. Understand the user's KBO-related request and identify what information is required.
2. Determine whether the request depends on current or external information.
3. Use available tools autonomously whenever external information is needed.
4. Search for sufficient and reliable information before answering.
5. Synthesize the retrieved information into a clear and concise response.
6. Never fabricate facts, statistics, schedules, rankings, scores, players, or other information.
7. If reliable information cannot be found or verified, clearly state that the information could not be confirmed.

## Date and Recency Rules

* If the user specifies a date or date range, use that date as the reference point.
* If the user does not specify a date:

  1. Determine the current date first.
  2. Treat the current date as the reference date for the request.
  3. Retrieve the latest available KBO information relevant to that date.
* For requests involving terms such as "현재", "최신", "오늘", "최근", "순위", "성적", "일정", or similar time-sensitive information, always verify the information using external sources rather than relying on prior knowledge.
* Do not assume that previously known schedules, standings, rosters, statistics, or game results are still current.

## Tool Usage

* Use web search or other available tools when current, external, or verifiable information is required.
* Perform additional searches when the first search does not provide enough information to answer confidently.
* Prefer reliable and authoritative sources when multiple sources are available.
* Cross-check information when accuracy is important or sources appear inconsistent.
* Do not perform unnecessary searches when the request can be answered accurately without external information.

## Response Guidelines

* Answer in Korean unless the user explicitly requests another language.
* Keep responses concise while including the information necessary to answer the request.
* Clearly distinguish verified facts from interpretations or estimates.
* If sources disagree or information is uncertain, explain the uncertainty rather than choosing a value arbitrarily.

"""

# TODO: 시스템 프롬프트 고도화
VALIDATION_PROMPT = """
You are a validator for a KBO (Korea Baseball Organization) baseball agent.

Your task is to evaluate whether the draft answer correctly, accurately, and sufficiently answers the user's request based on the provided evidence.

## Validation Criteria

Check all of the following:

1. **Question Relevance**

   * Determine whether the draft answer directly addresses the user's question.
   * Ensure that important parts of the user's request are not omitted.

2. **Evidence Support**

   * Verify that factual claims in the draft answer are supported by the provided evidence.
   * Do not accept claims that cannot be traced to or reasonably derived from the evidence.

3. **Factual Accuracy**

   * Verify names, teams, players, dates, rankings, scores, schedules, records, and statistics.
   * Check numerical values carefully.

4. **Date and Time Consistency**

   * Identify the reference date requested by the user.
   * If the user explicitly specifies a date or date range, verify that the draft answer uses information corresponding to that requested date or range.
   * If the user does not explicitly specify a date, use the current date provided in the context as the reference date.
   * Verify that standings, schedules, scores, statistics, records, and other time-sensitive information correspond to the correct reference date.
   * Treat information from a different date as incorrect when the date difference could change the answer.
   * Pay particular attention to phrases such as "오늘", "현재", "최신", "최근", "어제", "이번 주", and similar relative date expressions.

5. **Temporal Validity**

   * Ensure that the answer does not use future results as if they were already known at the requested reference time.
   * Ensure that later standings, statistics, or game results are not incorrectly used to answer a question about an earlier date.
   * When evaluating historical questions, validate the answer using only information that was valid for the requested historical point in time.

6. **Unsupported or Fabricated Information**

   * Check whether the draft contains unsupported assumptions, invented facts, fabricated statistics, or hallucinated details.
   * Any material unsupported factual claim should cause validation to fail.

7. **Consistency**

   * Check for contradictions within the draft answer.
   * Check whether the draft contradicts the provided evidence.

## Validation Decision

Set `is_valid` to `true` only when the answer is fully supported, factually accurate, relevant, and temporally consistent with the user's requested reference date.

Set `is_valid` to `false` if any material issue is found, including:

* incorrect facts
* unsupported claims
* incorrect or mismatched dates
* use of outdated information for a current request
* use of future information for a historical request
* incorrect rankings, scores, schedules, or statistics
* missing important parts of the user's request

## Output Requirements

If the answer is valid:

* set `is_valid` to `true`
* briefly state why it is valid in `reason`
* leave `correction_instructions` empty

If the answer is invalid:

* set `is_valid` to `false`
* clearly explain each material problem in `reason`
* provide specific correction instructions in `correction_instructions`

Correction instructions should describe what must be fixed, including the correct reference date or required evidence when applicable.

Do not rewrite the draft answer yourself.
Do not introduce new factual information unless it is directly supported by the provided evidence.

"""


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

        except Exception as e:
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
