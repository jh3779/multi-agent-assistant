from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.tools.file_converter.converter import SUPPORTED_FORMATS, convert
from app.tools.file_converter.exceptions import (
    ConversionTimeoutError,
    UnsupportedFormatError,
)

# 업로드 크기 상한 — 없으면 요청 하나가 서버 메모리를 무제한으로 잡아먹을 수 있음.
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB

# 이 라우터는 "사람이 쓰는 채팅 UI"가 fetch()로 직접 호출하는 HTTP API 경로다.
# LLM이 도구로 호출하는 경로는 별도로 tool.py(@tool 데코레이터 함수 file_converter)에 있음 —
# 두 소비자의 호출 방식이 달라서(HTTP 요청 vs 함수 호출 스키마) 나눠뒀고,
# 실제 변환 로직(converter.convert)은 하나만 두고 공유한다.
router = APIRouter(prefix="/tools/file-converter", tags=["file-converter"])

# 텍스트 계열 포맷에 charset=utf-8을 명시한 이유: converter.py의 --standalone
# 수정(html 자체 선언)과는 별개로, HTTP 레이어에서도 이중으로 인코딩을 명시해
# 클라이언트가 추측할 여지를 없앰(원래 겪었던 한글 깨짐 버그의 재발 방지).
_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "odt": "application/vnd.oasis.opendocument.text",
    "html": "text/html; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "rtf": "application/rtf",
    "epub": "application/epub+zip",
    "rst": "text/x-rst; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
}


@router.get("/formats")
async def list_formats() -> dict[str, list[str]]:
    return {"supported_formats": SUPPORTED_FORMATS}


@router.post("/convert")
async def convert_file(file: UploadFile, target_format: str = Form(...)) -> Response:
    filename = file.filename or ""
    if "." not in filename:
        raise HTTPException(400, "파일 확장자로 원본 포맷을 판별할 수 없습니다")
    source_format = filename.rsplit(".", 1)[-1]

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"파일이 너무 큽니다 (최대 {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB)",  # 이거 fastAPI에서 413으로 처리되나? 확인 필요
        )

    try:
        converted = await convert(content, source_format, target_format)
    except UnsupportedFormatError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ConversionTimeoutError as exc:
        raise HTTPException(504, str(exc)) from exc

    dst_ext = target_format.lower().lstrip(".")
    media_type = _MEDIA_TYPES.get(dst_ext, "application/octet-stream")
    # attachment로 강제: 브라우저가 html/txt 등을 새 탭에 바로 렌더링하지 않고
    # 항상 다운로드하게 함 — 채팅 UI가 "다운로드 링크" UX를 기대하고 있어서.
    return Response(
        content=converted,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="converted.{dst_ext}"'},
    )
