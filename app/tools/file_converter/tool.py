# app/tools/base.py의 BaseTool(LangChain)을 상속한, "LLM이 도구로 호출하는" 경로.
# 채팅 UI가 fetch()로 직접 부르는 router.py와는 별개 — 지금은 그걸 호출할 진짜
# LLM(Main LLM)이 없어서, 이 클래스는 스키마 생성(bind_tools)과 개별 함수 호출까지만
# 검증됐고 실제 에이전트 루프 안에서 호출된 적은 없다.
import asyncio
from pathlib import Path

from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.file_converter.converter import (
    SUPPORTED_FORMATS,
    UnsupportedFormatError,
    convert,
)


class FileConverterArgs(BaseModel):
    # LLM의 도구 호출 인자는 JSON(텍스트)만 가능해서 파일 바이트를 직접 못 받음 —
    # 그래서 바이트 대신 서버 측 경로를 받는 구조로 설계함(파일이 어떻게 그
    # 경로에 놓이는지는 아직 미정 — Main LLM/업로드 파이프라인이 생기면 정해질 부분).
    file_path: str = Field(description="변환할 원본 파일의 서버 측 경로")
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
    # 로직은 asyncio.to_thread를 쓰는 비동기 함수라 그대로 위임한다.
    def _run(self, file_path: str, target_format: str) -> tuple[str, bytes]:
        return asyncio.run(self._arun(file_path, target_format))

    async def _arun(self, file_path: str, target_format: str) -> tuple[str, bytes]:
        path = Path(file_path)
        if not path.exists():
            raise ToolException(f"파일을 찾을 수 없습니다: {file_path}")

        source_format = path.suffix.lstrip(".")
        try:
            converted = await convert(path.read_bytes(), source_format, target_format)
        except UnsupportedFormatError as exc:
            raise ToolException(str(exc)) from exc

        return f"{path.name}을(를) {target_format}로 변환했습니다.", converted
