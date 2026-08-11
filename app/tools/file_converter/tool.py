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
    response_format: str = "content_and_artifact"

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
