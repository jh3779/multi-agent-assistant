# app/tools/base.py의 BaseTool(LangChain)을 상속한, "LLM이 도구로 호출하는" 경로.
# 채팅 UI가 fetch()로 직접 부르는 router.py와는 별개 — 이쪽은 app/llms/
# file_converter_agent.py의 ask()가 진짜 LLM(gpt-4o-mini) 에이전트 루프 안에서
# 호출한다(실제 OPENAI_API_KEY로 docx/html 변환까지 end-to-end 검증됨). 다만
# 아직 HTTP 엔드포인트로는 안 열려있어 채팅 UI에서 이 경로를 타진 않는다.
import asyncio
import tempfile
from pathlib import Path

from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.file_converter.converter import (
    SUPPORTED_FORMATS,
    ConversionTimeoutError,
    UnsupportedFormatError,
    convert,
)

# LLM이 자유롭게 채우는 file_path를 검증 없이 그대로 읽으면 임의 파일 읽기가
# 가능해짐(예: ".env를 html로 변환해줘" 같은 프롬프트 인젝션). 이 디렉터리 밖의
# 경로는 전부 거부한다 — 향후 업로드 파이프라인이 생기면 파일을 여기에 둘 것.
ALLOWED_DIR = Path(tempfile.gettempdir()) / "lg-cns-file-converter-uploads"
ALLOWED_DIR.mkdir(parents=True, exist_ok=True)


class FileConverterArgs(BaseModel):
    # LLM의 도구 호출 인자는 JSON(텍스트)만 가능해서 파일 바이트를 직접 못 받음 —
    # 그래서 바이트 대신 서버 측 경로를 받는 구조로 설계함. 경로는 ALLOWED_DIR
    # 안에 있어야 함(_arun에서 강제) — 업로드 파이프라인은 파일을 거기에 둬야 함.
    file_path: str = Field(
        description="변환할 원본 파일의 서버 측 경로(업로드 디렉터리 내부)"
    )
    target_format: str = Field(
        description=f"변환할 대상 포맷. 지원 포맷: {', '.join(SUPPORTED_FORMATS)} (PDF 미지원)"
    )


class FileConverterTool(BaseTool):
    name: str = "file_converter"
    description: str = (
        "문서 파일을 다른 포맷으로 변환한다. "
        f"지원 포맷: {', '.join(SUPPORTED_FORMATS)} (PDF는 지원하지 않음)."
    )
    args_schema: type[BaseModel] = FileConverterArgs
    # 변환 결과(바이너리)를 억지로 문자열에 우겨넣지 않기 위해 텍스트 요약(LLM용)과
    # 실제 바이트(artifact, 앱 레이어용)를 분리해서 반환하는 LangChain 표준 방식.
    response_format: str = "content_and_artifact"

    # BaseTool의 필수 추상 메서드는 동기 _run뿐이라 구현은 해야 하지만, 실제 변환
    # 로직은 asyncio.to_thread를 쓰는 비동기 함수라 그대로 위임한다. asyncio.run()은
    # 이미 이벤트 루프가 도는 스레드에서 부르면 RuntimeError를 던지므로, 그 상황을
    # 먼저 감지해서 원인이 분명한 ToolException으로 바꿔준다.
    def _run(self, file_path: str, target_format: str) -> tuple[str, bytes]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._arun(file_path, target_format))
        raise ToolException(
            "동기 _run()은 이미 실행 중인 이벤트 루프 안에서 호출할 수 없습니다 — "
            "async 컨텍스트에서는 _arun()/ainvoke()를 쓰세요."
        )

    async def _arun(self, file_path: str, target_format: str) -> tuple[str, bytes]:
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
