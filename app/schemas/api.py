"""HTTP 요청·응답 스키마.

FastAPI가 이 모델로 요청을 검증하고 /docs 문서를 자동 생성한다.
"""

from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=500,
        description="금융 관련 질문",
        examples=["삼성전자 주가 알려줘"],
    )


class AskResponse(BaseModel):
    question: str
    answer: str
    tool_results: list[str] = Field(
        description="에이전트가 실제로 조회한 도구 결과. 답변의 근거를 확인할 때 쓴다."
    )


class StreamEvent(BaseModel):
    """SSE 한 건. 프론트가 type으로 렌더링을 구분한다."""

    type: Literal["answer", "done", "error"]
    text: str = ""
