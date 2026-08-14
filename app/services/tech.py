import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator

from app.llms.tech import TechAgent
from app.schemas.tech import TechStreamEvent

logger = logging.getLogger(__name__)


class TechService:
    """agent가 만든 이벤트를 클라이언트에 보낼 형식으로 바꾼다."""

    # 완성된 답변을 흘려보낼 때 한 번에 내보내는 글자 수
    CHUNK_SIZE = 5

    def __init__(self, agent: TechAgent, chunk_delay: float = 0.1):
        self.agent = agent
        self.chunk_delay = chunk_delay

    @staticmethod
    def to_sse(event: TechStreamEvent) -> str:
        """이벤트 모델을 SSE 프레임 문자열로 변환한다.

        마크다운에는 줄바꿈이 많아 data를 반드시 JSON으로 감싸야 한다.
        raw 줄바꿈이 들어가면 SSE 프레임이 그 자리에서 잘린다.
        """
        payload = json.dumps(event.data, ensure_ascii=False)
        return f"event: {event.type}\ndata: {payload}\n\n"

    def split_markdown(self, markdown: str) -> Iterator[str]:
        for index in range(0, len(markdown), self.CHUNK_SIZE):
            yield markdown[index : index + self.CHUNK_SIZE]

    async def delta_frames(self, markdown: str) -> AsyncIterator[str]:
        """완성된 답변을 조각내서 타이핑처럼 보이도록 내보낸다."""
        for chunk in self.split_markdown(markdown):
            yield self.to_sse(TechStreamEvent(type="delta", data={"text": chunk}))
            await asyncio.sleep(self.chunk_delay)

    async def astream_sse(self, question: str) -> AsyncIterator[str]:
        try:
            async for event in self.agent.astream(question):
                # 답변은 이미 완성된 상태로 오므로 여기서 조각내 흘려보낸다.
                if event.type == "result":
                    async for frame in self.delta_frames(event.data["markdown"]):
                        yield frame

                yield self.to_sse(event)
                await asyncio.sleep(self.chunk_delay)

        except Exception:
            # 스트림이 시작된 뒤에는 HTTP 상태 코드를 바꿀 수 없다.
            # 오류도 SSE 이벤트로 알려야 클라이언트가 상황을 파악할 수 있다.
            logger.exception("답변 스트리밍 실패")
            yield self.to_sse(
                TechStreamEvent(
                    type="error",
                    data={"message": "답변 생성 중 오류가 발생했습니다."},
                )
            )

    async def answer_markdown(self, question: str) -> str:
        """스트리밍 없이 완성된 마크다운만 한 번에 반환한다."""
        workflow = self.agent.create_workflow()

        response = await workflow.ainvoke({"question": question})

        return response.to_markdown()
