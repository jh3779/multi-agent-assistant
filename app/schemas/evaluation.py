"""검증·평가 단계의 출력 스키마.

도구 입력 스키마(app/schemas/finance.py)와 달리 이쪽은 LLM이나 검증 로직이
"채워서 돌려주는" 형식이다. AnswerEvaluation은 with_structured_output에 물려
평가 LLM이 직접 채우므로, 각 필드의 description이 그대로 지시문이 된다.
"""

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """도구 결과 검증의 반환 형식."""

    is_valid: bool
    reason: str


class AnswerEvaluation(BaseModel):
    """답변 품질 평가의 구조화 출력. 최종 판정은 평가 LLM이 내린다.

    필드 순서가 곧 모델의 사고 순서다. 구조화 출력은 위에서 아래로 생성되므로
    근거 서술 -> 항목별 점검 -> 최종 판정 순으로 두어야 한다. 판정을 먼저 두면
    아무 검토 없이 찍고 나서 근거를 끼워 맞춘다.
    """

    reason: str = Field(
        description=(
            "판정 근거를 먼저 서술한다. "
            "문제가 있다면 무엇을 어떻게 고쳐야 하는지 구체적으로 쓴다."
        )
    )
    unsupported_numbers: list[str] = Field(
        description=(
            "바뀔 수 있는 수치인데 도구 조회 결과에 근거 없이 제시된 것을 나열한다. "
            "대상은 두 종류다. (1) 현재 주가·환율·금리처럼 시시각각 변하는 값, "
            "(2) 세율·한도·규제 기준처럼 정책이나 법으로 바뀌는 값. "
            "도구 결과의 값을 단위나 자릿수만 바꿔 쓴 것은 근거가 있는 것으로 본다. "
            "확정된 역사적 사실(코스피 산출 기준일 1980년)과 계산 공식은 넣지 않는다. "
            "문제가 없으면 빈 리스트."
        )
    )
    hides_tool_failure: bool = Field(
        description=(
            "도구 결과에 [실패]가 있는데 답변이 이를 숨기고 아는 것처럼 말했으면 true. "
            "[실패]가 없거나 답변이 실패 사실을 밝혔으면 false."
        )
    )
    answers_question: bool = Field(
        description="사용자가 물어본 내용에 답했으면 true. 동문서답이면 false."
    )
    is_valid: bool = Field(
        description=(
            "위 점검을 종합한 최종 판정. 이 답변을 사용자에게 그대로 내보내도 되면 true. "
            "unsupported_numbers가 비어 있지 않거나, hides_tool_failure가 true거나, "
            "answers_question이 false면 반드시 false. "
            "도구 조회에 실패했더라도 답변이 그 사실을 솔직히 밝혔다면 true다. "
            "정보가 없다고 정직하게 답한 것은 좋은 답변이지 탈락 사유가 아니다."
        )
    )
