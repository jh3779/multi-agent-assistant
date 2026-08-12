from fastapi import APIRouter

from app.llms.kbo_agent import KBOAgent
from app.schemas.kbo import KBORequest, KBOResponse

router = APIRouter(
    prefix="/kbo",
    tags=["KBO"],
)

agent = KBOAgent()


@router.post(
    "/query",
    response_model=KBOResponse,
)
async def invoke_agent(
    request: KBORequest,
) -> KBOResponse:
    answer = await agent.ainvoke(request.query)

    return KBOResponse(answer=answer)
