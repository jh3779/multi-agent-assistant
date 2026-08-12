# file_converter(@tool 데코레이터 함수)를 실제 LLM이 도구로 호출하는 최소 경로. 실제 OPENAI_API_KEY로
# docx/html 변환이 진짜 에이전트 루프(bind_tools → 도구 실행 → 구조화 출력)를
# 통과하는 것까지 end-to-end 검증됨. 다만 아직 HTTP 엔드포인트로 노출되지 않아서
# (POST /chat은 폐기된 목 구현) 채팅 UI에서는 이 경로를 아직 안 탄다.
#
# Main LLM(중앙 오케스트레이터)은 팀이 폐기했으므로, 이건 file_converter 하나만
# 다루는 범위 좁은 에이전트다 — 다른 Tool이 생기면 그때 합치거나 라우팅을 얹으면 됨.
#
# 팀 공용 Agent(ABC)(app/llms/agent.py)를 실제로 상속한 첫 구현체 — 다른 담당자들이
# 참고할 수 있게, 최종 답변 검증(answer_validation)을 자리채우기가 아니라 이 도구
# 맥락에서 실제로 의미 있는 검증(도구가 성공을 주장하는데 artifact가 없는 경우 등
# 상태 불일치 탐지)으로 채웠다. validate_tool_result(도구별 결과 검증)는 팀 논의로
# Agent(ABC)에서 빠졌지만(2026-08-12 app/llms/agent.py 변경), 여전히 유효한 검증이라
# 이 클래스의 일반 메서드로 남겨뒀다 — astream()이 도구 실행마다 호출한다.
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import Runnable
from langchain_core.tools import ToolException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.llms.agent import Agent
from app.schemas.file_converter import FileConversionAnswer
from app.setting import settings
from app.tools.file_converter.tool import file_converter

_SYSTEM_PROMPT = (
    "너는 문서 변환을 도와주는 어시스턴트다. 사용자가 파일 변환을 요청하면 "
    "file_converter 도구를 호출해서 실제로 변환하고, 결과를 간단히 설명해라. "
    "변환이 필요 없는 질문이면 도구를 호출하지 말고 바로 답해라."
)


class ToolResultCheck(BaseModel):
    """validate_tool_result()의 반환 타입."""

    succeeded: bool = Field(
        description="도구 실행이 예외 없이 끝났고 결과가 일관되는지"
    )
    detail: str = Field(description="도구가 반환한 메시지 원문")


class AnswerCheck(BaseModel):
    """answer_validation()의 반환 타입."""

    is_valid: bool = Field(description="요약이 실제 도구 실행 결과와 일치하는지")
    reason: str = Field(description="판단 근거")


