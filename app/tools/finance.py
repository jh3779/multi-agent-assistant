"""금융 데이터 조회 도구.

각 도구는 실패해도 예외를 던지지 않고 실패 문자열을 돌려준다.
도구에서 예외가 새면 이를 호출한 에이전트 루프 전체가 죽기 때문이다.
"""

from datetime import UTC, datetime, timedelta

import requests
import yfinance as yf
from langchain_core.tools.base import ArgsSchema
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.memory import resolve_ticker
from app.schemas.finance import (
    GetExchangeRateInput,
    GetInterestRateInput,
    GetStockPriceInput,
)
from app.tools.base import BaseTool

FRANKFURTER_RATES_URL = "https://api.frankfurter.dev/v2/rates"

# 한국은행 ECOS: 722Y001(시장금리) 통계표의 0101000 항목이 한국은행 기준금리다.
ECOS_SEARCH_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
ECOS_BASE_RATE_STAT = "722Y001"
ECOS_BASE_RATE_ITEM = "0101000"

KOREA_ALIASES = {"KR", "KOR", "KOREA", "한국", "대한민국"}


class FinanceToolSettings(BaseSettings):
    """금융 도구에서만 쓰는 키. 공용 Settings를 건드리지 않으려고 따로 둔다.

    app/setting.py에 ecos_api_key를 추가하면 BaseTool이 제공하는
    self.settings.ecos_api_key로 통일할 수 있고 이 클래스는 지워도 된다.
    """

    ecos_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


finance_settings = FinanceToolSettings()


class GetStockPriceTool(BaseTool):
    name: str = "get_stock_price"
    description: str = (
        "주식·ETF·주가지수의 현재 시장 가격을 조회합니다.\n"
        "사용 예: '삼성전자 주가 알려줘', '테슬라 지금 얼마야', '코스피 지수 알려줘'.\n"
        "환율 질문에는 get_exchange_rate를, 금리 질문에는 get_interest_rate를 쓰세요.\n"
        "반환 형식: '<심볼> 현재 가격: <숫자>'. "
        "통화 단위는 상장 시장을 따릅니다(국내 종목은 원, 미국 종목은 달러).\n"
        "한계: 야후 파이낸스 기준이라 실시간이 아니며 최대 15분 지연될 수 있습니다. "
        "현재가만 조회할 수 있고 특정 과거 날짜의 가격은 알 수 없습니다."
    )
    args_schema: ArgsSchema | None = GetStockPriceInput

    def _run(self, ticker: str) -> str:
        # 종목명이 들어와도 저장된 매핑으로 심볼을 찾아낸다.
        # 매핑 전체(2700여 종목)를 프롬프트에 넣으면 요청당 2만 토큰이 붙으므로
        # LLM에게 심볼 변환을 맡기지 않고 여기서 해결한다.
        symbol = resolve_ticker(ticker)

        if symbol is None:
            return (
                f"'{ticker}'에 해당하는 종목을 찾지 못했습니다. "
                "정식 종목명이나 야후 파이낸스 심볼로 다시 시도하세요."
            )

        # yfinance는 비공식 스크래퍼라 예외 종류가 일정하지 않다.
        # 여기서 새면 에이전트 루프 전체가 죽으므로 도구 경계에서 전부 잡는다.
        try:
            stock = yf.Ticker(symbol)
            price = stock.fast_info["last_price"]
        except Exception as e:  # noqa: BLE001
            return f"{ticker}({symbol}) 가격 조회 실패: {e}"

        return f"{ticker}({symbol}) 현재 가격: {price}"


