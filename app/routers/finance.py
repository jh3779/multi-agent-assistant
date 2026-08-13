from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_finance_service
from app.schemas.finance import FinanceAnswerResponse, FinanceQuestionRequest
from app.services.finance import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])

# SSE는 중간 프록시가 응답을 모아버리면 스트리밍이 무의미해진다.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@router.post("/ask", response_model=FinanceAnswerResponse)
async def ask(
    request: FinanceQuestionRequest,
    service: Annotated[FinanceService, Depends(get_finance_service)],
) -> FinanceAnswerResponse:
    """스트리밍 없이 완성된 답변을 한 번에 돌려준다.

    /docs에서 바로 눌러볼 수 있어 테스트와 디버깅에 쓴다.
    """

    return await service.ask(request.question)


@router.get("/stream")
async def stream_answer(
    request: Request,
    service: Annotated[FinanceService, Depends(get_finance_service)],
    question: str = Query(min_length=1, max_length=500),
) -> StreamingResponse:
    """답변을 SSE로 전달한다.

    GET이라 브라우저 표준 EventSource를 그대로 쓸 수 있다.
    """

    return StreamingResponse(
        service.astream_sse(question, request.is_disconnected),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
