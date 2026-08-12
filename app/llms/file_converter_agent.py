# FileConverterTool을 실제 LLM이 도구로 호출하는 최소 경로 — 지금까지 tool.py는
# bind_tools() 스키마 생성과 개별 함수 호출까지만 검증됐고, 진짜 에이전트 루프
# 안에서 호출된 적은 없었음. 그 공백을 메우는 자리표시자 겸 데모.
#
# Main LLM(중앙 오케스트레이터)은 팀이 폐기했으므로, 이건 file_converter 하나만
# 다루는 범위 좁은 에이전트다 — 다른 Tool이 생기면 그때 합치거나 라우팅을 얹으면 됨.
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.setting import settings
from app.tools.file_converter.tool import FileConverterTool

_SYSTEM_PROMPT = (
    "너는 문서 변환을 도와주는 어시스턴트다. 사용자가 파일 변환을 요청하면 "
    "file_converter 도구를 호출해서 실제로 변환하고, 결과를 간단히 설명해라. "
    "변환이 필요 없는 질문이면 도구를 호출하지 말고 바로 답해라."
)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)


class FileConversionAnswer(BaseModel):
    used_tool: bool = Field(description="file_converter 도구를 실제로 호출했는지")
    tool_name: str | None = Field(
        default=None, description="호출한 도구 이름(안 썼으면 null)"
    )
    summary: str = Field(description="사용자에게 보여줄 결과 요약")


async def ask(
    question: str, file_path: str | None = None
) -> tuple[FileConversionAnswer, bytes | None]:
    full_question = (
        question
        if file_path is None
        else f"{question}\n\n(첨부 파일 경로: {file_path})"
    )

    tool = FileConverterTool()
    # os.environ에 OPENAI_API_KEY를 심어주는 load_dotenv()가 앱 어디에도 없어서,
    # pydantic-settings가 이미 읽어둔 settings에서 직접 키를 넘겨준다(더미 키로만
    # 검증됐던 이유 — 실제 키로는 인증 에러가 났었음).
    model = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, api_key=settings.openai_api_key
    )
    messages = _PROMPT.format_messages(question=full_question)

    # 1단계: 도구를 쓸지 말지 LLM이 스스로 판단(Function Calling)
    response = await model.bind_tools([tool]).ainvoke(messages)

    tool_calls = getattr(response, "tool_calls", None) or []
    if not tool_calls:
        return FileConversionAnswer(used_tool=False, summary=response.content), None

    # 2단계: 실제로 도구 실행 — 여기가 이전엔 아무도 안 지나가 본 경로
    call = tool_calls[0]
    content, artifact = await tool._arun(**call["args"])

    messages.append(response)
    messages.append(ToolMessage(content=content, tool_call_id=call["id"]))

    # 3단계: 도구 결과를 반영해 Pydantic 구조화 출력으로 최종 답변 생성
    result = await model.with_structured_output(FileConversionAnswer).ainvoke(messages)
    return result, artifact
