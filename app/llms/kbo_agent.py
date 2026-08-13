import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI

from app.llms.agent import Agent
from app.schemas.kbo import ValidationResult
from app.setting import settings
from app.tools.date_time import DateTimeTool
from app.tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)


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

PROMPT_PATH = Path(__file__).parent.parent / "resources" / "kbo.yaml"

with PROMPT_PATH.open(encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

MAIN_PROMPT = PROMPTS["main_prompt"]
VALIDATION_PROMPT = PROMPTS["validation_prompt"]


# =========================================================
# Message Helpers
# =========================================================


def collect_evidence(
    messages: list[BaseMessage],
) -> str:
    """
    Collect tool outputs used as evidence.
    """

    # message.content는 str뿐 아니라 list[dict|str]일 수도 있어 join이 깨진다.
    evidence = [
        str(message.content) for message in messages if isinstance(message, ToolMessage)
    ]

    return "\n\n".join(evidence)


# =========================================================
# Agent
# =========================================================


class KBOAgent(Agent):
    def __init__(self):

        # -------------------------------------------------
        # Tools
        # -------------------------------------------------

        self.tools = [
            WebSearchTool(
                max_results=MAX_SEARCH_RESULTS,
                search_depth=SEARCH_DEPTH,
            ),
            DateTimeTool(
                timezone=TIMEZONE,
            ),
        ]

        self.tool_map = {tool.name: tool for tool in self.tools}

        # -------------------------------------------------
        # Model
        # -------------------------------------------------

        model = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=MODEL_NAME,
            temperature=TEMPERATURE,
        )

        super().__init__(model)

        self.model_with_tools = self.model.bind_tools(self.tools)

        self.validator = self.model.with_structured_output(ValidationResult)

        # -------------------------------------------------
        # Workflow
        # -------------------------------------------------

        self.workflow = self.create_workflow()

    # =====================================================
    # Prompt
    # =====================================================

    def create_system_prompt(
        self,
        *args,
        **kwargs,
    ) -> SystemMessagePromptTemplate:
        """
        Create the system prompt template.
        """

        return SystemMessagePromptTemplate.from_template(MAIN_PROMPT)

    def create_human_prompt(
        self,
        *args,
        **kwargs,
    ) -> HumanMessagePromptTemplate:
        """
        Create the human prompt template.
        """

        return HumanMessagePromptTemplate.from_template("{question}")

    # =====================================================
    # Workflow
    # =====================================================

    def create_workflow(
        self,
        *args,
        **kwargs,
    ) -> Runnable[Any, Any]:
        """
        Create the execution workflow for the KBO agent.
        """

        return RunnableLambda(self._run)

    async def _run(
        self,
        question: str,
    ) -> str:
        """
        Generate, validate, and if necessary correct the final answer.
        """

        start_time = time.perf_counter()

        try:
            # 1. Generate draft answer
            answer, evidence = await self._generate_answer(question)

            # 2. Validate draft answer
            validation = await self.answer_validation(
                question=question,
                answer=answer,
                evidence=evidence,
            )

            # 3. Return if validation passes
            if validation.is_valid:
                logger.info("[VALIDATION] Passed")

                return answer

            logger.info("[VALIDATION] Failed")
            logger.info(f"[VALIDATION] Reason: {validation.reason}")
            logger.info(f"[VALIDATION] Correction: {validation.correction}")

            # 4. Correct invalid answer
            corrected_answer = await self._correct(
                question=question,
                answer=answer,
                evidence=evidence,
                validation=validation,
            )

            logger.info("[CORRECTION] Corrected answer:")
            logger.info(corrected_answer)

            return corrected_answer

        finally:
            elapsed_time = time.perf_counter() - start_time

            logger.info(f"[TIME] Total elapsed time: {elapsed_time}")

    # =====================================================
    # Answer Generation
    # =====================================================

    async def _generate_answer(
        self,
        question: str,
    ) -> tuple[str, str]:
        """
        Generate a draft answer using tools when needed.
        """

        system_prompt = self.create_system_prompt()
        human_prompt = self.create_human_prompt()

        messages = [
            system_prompt.format(),
            human_prompt.format(question=question),
        ]

        for _ in range(MAX_TOOL_ITERATIONS):
            logger.info("[MODEL] Calling model...")

            response = await self.model_with_tools.ainvoke(messages)

            messages.append(response)

            if not response.tool_calls:
                answer = response.content
                evidence = collect_evidence(messages)

                logger.info("[DRAFT] Generated answer:")
                logger.info(answer)

                logger.info("[EVIDENCE] Collected tool results:")
                logger.info(evidence)

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
                content=(f"Unknown tool: {tool_call['name']}"),
                tool_call_id=tool_call["id"],
            )

        try:
            logger.info(f"[TOOL] Executing {tool_call['name']}")

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
                content=(f"Tool execution error: {e}"),
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

    async def answer_validation(
        self,
        question: str,
        answer: str,
        *args,
        **kwargs,
    ) -> ValidationResult:
        """
        Validate the draft answer using
        collected evidence.
        """

        logger.info("[VALIDATION] Validating answer...")

        evidence = kwargs.get(
            "evidence",
            "",
        )

        messages = [
            SystemMessage(content=VALIDATION_PROMPT),
            HumanMessage(
                content=f"""
Question:
{question}

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
        question: str,
        answer: str,
        evidence: str,
        validation: ValidationResult,
    ) -> str:
        """
        Correct an invalid answer using
        validation feedback.
        """

        logger.info("[CORRECTION] Correcting answer...")

        messages = [
            SystemMessage(content=MAIN_PROMPT),
            HumanMessage(
                content=f"""
Original question:
{question}

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
        question: str,
    ) -> str:
        """
        Invoke the KBO agent workflow.
        """

        return await self.workflow.ainvoke(question)

    async def astream(
        self,
        question: str,
        *args,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream the validated final answer.
        """

        final_answer = await self.ainvoke(question)

        for chunk in final_answer.split():
            yield chunk + " "
            await asyncio.sleep(0.03)
