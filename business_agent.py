import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.llms.agent import Agent
from app.memory import load_featured
from app.schemas.evaluation import AnswerEvaluation, ValidationResult
from app.setting import settings
from app.tools.base import BaseTool
from app.tools.finance import (
    GetExchangeRateTool,
    GetInterestRateTool,
    GetStockPriceTool,
)
from app.tools.search import WebSearchTool


async def main():
    # ChatOpenAI는 os.environ만 보므로 .env를 읽은 settings에서 키를 직접 넘긴다.
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )
    agent = BusinessAgent(model)

    while True:
        user_input = input("\n사용자: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        print("AI: ", end="")

        async for chunk in agent.astream(user_input):
            print(chunk, end="", flush=True)

        print()


# 두 루프 모두 상한이 필요하다. 평가자는 생각보다 자주 거절하고,
# 도구 호출도 모델이 같은 도구를 반복 호출하며 맴돌 수 있다.
MAX_TOOL_ROUNDS = 3
MAX_ANSWER_ATTEMPTS = 2

# 최종 답변을 흘려보낼 때 한 번에 내보내는 글자 수.
ANSWER_CHUNK_SIZE = 3

# 조각 사이 간격. 없으면 완성본이라 전부 같은 순간에 도착한다.
ANSWER_CHUNK_DELAY = 0.04

# 답변이 길어도 타이핑 총 시간이 이 값을 넘지 않도록 간격을 줄인다.
ANSWER_STREAM_SECONDS = 1.5


# 이 프롬프트는 도구 선택 단계에서만 쓰인다. 여기서 나온 문장은 사용자에게
# 보여주지 않고 버리므로 답변 문체나 서술 규칙을 넣지 않는다.
# 최종 답변 작성 규칙은 ANSWER_WRITER_PROMPT가 담당한다.
FINANCE_AGENT_PROMPT = """
당신은 금융 질문을 받아 어떤 도구를 어떤 인자로 호출할지 결정합니다.
답변을 작성하는 것이 목적이 아니라 필요한 데이터를 모으는 것이 목적입니다.

[종목 코드 참고표]

{memory}

[도구 호출 규칙]

- 위 표는 예시일 뿐입니다. 표에 없는 국내 종목도 한글 종목명을 그대로 넘기면
  도구가 코스피·코스닥 2600여 종목에서 심볼을 찾아냅니다.
- 종목명은 정식 명칭으로 넘깁니다. 예: '현대차'가 아니라 '현대자동차'.
- 주가·환율·금리를 묻는 질문이면 반드시 해당 전용 도구를 호출합니다.
- 세율·한도·규제 기준처럼 정책이나 법으로 바뀌는 수치를 묻는 질문이면
  web_search를 호출합니다. 기억에 의존해 넘기지 않습니다.
- 개념·원리·용어 설명만 필요한 질문이면 아무 도구도 호출하지 않습니다.
- 한 질문에 여러 데이터가 필요하면 도구를 여러 개 호출합니다.
"""


# 역할·규칙은 system, 매번 달라지는 데이터는 human으로 나눈다.
# ChatPromptTemplate.from_template()은 전부 HumanMessage로 만들기 때문에
# from_messages()로 역할을 명시해야 세 프롬프트의 취급이 일관된다.
ANSWER_WRITER_SYSTEM = """
당신은 금융 질문에 대한 최종 답변을 작성하는 작성자입니다.

[도구 없이 수치를 단정하면 안 되는 것]

- 현재 주가, 환율, 기준금리처럼 시시각각 바뀌는 값.
- 세율, 각종 한도, 규제 기준처럼 정책이나 법 개정으로 바뀌는 값.
  (예: 예금자보호 한도, 배당소득세율, 상하한가 폭)
- 위 값들은 도구 결과에 있는 것만 씁니다. 도구가 [실패]했거나 호출되지 않았다면
  확인하지 못했다고 밝히고 어디서 확인할 수 있는지 안내합니다.
  기억하고 있는 예전 수치를 현재 값처럼 말하지 않습니다. 낡은 값은 틀린 값입니다.

[검색 결과를 쓸 때]

- web_search 결과에 있는 수치는 근거가 있으므로 그대로 씁니다.
- 검색으로 확인한 내용은 어디서 온 것인지 함께 밝힙니다.
  (예: "예금보험공사 안내에 따르면 ...")
- 검색 결과에 시점이 적혀 있으면 함께 씁니다. 웹 문서는 오래된 것이 섞이므로
  언제 기준인지 밝혀야 사용자가 판단할 수 있습니다.
- 검색 결과끼리 내용이 다르면 어느 쪽이 최신인지 살피고, 판단이 어려우면
  양쪽을 모두 알리고 공식 기관 확인을 권합니다.

[도구 없이 답해도 되는 것]

- 개념, 작동 원리, 배경, 용어 정의, 일반적인 판단 기준과 주의사항.
- 계산 방법이나 공식 자체(예: PER은 주가를 주당순이익으로 나눈 값).
- 수치를 못 구했다고 답변을 포기하지 않습니다. 위 범위에서 설명을 이어갑니다.
- 예를 들어 기준금리 수치를 못 구했다면, 기준금리가 무엇이고 물가·환율·대출에
  어떤 영향을 주는지 설명한 뒤 최신 수치는 한국은행에서 확인하도록 안내합니다.

[답변 스타일]

- 한국어로, 핵심부터 간결하게 씁니다.
- 도구로 확인한 값과 일반 지식으로 설명한 부분이 구분되도록 씁니다.
"""


ANSWER_WRITER_HUMAN = """
[사용자 질문]

{question}

[도구 조회 결과]

{tool_results}
{feedback}
"""


ANSWER_EVALUATOR_SYSTEM = """
당신은 금융 답변의 품질을 검증하는 평가자입니다.
문제를 항목별로 점검한 뒤 최종 통과 여부(is_valid)까지 당신이 판정합니다.

[점검 방법]

- 바뀔 수 있는 수치가 도구 근거 없이 제시됐는지 봅니다. 두 종류입니다.
  (1) 현재 주가·환율·금리처럼 시시각각 변하는 값.
  (2) 세율·한도·규제 기준처럼 정책이나 법으로 바뀌는 값.
  이런 수치가 도구 결과에 없는데 단정적으로 쓰였다면 빠짐없이 적습니다.
- 도구 결과의 값을 단위나 자릿수만 바꿔 쓴 것은 근거가 있는 것으로 봅니다.
- web_search 결과 본문에 나온 수치도 근거가 있는 것으로 봅니다.
  검색 발췌문 안에 있는 숫자라면 문제 삼지 않습니다.
- 확정된 역사적 사실(코스피 산출 기준일 1980년)과 계산 공식은 대조 대상이 아닙니다.

[탈락시키면 안 되는 경우]

- 도구 조회에 실패했고 답변이 그 사실을 밝힌 뒤 일반 지식으로 설명을 이어간 경우는
  통과입니다. 이 에이전트는 수치를 못 구했을 때 아는 범위에서 설명하도록 되어 있습니다.
  설명을 덧붙였다는 이유로 탈락시키지 마세요.
- 질문 자체가 일반적인 설명을 요구해서 답변에 수치가 없는 경우도 통과입니다.
- 제도·원리·용어를 설명한 내용은 도구 결과에 없더라도 문제가 아닙니다.

[탈락시켜야 하는 경우]

- 도구 결과에 없는 수치를 지어낸 경우.
- 조회에 실패했는데 성공한 것처럼 수치를 제시한 경우.
- 물어본 것과 다른 이야기를 한 경우.
"""


ANSWER_EVALUATOR_HUMAN = """
[사용자 질문]

{question}

[도구 조회 결과 — 이것이 유일한 근거입니다]

{tool_results}

[검토할 답변]

{answer}
"""


def build_prompt(
    system: SystemMessagePromptTemplate,
    human: HumanMessagePromptTemplate,
) -> ChatPromptTemplate:
    """시스템 프롬프트와 휴먼 프롬프트를 하나로 합친다.

    세 에이전트가 똑같이 필요한 조립이라 함수로 빼둔다.
    """

    return ChatPromptTemplate.from_messages([system, human])


class ToolSelectAgent(Agent):
    """1단계. 질문에 필요한 도구를 골라 실행하고 결과를 모은다."""

    def __init__(self, model: Any, tools: list[BaseTool]) -> None:
        super().__init__(model)
        self.memory = load_featured()
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}
        self.prompt = build_prompt(
            self.create_system_prompt(), self.create_human_prompt()
        )
        self.model_with_tools = model.bind_tools(tools)

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(FINANCE_AGENT_PROMPT)

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template("{input}")

    def create_workflow(self) -> Runnable[Any, Any]:
        """계약 이행용. 실제 실행은 collect()가 메시지 리스트를 직접 관리한다.

        도구 결과(ToolMessage)를 대화 중간에 끼워 넣으며 반복해야 해서
        한 방향으로만 흐르는 체인으로는 이 루프를 표현할 수 없다.
        """

        return self.prompt | self.model_with_tools

    async def answer_validation(
        self, question: str, answer: str, *args: Any, **kwargs: Any
    ) -> BaseModel:
        raise NotImplementedError("답변 평가는 AnswerEvaluatorAgent가 맡는다.")

    async def astream(
        self, question: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[str]:
        raise NotImplementedError("사용자 스트리밍은 BusinessAgent가 맡는다.")

    def format_memory(self) -> str:
        return "\n".join(f"- {key}: {value}" for key, value in self.memory.items())

    async def validate_tool_result(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: Any,
    ) -> ValidationResult:
        # TODO: 검증 LLM 연결 전까지는 도구가 돌려준 실패 문자열만 걸러낸다.
        text = str(tool_result)
        failed = "실패" in text or "미지원" in text

        return ValidationResult(
            is_valid=not failed,
            reason=text if failed else f"{tool_name} 조회 성공",
        )

    async def collect(self, question: str) -> list[str]:
        messages: list[BaseMessage] = self.prompt.format_messages(
            input=question,
            memory=self.format_memory(),
        )
        collected: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            ai = await self.model_with_tools.ainvoke(messages)

            if not isinstance(ai, AIMessage) or not ai.tool_calls:
                break

            messages.append(ai)

            for tool_call in ai.tool_calls:
                selected = self.tools_by_name[tool_call["name"]]
                result = await selected.ainvoke(tool_call["args"])
                check = await self.validate_tool_result(
                    tool_call["name"], tool_call["args"], result
                )
                label = "성공" if check.is_valid else "실패"

                collected.append(
                    f"[{label}] {tool_call['name']}({tool_call['args']}) -> {result}"
                )
                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                    )
                )

        return collected


