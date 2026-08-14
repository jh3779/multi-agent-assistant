from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TechAnswer(BaseModel):
    topic: str = Field(description="답변하는 기술 또는 개념의 이름")

    answer: str = Field(description="해당 질문에 대한 설명")

    example: str | None = Field(
        default=None, description="필요한 경우 간단한 코드 또는 사용 예제"
    )

    # LLM이 출처를 빠뜨려도 파싱이 실패하지 않도록 기본값을 둔다.
    # 출처가 비었는지는 답변 품질 검증 단계에서 걸러낸다.
    sources: list[str] = Field(
        default_factory=list, description="해당 답변 작성에 사용한 출처 URL"
    )

    def to_markdown(self) -> str:
        parts = [f"## {self.topic}", "", self.answer]

        if self.example:
            parts += ["", "### 예제", "", self.example]

        if self.sources:
            parts += ["", "### 출처", ""]
            parts += [f"- <{url}>" for url in self.sources]

        return "\n".join(parts)


class TechAgentResponse(BaseModel):
    status: Literal[
        "success",
        "unsupported",
        "insufficient_sources",
        "validation_failed",
    ] = Field(
        description=(
            "success: 정상적으로 답변한 경우, "
            "unsupported: 개발 관련 질문이 아닌 경우, "
            "insufficient_sources: 신뢰할 수 있는 자료가 부족한 경우, "
            "validation_failed: 답변 품질 검증에 최종 실패한 경우로, "
            "시스템이 설정하는 값이므로 직접 사용하지 않는다"
        )
    )

    message: str | None = Field(
        default=None, description="답변 불가 또는 오류 상태에 대한 안내 메시지"
    )

    answers: list[TechAnswer] = Field(
        default_factory=list,
        description=(
            "사용자 질문에 포함된 독립적인 질문별 답변. "
            "질문이 여러 개라면 각각 별도의 항목으로 반환한다."
        ),
    )

    @model_validator(mode="after")
    def set_message(self):
        if self.status == "unsupported":
            self.message = (
                "죄송합니다. 현재 기술적인 지식이 부족하여 "
                "해당 질문에 대한 답변을 제공할 수 없습니다."
            )

        elif self.status == "insufficient_sources":
            self.message = "신뢰할 수 있는 자료를 충분히 확인하지 못했습니다."

        elif self.status == "validation_failed":
            self.message = (
                "죄송합니다. 답변을 여러 번 다시 작성했지만 "
                "품질 기준을 만족하지 못해 답변을 제공할 수 없습니다."
            )

        elif self.status == "success":
            self.message = None

        return self

    def to_markdown(self) -> str:
        """API로 그대로 내려보낼 수 있는 마크다운 문자열을 만든다."""
        if self.status != "success":
            return self.message or ""

        return "\n\n".join(answer.to_markdown() for answer in self.answers)


class TechQuestionRequest(BaseModel):
    question: str = Field(min_length=2, description="개발 관련 질문")


class TechStreamEvent(BaseModel):
    """SSE로 내보낼 단일 이벤트.

    status: 검색, 검증 등 진행 상황 안내
    delta:  최종 답변 마크다운 조각
    result: 완성된 답변 전체
    error:  처리 중 발생한 오류
    """

    type: Literal["status", "delta", "result", "error"]

    data: dict[str, Any] = Field(default_factory=dict)

    # 서버 내부에서만 쓰는 원본 응답. 클라이언트로는 내보내지 않는다.
    response: TechAgentResponse | None = Field(
        default=None,
        exclude=True,
    )


class AnswerValidationResponse(BaseModel):
    score: int = Field(ge=0, le=100, description="답변 품질 점수")

    reason: str = Field(description="판단 이유")

    missing_points: list[str] = Field(description="답변에서 빠진 내용")
