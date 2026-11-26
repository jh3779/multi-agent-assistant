import tempfile
from pathlib import Path

from langchain_core.tools import ToolException, tool

from app.schemas.file_converter import FileConverterArgs
from app.tools.file_converter.converter import convert
from app.tools.file_converter.exceptions import (
    ConversionTimeoutError,
    UnsupportedFormatError,
)

# LLM이 자유롭게 채우는 file_path를 검증 없이 그대로 읽으면 임의 파일 읽기가
# 가능해짐(예: ".env를 html로 변환해줘" 같은 프롬프트 인젝션). 이 디렉터리 밖의
# 경로는 전부 거부한다 — 향후 업로드 파이프라인이 생기면 파일을 여기에 둘 것.
ALLOWED_DIR = Path(tempfile.gettempdir()) / "multi-agent-assistant-uploads"
ALLOWED_DIR.mkdir(parents=True, exist_ok=True)


# "LLM이 도구로 호출하는" 경로 — 채팅 UI가 fetch()로 직접 부르는 app/routers/file_converter.py와는
# 별개다. 이쪽은 app/llms/file_converter_agent.py의 FileConverterAgent가 진짜
# LLM(gpt-4o-mini) 에이전트 루프 안에서 호출한다(실제 OPENAI_API_KEY로 docx/html
# 변환까지 end-to-end 검증됨). 다만 아직 HTTP 엔드포인트로는 안 열려있어 채팅
# UI에서 이 경로를 타진 않는다.
#
# app/tools/base.py의 BaseTool(클래스 상속형)이 아니라 @tool 데코레이터(함수형)로
# 선언함 — file_converter는 공용 BaseTool이 주는 settings가 필요 없어서(순수 pandoc
# 변환, API 키 불필요) 더 간단한 이 패턴을 쓸 수 있었다. 동기 호출(.invoke())은
# StructuredTool이 async-only 함수에 대해 자동으로 명확한 NotImplementedError를
# 던져주므로(이벤트 루프 안에서 asyncio.run()을 잘못 부르는 문제를 우리가 따로
# 막아줄 필요가 없음), 예전 클래스형 구현에 있던 _run() 이벤트 루프 가드도 불필요.
@tool(
    "file_converter",
    args_schema=FileConverterArgs,
    response_format="content_and_artifact",
)
async def file_converter(file_path: str, target_format: str) -> tuple[str, bytes]:
    """문서 파일을 다른 포맷으로 변환한다."""
    path = Path(file_path).resolve()
    try:
        path.relative_to(ALLOWED_DIR.resolve())
    except ValueError:
        raise ToolException(
            f"허용되지 않은 경로입니다: {file_path} "
            f"(업로드 디렉터리({ALLOWED_DIR}) 밖의 파일은 읽을 수 없음)"
        ) from None
    if not path.exists():
        raise ToolException(f"파일을 찾을 수 없습니다: {file_path}")

    source_format = path.suffix.lstrip(".")
    try:
        converted = await convert(path.read_bytes(), source_format, target_format)
    except (UnsupportedFormatError, ConversionTimeoutError) as exc:
        raise ToolException(str(exc)) from exc

    return f"{path.name}을(를) {target_format}로 변환했습니다.", converted
