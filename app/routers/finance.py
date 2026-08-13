"""금융 에이전트 엔드포인트.

라우터는 요청 검증과 에이전트 호출까지만 한다. 비즈니스 로직은 에이전트에 있다.
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas.api import AskRequest, AskResponse, StreamEvent
from business_agent import BusinessAgent

router = APIRouter(prefix="/finance", tags=["finance"])

# SSE는 중간 프록시가 응답을 모아버리면 스트리밍이 무의미해진다.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # nginx 버퍼링 차단
}


def create_agent(request: Request) -> BusinessAgent:
    """요청마다 새 에이전트를 만든다.

    BusinessAgent는 question/tool_results를 인스턴스에 들고 있어서 공유하면
    동시 요청끼리 값이 섞인다. 반면 모델 객체는 무상태라 앱 전체가 공유한다.
    생성 비용은 프롬프트 조립과 bind_tools 정도라 네트워크 호출이 없다.
    """

    return BusinessAgent(request.app.state.model)


@router.post("/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest) -> AskResponse:
    """스트리밍 없이 완성된 답변을 한 번에 돌려준다.

    /docs에서 바로 눌러볼 수 있어 테스트와 디버깅에 쓴다.
    """

    agent = create_agent(request)
    chunks = [chunk async for chunk in agent.astream(body.question)]

    return AskResponse(
        question=body.question,
        answer="".join(chunks),
        tool_results=agent.tool_results,
    )


@router.get("/stream")
async def stream(
    request: Request,
    question: str = Query(min_length=1, max_length=500),
) -> StreamingResponse:
    """SSE로 답변을 흘린다.

    GET인 이유는 브라우저 표준 EventSource가 GET만 지원하기 때문이다.
    """

    async def events() -> AsyncIterator[str]:
        agent = create_agent(request)

        try:
            async for chunk in agent.astream(question):
                # 사용자가 탭을 닫아도 LLM 호출이 계속되면 비용만 나간다.
                if await request.is_disconnected():
                    return

                yield sse(StreamEvent(type="answer", text=chunk))

            yield sse(StreamEvent(type="done"))
        except Exception as e:  # noqa: BLE001
            # 스트리밍 도중 예외가 나면 응답이 어중간하게 끊긴다.
            # 프론트가 알아챌 수 있도록 error 이벤트로 내보낸다.
            yield sse(StreamEvent(type="error", text=f"{type(e).__name__}: {e}"))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def sse(event: StreamEvent) -> str:
    """SSE 한 건을 만든다. 줄바꿈 두 개가 이벤트의 끝이다."""

    return f"data: {event.model_dump_json()}\n\n"
