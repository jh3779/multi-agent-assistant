from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings의 env_file은 .env 값을 Settings 필드에만 채워줄 뿐 os.environ에는
# 심지 않는다. 그런데 langsmith/openai SDK는 LANGCHAIN_*·OPENAI_API_KEY를 os.environ에서
# 직접 읽기 때문에(Settings를 거치지 않음), load_dotenv()로 한 번 더 실제 프로세스
# 환경변수에 심어줘야 LangSmith 트레이싱이 켜지고 ChatOpenAI()가 키를 자동으로 찾는다.
load_dotenv()


class Settings(BaseSettings):
    # 전부 기본값을 둬서 .env가 아예 없거나 값이 비어있어도 Settings() 생성 자체는
    # 실패하지 않게 함 — OpenAI/Tavily 키가 필요 없는 도구가 app.tools.base(BaseTool)를
    # 상속하는 것만으로 죽는 걸 막기 위함(file_converter는 지금 @tool 데코레이터 함수라
    # 이 클래스를 안 쓰지만, 다른 도구가 상속해서 쓸 수 있음). 실제로 그 값이 필요한
    # 코드(OpenAI 호출 등)에서 비어있으면 그때 에러를 내야 함.
    openai_api_key: str = ""
    langchain_api_key: str = ""
    langchain_project: str = ""
    langchain_tracing_v2: str = "false"
    naver_client_id: str = ""
    naver_client_secret: str = ""
    youtube_api_key: str = ""
    tavily_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
