from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_kbo_service
from app.schemas.kbo import KBORequest, KBOResponse
from app.services.kbo import KBOService

router = APIRouter(
    prefix="/kbo",
    tags=["KBO"],
)


@router.post(
    "/invoke",
    response_model=KBOResponse,
)
async def invoke_agent(
    request: KBORequest,
    service: Annotated[KBOService, Depends(get_kbo_service)],
) -> KBOResponse:
    answer = await service.ainvoke(request.query)

    return KBOResponse(answer=answer)


@router.post("/stream")
async def stream_agent(
    request: KBORequest,
    service: Annotated[KBOService, Depends(get_kbo_service)],
) -> StreamingResponse:
    return StreamingResponse(
        service.astream(request.query),
        media_type="text/plain",
    )
