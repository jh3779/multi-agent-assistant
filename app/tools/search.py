"""금융 에이전트용 웹 검색 도구.

Tavily 호출과 캐싱은 app/tools/web_search.py의 CachedWebSearchTool을 그대로 쓴다.
구현을 중복하지 않고, 금융 질문에 맞는 설명과 읽기 좋은 결과 형식만 덧입힌다.

원본 응답을 그대로 넘기면 이미지·메타데이터까지 딸려와 5,900토큰이 넘는다.
이 결과는 작성자와 평가자 프롬프트에 각각 들어가므로 정리해서 넘겨야 한다.
"""

from typing import Any

from langchain_core.tools.base import ArgsSchema

from app.schemas.search import WebSearchInput
from app.tools.web_search import CachedWebSearchTool

# 결과가 많아질수록 작성자·평가자 프롬프트가 같이 커진다. 3건이면 충분하다.
SEARCH_MAX_RESULTS = 3

# 본문 전체를 넣으면 토큰이 급증한다. 수치와 문맥을 담기에 이 정도면 된다.
SEARCH_SNIPPET_CHARS = 500


class WebSearchTool(CachedWebSearchTool):
    name: str = "web_search"
    description: str = (
        "웹을 검색해 최신 정보를 확인합니다.\n"
        "사용 예: '예금자보호 한도 얼마야', '배당소득세 몇 퍼센트야', "
        "'ISA 계좌 혜택이 뭐야', '공매도 규제 어떻게 됐어'.\n"
        "세율·한도·규제 기준처럼 정책이나 법 개정으로 바뀌는 수치는 "
        "기억에 의존하지 말고 반드시 이 도구로 확인하세요.\n"
        "주가는 get_stock_price, 환율은 get_exchange_rate, "
        "기준금리는 get_interest_rate를 쓰세요. 그쪽이 더 정확합니다.\n"
        "반환 형식: 검색 결과 여러 건이 '[n] 제목 / 출처 URL / 발췌' 순으로 나옵니다.\n"
        "한계: 웹 문서라 오래된 페이지가 섞일 수 있으므로 "
        "본문에 적힌 시점을 함께 확인해야 합니다."
    )
    args_schema: ArgsSchema | None = WebSearchInput
    max_results: int = SEARCH_MAX_RESULTS

    def format_results(self, payload: Any) -> str:
        results = payload.get("results") if isinstance(payload, dict) else None

        if not results:
            return "검색 결과가 없습니다."

        blocks = []

        for i, item in enumerate(results, 1):
            snippet = str(item.get("content", "")).strip()[:SEARCH_SNIPPET_CHARS]
            blocks.append(
                f"[{i}] {item.get('title', '제목 없음')}\n"
                f"    출처: {item.get('url', '')}\n"
                f"    {snippet}"
            )

        return "\n".join(blocks)

    def _run(self, query: str, **kwargs: Any) -> str:
        if not self.settings.tavily_api_key:
            return (
                "검색 실패: TAVILY_API_KEY가 .env에 없습니다. "
                "https://tavily.com 에서 발급받을 수 있습니다."
            )

        # 외부 API라 예외 종류를 특정할 수 없다. 도구 경계에서 전부 잡는다.
        try:
            payload = super()._run(query, **kwargs)
        except Exception as e:  # noqa: BLE001
            return f"검색 실패: {e}"

        return self.format_results(payload)

    async def _arun(self, query: str, **kwargs: Any) -> str:
        if not self.settings.tavily_api_key:
            return (
                "검색 실패: TAVILY_API_KEY가 .env에 없습니다. "
                "https://tavily.com 에서 발급받을 수 있습니다."
            )

        try:
            payload = await super()._arun(query, **kwargs)
        except Exception as e:  # noqa: BLE001
            return f"검색 실패: {e}"

        return self.format_results(payload)
