from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.tools.file_converter.converter import (
    SUPPORTED_FORMATS,
    UnsupportedFormatError,
    convert,
)

router = APIRouter(prefix="/tools/file-converter", tags=["file-converter"])

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
    try:
        converted = await convert(content, source_format, target_format)
    except UnsupportedFormatError as exc:
        raise HTTPException(400, str(exc)) from exc

    dst_ext = target_format.lower().lstrip(".")
    media_type = _MEDIA_TYPES.get(dst_ext, "application/octet-stream")
    return Response(
        content=converted,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="converted.{dst_ext}"'},
    )
