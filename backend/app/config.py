import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    bank_api_base_url: str = "http://localhost:8001"
    max_retry_count: int = 3
    max_agent_loops: int = 5
    max_schema_retries: int = 3
    database_url: str = "sqlite:///./smart_rec.db"
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")


def load_settings() -> Settings:
    load_dotenv()  # finds .env by walking up from this file (repo root .env works)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        bank_api_base_url=os.getenv("BANK_API_BASE_URL", "http://localhost:8001"),
        max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "3")),
        max_agent_loops=int(os.getenv("MAX_AGENT_LOOPS", "5")),
        max_schema_retries=int(os.getenv("MAX_SCHEMA_RETRIES", "3")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./smart_rec.db"),
    )