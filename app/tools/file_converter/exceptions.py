# 변환 실패를 라우터에서 HTTPException으로 바꾸기 위해 별도 예외로 감싼다.
class UnsupportedFormatError(ValueError):
    pass


# 변환이 너무 오래 걸리면 asyncio.wait_for가 TimeoutError를 던지는데,
# 그걸 그대로 HTTPException으로 바꾸면 504 Gateway Timeout이 아니라
# 500 Internal Server Error가 되므로, 별도 예외로 감싸서 라우터에서 504로 바꿔주도록 한다.
class ConversionTimeoutError(RuntimeError):
    pass
