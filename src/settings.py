from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: SecretStr
    google_embedding_model: str = "models/gemini-embedding-001"
    google_llm_model: str = "gemini-3.5-flash-lite"
    database_url: str
    pg_vector_collection_name: str
    pdf_path: str = "document.pdf"


@lru_cache
def get_settings() -> Settings:
    return Settings()
