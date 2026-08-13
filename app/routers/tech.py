from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencise import get_tech_service
from app.schemas.tech import TechQuestionRequest
from app.services.tech import TechService

router = APIRouter(prefix="/tech", tags=["tech"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@router.post("/stream")
async def stream_answer(
    request: TechQuestionRequest,
    service: Annotated[TechService, Depends(get_tech_service)],
) -> StreamingResponse:
    """답변 생성 과정을 SSE로 전달한다.

    POST라서 브라우저 EventSource는 사용할 수 없다.
    클라이언트는 fetch로 응답 스트림을 직접 읽어야 한다.
    """
    return StreamingResponse(
        service.astream_sse(request.question),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
