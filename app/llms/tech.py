import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import (
    ProviderStrategy,
    StructuredOutputValidationError,
)
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import Runnable, RunnableLambda

from app.llms.agent import Agent
from app.schemas.tech import (
    AnswerValidationResponse,
    TechAgentResponse,
    TechStreamEvent,
)
from app.tools.web_search import CachedWebSearchTool

logger = logging.getLogger(__name__)


class TechAgent(Agent):
    MAX_RETRY = 3
    MIN_VALIDATION_SCORE = 70

    def create_system_prompt(self) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(
            """
            당신은 소프트웨어 개발 기술 정보를 조사하고 답변하는 전문 Agent입니다.

            [답변 가능한 질문]
            개발에 관련된 설명, 사용법, 비교, 특징,
            버전 변화 등의 질문은 반드시 개발 관련 질문으로 처리하세요.

            질문이 개발과 관련 있는지 확실하지 않은 경우에도
            개발 기술과 연관성이 있다면 개발 관련 질문으로 처리하세요.

            명백하게 개발과 관련 없는 질문에는 답변을 하지 않고 작업을 종료하세요.

            [검색]

            개발 관련 질문에는 tavily_search를 사용해서 정보를 조사하세요.

            동일한 기술이나 동일한 공식 도메인에 대해
            여러 개의 유사한 검색을 동시에 수행하지 마세요.

            하나의 검색 query에 필요한 키워드를 결합해서 검색하세요.

            잘못된 방식:
            - "FastAPI"
            - "FastAPI official documentation"

            올바른 방식:
            - "FastAPI async await coroutine"

            [검색 출처]

            검색 출처 우선순위:

            1. 해당 기술의 공식 문서
            2. 해당 프로젝트의 공식 GitHub 저장소
            3. 해당 기업/재단의 공식 블로그 또는 발표 자료
            4. 위 자료가 없는 경우 신뢰할 수 있는 2차 자료

            공식 출처의 도메인을 알고 있다면
            tavily_search의 domains에 전달하세요.

            [답변]
            한글로 답변하며,
            내용은 간결하고 학습에 도움이 되도록 작성하세요.
            불필요하게 길거나 느러지는 단어 및 말투를 선택하지 마세요.

            [답변 형식]

            answer와 example은 마크다운 문법으로 작성하세요.
            목록, 굵은 글씨, 인라인 코드(`FastAPI`)를 활용하고
            example의 코드는 반드시 언어를 명시한 코드 블록으로 감싸세요.

            제목(#, ##)은 사용하지 마세요.
            제목과 출처 목록은 시스템이 따로 붙입니다.
            """
        )

    def create_human_prompt(self) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template(
            """
            개발과 관련된 정보를 검색하고 근거와 출처를 포함해 답해주세요.
            {question}
            """
        )

    def create_validation_system_prompt(
        self,
    ) -> SystemMessagePromptTemplate:
        return SystemMessagePromptTemplate.from_template(
            """
            당신은 AI 답변 품질을 평가하는 Evaluator입니다.

            사용자 질문과 AI 답변을 비교하여
            답변이 질문에 적절하게 답했는지 평가하세요.

            다음 기준으로 평가하세요.

            1. 질문의 의도를 정확하게 이해했는가
            2. 질문에서 요구한 내용을 실제로 답했는가
            3. 중요한 내용이 누락되지 않았는가
            4. 질문과 관련 없는 불필요한 내용이 포함되지 않았는가
            5. 설명이 논리적이고 이해하기 쉬운가
            6. 각 답변에 출처(sources)가 포함되어 있는가
               출처가 비어 있다면 낮은 점수를 부여하세요.

            [평가 결과]

            score:
            - 0~100 사이의 답변 품질 점수

            reason:
            - 해당 점수를 부여한 이유
            - 답변의 장점과 문제점을 간결하게 설명

            missing_points:
            - 사용자 질문에 비해 빠진 중요한 내용을 작성
            - 누락된 내용이 없다면 빈 배열 [] 반환
            """
        )

    def create_validation_human_prompt(
        self,
    ) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template(
            """
            [사용자 질문]

            {question}


            [AI 답변]

            {answer}
            """
        )

    def create_retry_human_prompt(
        self,
    ) -> HumanMessagePromptTemplate:
        return HumanMessagePromptTemplate.from_template(
            """
            이전 답변에 대한 품질 검증 결과 문제가 발견되었습니다.

            [사용자 질문]

            {question}


            [이전 답변]

            {previous_answer}


            [검증 점수]

            {score}


            [검증 판단 이유]

            {reason}


            [누락된 내용]

            {missing_points}


            위 검증 결과를 반영하여 답변을 다시 작성하세요.

            특히 missing_points에 있는 내용이 있다면
            반드시 보완하세요.

            필요한 경우 웹 검색을 다시 수행하세요.

            이전 답변을 그대로 반복하지 말고,
            검증에서 발견된 문제를 해결한 개선된 답변을 작성하세요.
            """
        )

    async def answer_validation(
        self,
        question: str,
        answer: str,
    ) -> AnswerValidationResponse:
        validator = self.model.with_structured_output(AnswerValidationResponse)

        messages = [
            self.create_validation_system_prompt().format(),
            self.create_validation_human_prompt().format(
                question=question,
                answer=answer,
            ),
        ]

        return await validator.ainvoke(messages)

    def create_answer_agent(self):
        return create_agent(
            model=self.model,
            tools=[
                # 검색 결과 캐시를 agent memory에 보관한다.
                CachedWebSearchTool(
                    cache=self.memory.setdefault("web_search", {}),
                ),
            ],
            system_prompt=self.create_system_prompt().format(),
            response_format=ProviderStrategy(TechAgentResponse),
        )

    @staticmethod
    def status_event(message: str) -> TechStreamEvent:
        return TechStreamEvent(type="status", data={"message": message})

    @staticmethod
    def result_event(answer: TechAgentResponse) -> TechStreamEvent:
        """확정된 답변을 이벤트 하나로 만든다.

        조각내서 흘려보내는 일은 이 결과를 사용하는 쪽에서 담당한다.
        """
        return TechStreamEvent(
            type="result",
            data={
                "status": answer.status,
                "markdown": answer.to_markdown(),
            },
            response=answer,
        )

    async def astream(
        self, question: str, *args, **kwargs
    ) -> AsyncIterator[TechStreamEvent]:
        """답변 생성 과정을 진행 상황 이벤트로 내보낸다.

        답변 전체가 있어야 검증할 수 있으므로 토큰 단위로 흘리지 않는다.
        검증을 통과한 답변만 result 이벤트로 전달한다.
        """
        answer_agent = self.create_answer_agent()

        # 최초에는 사용자 질문, 재시도에는 검증 결과를 담은 메시지를 전달한다.
        message = self.create_human_prompt().format(
            question=question,
        )

        total = self.MAX_RETRY + 1

        for attempt in range(1, total + 1):
            yield self.status_event(f"답변 생성 중 ({attempt}/{total})")

            try:
                result = await answer_agent.ainvoke({"messages": [message]})
            except StructuredOutputValidationError as error:
                # 응답 스키마를 지키지 못한 경우도 재시도 대상으로 처리한다.
                logger.warning("구조화 출력 파싱 실패: %s", error)
                yield self.status_event("응답 형식 오류, 다시 시도합니다")
                continue

            answer: TechAgentResponse = result["structured_response"]

            # 개발 질문이 아니거나 자료가 부족한 경우는 재시도해도 달라지지 않는다.
            if answer.status != "success":
                yield self.result_event(answer)
                return

            # 전체 structured response를 검증 LLM에게 전달
            answer_text = answer.model_dump_json(indent=2)

            yield self.status_event("답변 품질 검증 중")

            validation = await self.answer_validation(
                question=question,
                answer=answer_text,
            )

            logger.info(
                "검증 점수: %s / %s",
                validation.score,
                validation.reason,
            )

            yield self.status_event(f"검증 점수 {validation.score}점")

            if validation.score >= self.MIN_VALIDATION_SCORE:
                yield self.result_event(answer)
                return

            message = self.create_retry_human_prompt().format(
                question=question,
                previous_answer=answer_text,
                score=validation.score,
                reason=validation.reason,
                missing_points=validation.missing_points,
            )

        # 재시도 횟수를 모두 사용했지만 품질 기준을 만족하지 못한 경우
        yield self.result_event(TechAgentResponse(status="validation_failed"))

    def create_workflow(self, *args, **kwargs) -> Runnable[Any, Any]:
        """스트리밍이 필요 없는 호출을 위해 최종 답변만 반환한다."""

        async def workflow(
            inputs: dict[str, Any],
        ) -> TechAgentResponse:
            answer = TechAgentResponse(status="validation_failed")

            async for event in self.astream(inputs["question"]):
                if event.response is not None:
                    answer = event.response

            return answer

        return RunnableLambda(workflow)
