import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pypandoc

from app.tools.file_converter.exceptions import (
    ConversionTimeoutError,
    UnsupportedFormatError,
)

# pandoc --list-input-formats / --list-output-formats로 실제 지원 여부를 확인하고
# 등록함. PDF는 뺐음 — pandoc은 PDF용 리더가 아예 없어 입력으로 못 읽고, 출력하려면
# LaTeX 같은 별도 엔진이 더 필요해서 5일 스프린트엔 부담이라 스코프 제외.
#
# 입력/출력을 별도 dict로 둔 이유: 확장자별로 방향에 따라 pandoc 포맷명이 다를 수
# 있어서(예: txt는 읽을 땐 "markdown"으로 취급 — pandoc엔 순수 텍스트 전용 리더가
# 없음 — 하지만 쓸 땐 "plain"). 하나로 합치면 이런 비대칭을 표현할 수 없음.
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

# pandoc이 멈추거나 비정상적으로 오래 걸리는 파일(악의적이거나 그냥 거대한 파일)에
# 대비한 상한선. asyncio.wait_for는 "기다리는 걸 포기"할 뿐 백그라운드 스레드 자체를
# 강제 종료하진 못하지만, 최소한 호출자가 무한정 멈춰있진 않게 해준다.
CONVERT_TIMEOUT_SECONDS = 30


## 변환 로직 — app/routers/file_converter.py와 tool.py에서 공유한다.
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

    # pandoc 호출은 subprocess를 기다리는 blocking 작업 — 그대로 부르면 변환하는
    # 동안 FastAPI의 이벤트 루프가 막혀서 같은 프로세스의 다른 요청(SSE 스트리밍 등)도
    # 같이 멈춤. 별도 스레드로 돌려서 이벤트 루프는 계속 다른 일을 하게 함.
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _convert_sync,
                content,
                src_ext,
                src_pandoc_format,
                dst_ext,
                dst_pandoc_format,
            ),
            timeout=CONVERT_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise ConversionTimeoutError(
            f"변환이 {CONVERT_TIMEOUT_SECONDS}초 안에 끝나지 않았습니다: {source_format} -> {target_format}"
        ) from exc


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
