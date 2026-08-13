"""금융 도구의 입력 스키마.

각 필드의 description은 그대로 LLM에게 전달되는 지시문이다.
도구 호출 인자가 틀리는 것을 막는 것이 목적이므로 예시를 구체적으로 적는다.
"""

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
