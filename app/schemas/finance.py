"""금융 도메인 스키마.

앞부분은 도구 입력 스키마다. 각 필드의 description은 그대로 LLM에게 전달되는
지시문이므로 예시를 구체적으로 적는다.
뒷부분은 HTTP 요청·응답과 SSE 이벤트 스키마다.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class GetStockPriceInput(BaseModel):
    ticker: str = Field(
        description=(
            "종목명 또는 야후 파이낸스 심볼. "
            "국내 상장사는 한글 종목명을 그대로 넣어도 된다(삼성전자, 에코프로비엠). "
            "코스피·코스닥 2600여 종목의 심볼 변환은 도구가 알아서 처리한다. "
            "심볼을 확실히 아는 경우에만 심볼로 넣는다"
            "(미국 종목 AAPL, 국내 005930.KS, 지수 ^KS11). "
            "종목명은 정식 명칭을 쓴다. 예: '현대차'보다 '현대자동차'."
        )
    )


class GetExchangeRateInput(BaseModel):
    base_currency: str = Field(
        description=(
            "기준이 되는 통화의 ISO 4217 코드. 대문자 3글자. "
            "예: 달러 USD, 원 KRW, 엔 JPY, 유로 EUR, 위안 CNY."
        )
    )
    target_currency: str = Field(
        description=(
            "환산할 대상 통화의 ISO 4217 코드. 대문자 3글자. "
            "'달러 환율'처럼 한국 사용자가 통화 하나만 말하면 대상은 KRW다."
        )
    )


class GetInterestRateInput(BaseModel):
    country: str = Field(
        description=(
            "조회할 국가. 한국어 국가명이나 국가 코드를 쓴다. 예: 한국, KR. "
            "질문에 나라가 없으면 한국으로 본다."
        )
    )


class FinanceQuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=500,
        description="금융 관련 질문",
        examples=["삼성전자 주가 알려줘"],
    )


class FinanceAnswerResponse(BaseModel):
    question: str

    answer: str

    tool_results: list[str] = Field(
        description="에이전트가 실제로 조회한 도구 결과. 답변의 근거를 확인할 때 쓴다."
    )


class FinanceStreamEvent(BaseModel):
    """SSE로 내보낼 단일 이벤트.

    delta: 최종 답변 조각
    done:  스트림 종료
    error: 처리 중 발생한 오류
    """

    type: Literal["delta", "done", "error"]

    data: dict[str, Any] = Field(default_factory=dict)
