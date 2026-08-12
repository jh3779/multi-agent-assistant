from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.llms.kbo_agent import KBOAgent
from app.schemas.kbo import KBORequest, KBOResponse

router = APIRouter(
    prefix="/kbo",
    tags=["KBO"],
)

agent = KBOAgent()


@router.post(
    "/invoke",
    response_model=KBOResponse,
)
async def invoke_agent(
    request: KBORequest,
) -> KBOResponse:
    answer = await agent.ainvoke(request.query)
    return KBOResponse(answer=answer)


@router.post("/stream")
async def stream_agent(
    request: KBORequest,
) -> StreamingResponse:
    return StreamingResponse(
        agent.astream(request.query),
        media_type="text/plain",
    )
