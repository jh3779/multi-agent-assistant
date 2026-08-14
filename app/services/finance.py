import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from app.llms.business_agent import BusinessAgent
from app.schemas.finance import (
    FinanceAnswerResponse,
    FinanceStreamEvent,
)

logger = logging.getLogger(__name__)


class FinanceService:
    """agent가 만든 답변을 클라이언트에 보낼 형식으로 바꾼다.

    HTTP를 모른다. Request 객체 대신 연결 확인용 콜러블만 받아서
    fastapi 의존성이 이 계층으로 새어 들어오지 않게 한다.
    """

    def __init__(self, agent: BusinessAgent):
        self.agent = agent

    @staticmethod
    def to_sse(event: FinanceStreamEvent) -> str:
        """이벤트 모델을 SSE 프레임 문자열로 변환한다.

        답변에 줄바꿈이 들어갈 수 있어 data를 반드시 JSON으로 감싼다.
        raw 줄바꿈이 들어가면 SSE 프레임이 그 자리에서 잘린다.
        """

        return f"data: {event.model_dump_json()}\n\n"

    async def ask(self, question: str) -> FinanceAnswerResponse:
        """스트리밍 없이 완성된 답변을 한 번에 만든다."""

        chunks = [chunk async for chunk in self.agent.astream(question)]

        return FinanceAnswerResponse(
            question=question,
            answer="".join(chunks),
            tool_results=self.agent.tool_results,
        )

    async def astream_sse(
        self,
        question: str,
        is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[str]:
        """답변 조각을 SSE 프레임으로 흘린다."""

        try:
            async for chunk in self.agent.astream(question):
                # 사용자가 탭을 닫아도 LLM 호출이 계속되면 비용만 나간다.
                if is_disconnected is not None and await is_disconnected():
                    logger.info("클라이언트 연결 종료로 스트리밍 중단")
                    return

                yield self.to_sse(FinanceStreamEvent(type="answer", text=chunk))

            yield self.to_sse(FinanceStreamEvent(type="done"))

        except Exception:
            # 스트림이 시작된 뒤에는 HTTP 상태 코드를 바꿀 수 없다.
            # 오류도 SSE 이벤트로 알려야 클라이언트가 상황을 파악할 수 있다.
            # 내부 메시지는 로그로만 남기고 클라이언트에는 일반 문구를 준다.
            logger.exception("답변 스트리밍 실패")
            yield self.to_sse(
                FinanceStreamEvent(
                    type="error",
                    text="답변 생성 중 오류가 발생했습니다.",
                )
            )
