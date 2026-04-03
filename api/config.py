from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_db_url: str = "postgresql+asyncpg://dqa:dqa_password@postgres:5432/dqa_app"
    data_source_url: str = "postgresql+asyncpg://dqa:dqa_password@postgres:5432/dqa_erp"

    model_provider: str = "anthropic"
    model_name: str = "claude-opus-4-6"
    embeddings_provider: str = "local"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    databricks_host: str = ""
    databricks_token: str = ""

    env: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
