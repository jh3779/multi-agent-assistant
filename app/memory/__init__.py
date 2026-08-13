"""에이전트가 참고하는 저장된 지식.

종목명 -> 야후 파이낸스 심볼 매핑을 JSON으로 분리해 둔다. 종목을 추가할 때
파이썬을 건드릴 필요가 없고, 비개발 팀원도 JSON만 고치면 된다.

파일이 셋으로 나뉘어 있는 이유:
- tickers.json  전체 매핑(2700여 종목). 프롬프트에 넣기엔 너무 커서
                파이썬 쪽 resolve_ticker()로만 조회한다.
- featured.json 프롬프트에 실을 대표 종목 소수. 전체를 넣으면 요청당
                2만 토큰이 넘게 붙는다.
- aliases.json  '현대차' -> '현대자동차'처럼 통칭을 정식 명칭으로 잇는 표.
"""

import json
import re
from pathlib import Path

MEMORY_DIR = Path(__file__).parent
TICKERS_PATH = MEMORY_DIR / "tickers.json"
FEATURED_PATH = MEMORY_DIR / "featured.json"
ALIASES_PATH = MEMORY_DIR / "aliases.json"

# 이미 야후 심볼 형태인지 판별한다. 005930.KS / AAPL / ^KS11 등.
SYMBOL_PATTERN = re.compile(r"^(\^[A-Z0-9]+|[A-Z.]{1,6}|\d{6}\.(KS|KQ))$")


def load_json_map(path: Path) -> dict[str, str]:
    """매핑 파일을 읽는다.

    파일이 없거나 깨져 있어도 에이전트는 떠야 한다. 매핑이 비면 LLM이
    심볼을 직접 유추하게 되고, 그건 프롬프트의 .KS/.KQ 규칙이 받아준다.
    """

    # except를 둘로 나눈 이유: `except (A, B)`는 ruff가 프로젝트 타깃(3.14)에 맞춰
    # 괄호를 지우는데, 그 문법은 3.13 이하에서 파싱되지 않는다. pre-commit 훅이
    # 3.13에서 돌면 커밋이 막힌다. 이렇게 두면 어느 버전에서도 안전하다.
    try:
        with path.open(encoding="utf-8") as f:
            loaded = json.load(f)
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}

    if not isinstance(loaded, dict):
        return {}

    return {str(k): str(v) for k, v in loaded.items()}


def load_tickers() -> dict[str, str]:
    """종목명 -> 심볼 전체 매핑."""

    return load_json_map(TICKERS_PATH)


def load_featured() -> dict[str, str]:
    """프롬프트에 실을 대표 종목만."""

    featured = load_json_map(FEATURED_PATH)

    return featured or dict(list(load_tickers().items())[:20])


def load_aliases() -> dict[str, str]:
    """통칭 -> 정식 명칭."""

    return load_json_map(ALIASES_PATH)


def normalize(text: str) -> str:
    """공백·괄호·마침표를 지워 표기 차이를 흡수한다."""

    return re.sub(r"[\s().,\-_]", "", text).lower()


def resolve_ticker(text: str) -> str | None:
    """종목명이나 심볼을 야후 파이낸스 심볼로 바꾼다.

    LLM이 심볼을 정확히 못 맞혀도 종목명만 넘기면 여기서 해결된다.
    찾지 못하면 None을 돌려주고, 호출한 쪽이 안내 문구를 만든다.
    """

    query = text.strip()

    if not query:
        return None

    tickers = load_tickers()
    aliases = load_aliases()

    # 1. 이미 심볼 형태면 그대로 쓴다. 표에 없는 해외 종목도 통과시켜야 한다.
    if SYMBOL_PATTERN.match(query.upper()) and query.upper() == query:
        return query

    # 2. 정식 명칭으로 바로 찾기
    if query in tickers:
        return tickers[query]

    # 3. 통칭이면 정식 명칭으로 바꿔 다시 찾기
    official = aliases.get(query)
    if official and official in tickers:
        return tickers[official]

    # 4. 표기 차이를 무시하고 찾기 (SK 하이닉스 / Apple Inc / apple)
    folded = {normalize(k): v for k, v in tickers.items()}
    folded.update(
        {normalize(k): tickers[v] for k, v in aliases.items() if v in tickers}
    )

    return folded.get(normalize(query))


def save_tickers(tickers: dict[str, str]) -> None:
    """전체 매핑을 파일에 다시 쓴다. 새 종목을 학습시켜 둘 때 쓴다."""

    with TICKERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False, indent=2)
        f.write("\n")
