from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres connection string, e.g.
    # postgresql+psycopg2://user:password@localhost:5432/hcp_crm
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hcp_crm"

    # Groq API
    groq_api_key: str = ""
    groq_model_primary: str = "gemma2-9b-it"
    groq_model_fallback: str = "llama-3.3-70b-versatile"

    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