class AnswerWriterAgent(Agent):
    """2단계. 도구 결과만 근거로 최종 답변을 작성한다."""

    def __init__(self, model: Any) -> None:
        super().__init__(model)
        self.workflow = self.create_workflow()

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(ANSWER_WRITER_SYSTEM)

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template(ANSWER_WRITER_HUMAN)

    def create_workflow(self) -> Runnable[Any, Any]:
        prompt = build_prompt(self.create_system_prompt(), self.create_human_prompt())

        return prompt | self.model

    async def answer_validation(
        self, question: str, answer: str, *args: Any, **kwargs: Any
    ) -> BaseModel:
        raise NotImplementedError("답변 평가는 AnswerEvaluatorAgent가 맡는다.")

    async def astream(
        self, question: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[str]:
        raise NotImplementedError("사용자 스트리밍은 BusinessAgent가 맡는다.")

    async def write(self, question: str, tool_results: str, feedback: str = "") -> str:
        written = await self.workflow.ainvoke(
            {
                "question": question,
                "tool_results": tool_results,
                "feedback": feedback,
            }
        )

        return str(written.content)


class AnswerEvaluatorAgent(Agent):
    """3단계. 답변을 도구 결과와 대조해 통과 여부를 판정한다."""

    def __init__(self, model: Any) -> None:
        super().__init__(model)
        self.workflow = self.create_workflow()

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(ANSWER_EVALUATOR_SYSTEM)

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template(ANSWER_EVALUATOR_HUMAN)

    def create_workflow(self) -> Runnable[Any, Any]:
        prompt = build_prompt(self.create_system_prompt(), self.create_human_prompt())

        # 구조화 출력이라 판정 결과가 AnswerEvaluation으로 파싱되어 돌아온다.
        return prompt | self.model.with_structured_output(AnswerEvaluation)

    async def astream(
        self, question: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[str]:
        raise NotImplementedError("사용자 스트리밍은 BusinessAgent가 맡는다.")

    def build_feedback(self, evaluation: AnswerEvaluation) -> str:
        """자기가 내린 판정을 작성자가 바로 쓸 수 있는 지시문으로 옮긴다.

        판정을 내린 쪽이 그 뜻도 해석한다. 오케스트레이터가 AnswerEvaluation의
        필드를 일일이 들여다보지 않게 하려는 것이다.

        별도 리라이터 LLM을 두지 않고 이 피드백을 작성자에게 되먹인다.
        리라이터를 따로 두면 그쪽도 도구 결과를 못 봐서 환각이 다시 생긴다.
        """

        problems = [evaluation.reason] if evaluation.reason else []

        if evaluation.unsupported_numbers:
            problems.append(
                "근거 없는 수치: "
                + ", ".join(evaluation.unsupported_numbers)
                + ". 도구 결과에 있는 값만 쓰세요."
            )

        if evaluation.hides_tool_failure:
            problems.append("조회에 실패한 항목은 실패했다고 밝히세요.")

        if not evaluation.answers_question:
            problems.append("질문에서 물어본 내용에 직접 답하세요.")

        return (
            "\n[이전 답변의 문제점]\n"
            + "\n".join(f"- {p}" for p in problems)
            + "\n위 문제를 고쳐서 처음부터 다시 작성하세요."
        )

    async def answer_validation(
        self,
        question: str,
        answer: str,
        tool_results: str = "",
        *args: Any,
        **kwargs: Any,
    ) -> AnswerEvaluation:
        """질문·도구 결과·답변을 모두 주고 항목별로 판정받는다.

        답변만 주면 수치가 진짜인지 판단할 근거가 없어 환각을 못 잡는다.
        베이스가 *args/**kwargs를 허용해서 tool_results를 추가로 받을 수 있다.
        """

        if not answer.strip():
            return AnswerEvaluation(
                reason="답변이 비어 있습니다.",
                unsupported_numbers=[],
                hides_tool_failure=False,
                answers_question=False,
                is_valid=False,
            )

        return await self.workflow.ainvoke(
            {
                "question": question,
                "tool_results": tool_results,
                "answer": answer,
            }
        )


class BusinessAgent(Agent):
    """오케스트레이터. 세 서브 에이전트를 순서대로 돌리고 재작성 루프를 관리한다.

    내부 단계는 전부 ainvoke로 돌리고, 검증을 통과한 최종 답변만 스트리밍한다.
    """

    def __init__(self, model: Any):
        super().__init__(model)
        self.tools: list[BaseTool] = [
            GetStockPriceTool(),
            GetExchangeRateTool(),
            GetInterestRateTool(),
            WebSearchTool(),
        ]
        self.tool_agent = ToolSelectAgent(model, self.tools)
        # 파일을 두 번 읽지 않도록 도구 에이전트가 읽은 것을 그대로 참조한다.
        self.memory = self.tool_agent.memory
        self.writer_agent = AnswerWriterAgent(model)
        self.evaluator_agent = AnswerEvaluatorAgent(model)

        # 베이스의 answer_validation(answer) 시그니처가 질문·도구 결과를 못 받아서
        # 이번 턴의 근거를 인스턴스에 들고 있는다. 베이스 수정 시 인자로 옮길 것.
        # 상태를 들고 있으므로 요청마다 새 인스턴스를 만들어야 한다(웹 서버 주의).
        self.question: str = ""
        self.tool_results: list[str] = []

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return self.tool_agent.create_system_prompt()

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return self.tool_agent.create_human_prompt()

    def create_workflow(self) -> Runnable[Any, Any]:
        return self.writer_agent.create_workflow()

    async def validate_tool_result(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: Any,
    ) -> ValidationResult:
        return await self.tool_agent.validate_tool_result(
            tool_name, tool_input, tool_result
        )

    async def answer_validation(
        self, question: str, answer: str, *args: Any, **kwargs: Any
    ) -> AnswerEvaluation:
        return await self.evaluator_agent.answer_validation(
            question, answer, self.format_tool_results()
        )

    def format_memory(self) -> str:
        return self.tool_agent.format_memory()

    def format_tool_results(self) -> str:
        if not self.tool_results:
            return "(도구를 사용하지 않았습니다)"

        return "\n".join(self.tool_results)

    # 베이스 클래스가 astream을 `async def`로 선언해 Coroutine[..., AsyncIterator]가 된다.
    # 여기는 async generator라 반환형이 AsyncIterator 자체다. 베이스 수정 전까지 무시한다.
    # pyrefly: ignore[bad-override]
    async def astream(
        self, question: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[str]:
        """도구 조회 -> 답변 작성 -> 품질 평가 -> (필요시) 재작성 순으로 진행한다.

        중간 단계는 사용자에게 보여줄 것이 아니므로 전부 ainvoke로 처리하고,
        검증을 통과한 최종 답변만 조각내어 스트리밍한다. 작성 중에 흘려보내면
        평가에서 탈락한 답변을 이미 사용자가 다 읽은 뒤가 된다.
        """

        self.question = question
        self.tool_results = await self.tool_agent.collect(question)

        answer = ""
        feedback = ""

        for _ in range(MAX_ANSWER_ATTEMPTS):
            answer = await self.writer_agent.write(
                question, self.format_tool_results(), feedback
            )
            evaluation = await self.answer_validation(question, answer)

            if evaluation.is_valid:
                break

            feedback = self.evaluator_agent.build_feedback(evaluation)
        else:
            # 한도를 다 써도 통과 못 하면 마지막 답변을 그대로 내보낸다.
            # 폴백이 없으면 평가자가 계속 거절할 때 무한 루프가 된다.
            pass

        async for piece in self.stream_answer(answer):
            yield piece

    async def stream_answer(self, answer: str) -> AsyncIterator[str]:
        """확정된 답변을 타이핑하듯 조금씩 흘린다.

        검증을 통과한 문자열이라 LLM을 다시 부르지 않는다. 재생성하면 방금
        검증한 답변과 다른 문장이 나갈 수 있다. 즉 토큰 스트리밍이 아니라
        완성본을 잘라 보내는 것이고, 간격이 없으면 전부 같은 순간에 도착한다.

        답변 길이와 무관하게 총 소요가 ANSWER_STREAM_SECONDS를 넘지 않도록
        간격을 자동으로 줄인다. 긴 답변에서 타이핑이 하염없이 이어지면
        오히려 답답해지기 때문이다.
        """

        if not answer:
            return

        chunks = [
            answer[i : i + ANSWER_CHUNK_SIZE]
            for i in range(0, len(answer), ANSWER_CHUNK_SIZE)
        ]
        delay = min(ANSWER_CHUNK_DELAY, ANSWER_STREAM_SECONDS / len(chunks))

        for index, chunk in enumerate(chunks):
            if index:  # 첫 조각은 기다리지 않고 바로 내보낸다.
                await asyncio.sleep(delay)

            yield chunk


if __name__ == "__main__":
    asyncio.run(main())