class GetExchangeRateTool(BaseTool):
    name: str = "get_exchange_rate"
    description: str = (
        "두 통화 사이의 환율을 조회합니다.\n"
        "사용 예: '달러 환율 얼마야', '엔화 대비 원화', '유로 환율 알려줘'.\n"
        "'달러 환율'처럼 대상 통화가 생략되면 USD에서 KRW로 해석합니다.\n"
        "반환 형식: '<기준>/<대상> 환율: <숫자> (<날짜> 기준)'. "
        "숫자는 기준 통화 1단위당 대상 통화 금액입니다.\n"
        "한계: 유럽중앙은행 고시 기준이라 평일 하루 한 번만 갱신되며, "
        "주말과 공휴일에는 직전 영업일 값이 나옵니다. "
        "은행 창구의 매매기준율이나 실시간 시세와는 차이가 있습니다. "
        "암호화폐는 지원하지 않습니다."
    )
    args_schema: ArgsSchema | None = GetExchangeRateInput

    def _run(self, base_currency: str, target_currency: str) -> str:
        try:
            res = requests.get(
                FRANKFURTER_RATES_URL,
                params={
                    "base": base_currency.upper(),
                    "quotes": target_currency.upper(),
                },
                timeout=5,
            )
            res.raise_for_status()
            rows = res.json()
        except requests.RequestException as e:
            return f"환율 조회 실패: {e}"

        if not rows:
            return f"{base_currency}/{target_currency} 환율을 찾을 수 없습니다."

        row = rows[0]

        return f"{row['base']}/{row['quote']} 환율: {row['rate']} ({row['date']} 기준)"


class GetInterestRateTool(BaseTool):
    name: str = "get_interest_rate"
    description: str = (
        "중앙은행이 결정하는 정책금리(기준금리)를 조회합니다.\n"
        "사용 예: '한국 기준금리 얼마야', '기준금리 올랐어?', '금리 몇 퍼센트야'.\n"
        "예금·적금 금리, 대출 금리, 국채 수익률, 회사채 금리는 이 도구로 알 수 없습니다. "
        "그런 질문에는 이 도구를 부르지 말고 확인이 어렵다고 답하세요.\n"
        "반환 형식: '한국은행 기준금리: <숫자>% (<YYYYMM> 기준)'.\n"
        "한계: 한국은행 ECOS 통계를 쓰며 월 단위 최신값이라 "
        "금리 결정 직후에는 반영이 늦을 수 있습니다. "
        "현재 한국만 지원하고, 다른 나라를 넣으면 미지원 안내를 반환합니다."
    )
    args_schema: ArgsSchema | None = GetInterestRateInput

    def _run(self, country: str) -> str:
        if country.strip().upper() not in KOREA_ALIASES:
            return (
                f"'{country}'는 아직 지원하지 않습니다. 현재 한국만 조회할 수 있습니다."
            )

        api_key = finance_settings.ecos_api_key

        if not api_key:
            return (
                "금리 조회 실패: ECOS_API_KEY가 .env에 없습니다. "
                "https://ecos.bok.or.kr/api/ 에서 무료로 발급받을 수 있습니다."
            )

        # 최근 1년치를 받아 마지막 값을 쓴다. 월 단위라 표준시 차이는 영향이 없다.
        today = datetime.now(tz=UTC).date()
        start = (today - timedelta(days=365)).strftime("%Y%m")

        url = "/".join(
            [
                ECOS_SEARCH_URL,
                api_key,
                "json",
                "kr",
                "1",
                "100",
                ECOS_BASE_RATE_STAT,
                "M",
                start,
                today.strftime("%Y%m"),
                ECOS_BASE_RATE_ITEM,
            ]
        )

        try:
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            payload = res.json()
        except requests.RequestException as e:
            return f"금리 조회 실패: {e}"

        # ECOS는 인증 실패·조회 결과 없음도 HTTP 200으로 내려주므로 본문을 봐야 한다.
        if "StatisticSearch" not in payload:
            reason = payload.get("RESULT", {}).get("MESSAGE", "알 수 없는 오류")
            return f"금리 조회 실패: {reason}"

        rows = payload["StatisticSearch"]["row"]
        latest = rows[-1]

        return f"한국은행 기준금리: {latest['DATA_VALUE']}% ({latest['TIME']} 기준)"
