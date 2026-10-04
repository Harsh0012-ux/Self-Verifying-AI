from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/sva"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    humaneval_cache_path: Path = Path(".cache/humaneval.jsonl")
    sandbox_image: str = "sva-sandbox:latest"
    verification_candidates: int = 3
    max_repair_attempts: int = 2


settings = Settings()