class FileConverterAgent(Agent):
    def __init__(self) -> None:
        # ChatOpenAI는 기본적으로 os.environ의 OPENAI_API_KEY를 읽지만, settings에서
        # 명시적으로 넘겨 .env 로딩 경로에 덜 의존하게 한다(이중 안전장치).
        model = ChatOpenAI(
            model="gpt-4o-mini", temperature=0, api_key=settings.openai_api_key
        )
        super().__init__(model)
        self.tools = [file_converter]

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(_SYSTEM_PROMPT)

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template("{question}")

    def create_workflow(self) -> Runnable[Any, Any]:
        # 도구를 여러 번 반복 호출할 수 있는 루프까지 하나의 Runnable로 억지로
        # 합치면 조건 분기가 LCEL 표현식 안에 숨어 오히려 읽기 어려워진다. 그래서
        # 여기서는 "1단계: 도구를 쓸지 판단"까지만 Runnable로 만들고, 도구 실행·
        # 검증·최종 답변 생성은 astream()에서 명시적으로 오케스트레이션한다.
        prompt = ChatPromptTemplate.from_messages(
            [self.create_system_prompt(), self.create_human_prompt()]
        )
        return prompt | self.model.bind_tools(self.tools)

    async def validate_tool_result(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: Any,
    ) -> ToolResultCheck:
        content = getattr(tool_result, "content", str(tool_result))
        artifact = getattr(tool_result, "artifact", None)
        succeeded = not content.startswith("변환 실패")
        # 성공을 주장하는데 artifact(변환된 바이트)가 없으면 상태 불일치 — pandoc
        # 결과가 유실됐거나 ToolMessage 조립이 잘못됐다는 신호라 신뢰하지 않는다.
        if succeeded and artifact is None:
            succeeded = False
        return ToolResultCheck(succeeded=succeeded, detail=content)

    async def answer_validation(self, question: str, answer: str) -> AnswerCheck:
        has_artifacts = bool(self.memory.get("artifacts"))
        claims_conversion = "변환" in answer and "실패" not in answer
        # KBO 에이전트처럼 외부 근거로 사실관계를 대조할 대상이 없다(변환 성공 여부는
        # pandoc이 이미 결정론적으로 판정함). 그래서 여기서는 "LLM 요약이 실제 실행
        # 결과와 모순되지 않는지"만 확인한다 — 도구를 안 썼는데 변환했다고 주장하는
        # 경우(환각)를 잡아낸다.
        is_valid = has_artifacts or not claims_conversion
        reason = (
            "요약과 실제 변환 결과가 일치함"
            if is_valid
            else "도구를 호출하지 않았는데 변환에 성공했다고 요약함"
        )
        return AnswerCheck(is_valid=is_valid, reason=reason)

    async def astream(
        self, question: str, file_path: str | None = None
    ) -> AsyncIterator[str]:
        full_question = (
            question
            if file_path is None
            else f"{question}\n\n(첨부 파일 경로: {file_path})"
        )

        messages: list[BaseMessage] = ChatPromptTemplate.from_messages(
            [self.create_system_prompt(), self.create_human_prompt()]
        ).format_messages(question=full_question)

        # 1단계: 도구를 쓸지 말지, 몇 번 쓸지 LLM이 스스로 판단(Function Calling)
        response = await self.create_workflow().ainvoke({"question": full_question})
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        artifacts: list[bytes] = []
        tool_checks: list[ToolResultCheck] = []

        if tool_calls:
            # 2단계: 도구를 실제로 실행 — LLM이 tool_calls를 여러 개 반환할 수 있고,
            # OpenAI는 각 tool_call마다 대응하는 ToolMessage가 있어야 다음 턴을
            # 받아준다. 하나만 처리하고 나머지를 빼먹으면 다음 요청에서 400 에러가 난다.
            # file_converter.ainvoke(call)에 tool_call 딕셔너리를 통째로 넘기면
            # tool_call_id까지 채워진 ToolMessage(content/artifact 포함)가 바로 나온다.
            for call in tool_calls:
                try:
                    tool_message = await file_converter.ainvoke(call)
                except ToolException as exc:
                    tool_message = ToolMessage(
                        content=f"변환 실패: {exc}", tool_call_id=call["id"]
                    )
                messages.append(tool_message)

                check = await self.validate_tool_result(
                    call["name"], call.get("args", {}), tool_message
                )
                tool_checks.append(check)

                artifact = getattr(tool_message, "artifact", None)
                if artifact is not None:
                    artifacts.append(artifact)

            # 3단계: 도구 결과(성공/실패 전부)를 반영해 Pydantic 구조화 출력으로 최종 답변 생성
            answer = await self.model.with_structured_output(
                FileConversionAnswer
            ).ainvoke(messages)
        else:
            answer = FileConversionAnswer(used_tool=False, summary=response.content)

        self.memory["artifacts"] = artifacts
        self.memory["tool_checks"] = tool_checks
        self.memory["answer"] = answer

        # 4단계: 최종 답변이 실제 실행 결과와 모순되지 않는지 검증
        self.memory["answer_validation"] = await self.answer_validation(
            full_question, answer.summary
        )

        # with_structured_output은 완성된 Pydantic 객체를 한 번에 반환하므로(토큰
        # 단위 부분 JSON을 안전하게 노출할 수 없음), 여기서는 완성된 요약을 한
        # 청크로 yield한다 — 실제 토큰 스트리밍이 필요해지면 구조화 출력 없이
        # 순수 텍스트 답변을 만드는 경로를 별도로 두고 그쪽에서 처리해야 한다.
        yield answer.summary
