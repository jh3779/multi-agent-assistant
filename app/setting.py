from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 전부 기본값을 둬서 .env가 아예 없거나 값이 비어있어도 Settings() 생성 자체는
    # 실패하지 않게 함 — file_converter처럼 OpenAI/Naver 키가 필요 없는 도구가
    # app.tools.base(BaseTool)를 상속하는 것만으로 죽는 걸 막기 위함. 실제로 그
    # 값이 필요한 코드(OpenAI 호출 등)에서 비어있으면 그때 에러를 내야 함.
    openai_api_key: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""
    langchain_api_key: str = ""
    langchain_project: str = ""
    langchain_tracing_v2: str = "false"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
