# 프론트(app/static/chat.js)를 검증하기 위한 목(mock, app/chat_mock.py)을 폐기한 뒤
# 비어있던 POST /chat 자리 — FileConverterAgent(app/llms/file_converter_agent.py)를
# 실제 백엔드로 연결한다. 이벤트 계약(tool_start/tool_end/answer_chunk/done)은 목이
# 쓰던 것과 동일하게 맞춰서, chat.js를 고칠 필요 없이 그대로 재사용한다.
#
# 채팅 텍스트 입력창은 파일 경로를 같이 보내지 않는다(파일 변환은 여전히 별도
# 드래그앤드롭 플로우 → POST /tools/file-converter/convert 로 처리됨) — 그래서 지금
# 이 경로는 실질적으로 "file_converter가 뭘 하는 도구인지 설명하는 질문"에 실제
# LLM(gpt-4o-mini)이 답하는 데 쓰인다. 파일 경로까지 채팅으로 넘기는 건 범위 밖.
#
# SSE 이벤트 조립(app/services/chat.py의 ChatService)은 tech(app/routers/tech.py +
# app/services/tech.py) 패턴에 맞춰 라우터에서 분리했다 — 여기는 HTTP 계층만 담당.
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencise import get_chat_service
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    return StreamingResponse(
        service.astream_sse(request.message), media_type="text/event-stream"
    )
