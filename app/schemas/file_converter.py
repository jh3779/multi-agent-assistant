from pydantic import BaseModel, Field

from app.tools.file_converter.converter import SUPPORTED_FORMATS


class FileConverterArgs(BaseModel):
    """file_converter 도구(app/tools/file_converter/tool.py)의 입력 스키마."""

    file_path: str = Field(
        description="변환할 원본 파일의 서버 측 경로(업로드 디렉터리 내부)"
    )
    target_format: str = Field(
        description=f"변환할 대상 포맷. 지원 포맷: {', '.join(SUPPORTED_FORMATS)} (PDF 미지원)"
    )


class FileConversionAnswer(BaseModel):
    """FileConverterAgent(app/llms/file_converter_agent.py)의 구조화 출력."""

    used_tool: bool = Field(description="file_converter 도구를 실제로 호출했는지")
    tool_name: str | None = Field(
        default=None, description="호출한 도구 이름(안 썼으면 null)"
    )
    summary: str = Field(description="사용자에게 보여줄 결과 요약")
