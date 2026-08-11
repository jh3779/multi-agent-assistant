# TODO(백엔드 담당 미정): 실제 Main LLM/Tech·Code·General 도구가 나오기 전까지
# 프론트엔드를 개발·검증하기 위한 목(mock) 채팅 엔드포인트.
# 계약(이벤트 종류: tool_start/tool_end/answer_chunk/done)은 docs/06_open_questions.md
# OQ-001 초안을 따름 — 실제 백엔드가 나오면 이 파일을 통째로 교체한다.
import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


def _pick_mock_tool(message: str) -> str:
    if any(k in message for k in ("코드", "버그", "함수", "리팩터")):
        return "code_llm_tool"
    if any(k in message for k in ("기술", "쿠버네티스", "서버", "네트워크")):
        return "tech_llm_tool"
    return "general_llm_tool"


async def _mock_stream(message: str) -> AsyncIterator[str]:
    tool = _pick_mock_tool(message)

    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool})}\n\n"
    await asyncio.sleep(0.6)
    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool})}\n\n"

    answer = (
        f"(목 응답) '{message}'에 대해 {tool}를 호출했다고 가정한 자리표시자 답변입니다. "
        "실제 Main LLM이 연결되면 이 문장은 진짜 답변으로 교체됩니다."
    )
    for word in answer.split(" "):
        yield f"data: {json.dumps({'type': 'answer_chunk', 'content': word + ' '})}\n\n"
        await asyncio.sleep(0.05)

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _mock_stream(request.message), media_type="text/event-stream"
    )
