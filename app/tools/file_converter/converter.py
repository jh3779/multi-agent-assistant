import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pypandoc

# pandoc이 실제로 읽고/쓸 수 있는 포맷만 등록. PDF는 출력에 별도 엔진(LaTeX 등)이
# 필요해서 지금은 지원 목록에서 제외 — 필요해지면 추가.
_INPUT_FORMATS = {
    "docx": "docx",
    "html": "html",
    "htm": "html",
    "md": "markdown",
    "markdown": "markdown",
    "txt": "markdown",
    "odt": "odt",
    "rtf": "rtf",
    "pptx": "pptx",
    "epub": "epub",
    "rst": "rst",
}
_OUTPUT_FORMATS = {
    "docx": "docx",
    "html": "html",
    "htm": "html",
    "md": "markdown",
    "markdown": "markdown",
    "txt": "plain",
    "odt": "odt",
    "rtf": "rtf",
    "pptx": "pptx",
    "epub": "epub",
    "rst": "rst",
}

SUPPORTED_FORMATS = sorted(set(_INPUT_FORMATS) | set(_OUTPUT_FORMATS))


class UnsupportedFormatError(ValueError):
    pass


async def convert(content: bytes, source_format: str, target_format: str) -> bytes:
    src_ext = source_format.lower().lstrip(".")
    dst_ext = target_format.lower().lstrip(".")

    src_pandoc_format = _INPUT_FORMATS.get(src_ext)
    dst_pandoc_format = _OUTPUT_FORMATS.get(dst_ext)
    if src_pandoc_format is None or dst_pandoc_format is None:
        raise UnsupportedFormatError(
            f"지원하지 않는 변환: {source_format} -> {target_format} "
            f"(지원 포맷: {', '.join(SUPPORTED_FORMATS)})"
        )

    return await asyncio.to_thread(
        _convert_sync, content, src_ext, src_pandoc_format, dst_ext, dst_pandoc_format
    )


def _convert_sync(
    content: bytes,
    src_ext: str,
    src_pandoc_format: str,
    dst_ext: str,
    dst_pandoc_format: str,
) -> bytes:
    with TemporaryDirectory() as tmp:
        in_path = Path(tmp) / f"input.{src_ext}"
        out_path = Path(tmp) / f"output.{dst_ext}"
        in_path.write_bytes(content)

        extra_args = ["--standalone"] if dst_pandoc_format == "html" else []
        # --standalone: html은 기본으로 <head> 없는 조각(fragment)만 내보내서
        # <meta charset="utf-8">가 빠짐 — 파일 단독으로 열었을 때 한글 등
        # 비ASCII 문자가 브라우저의 인코딩 추측 실패로 깨져 보이는 원인이었음.
        # 완전한 문서로 만들어 스스로 UTF-8임을 선언하게 함.

        pypandoc.convert_file(
            str(in_path),
            dst_pandoc_format,
            format=src_pandoc_format,
            outputfile=str(out_path),
            extra_args=extra_args,
        )
        return out_path.read_bytes()
