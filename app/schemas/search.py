"""웹 검색 도구의 입력 스키마."""

from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(
        description=(
            "검색어. 사용자 질문을 그대로 넣지 말고 검색에 맞게 다듬는다. "
            "한국 제도·세금 관련이면 한국어로, 해외 정보면 영어로 쓴다. "
            "예: '예금자보호 한도 2026', '배당소득세율 원천징수', "
            "'ISA 계좌 비과세 한도'. "
            "연도를 붙이면 최신 정보를 찾는 데 도움이 된다."
        )
    )
