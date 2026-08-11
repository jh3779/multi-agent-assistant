from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    naver_client_id: str
    naver_client_secret: str
    langchain_api_key: str
    langchain_project: str
    langchain_tracing_v2: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()