from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Northeast Sentinel AI"

    # News collection window
    START_DATE: str = "2026-09-01"
    END_DATE: str = "2026-10-05"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'northeast_sentinel.db'}"

    # Chroma
    CHROMA_PATH: str = str(BASE_DIR / "chroma_db")

    # Data directories
    RAW_DATA_DIR: str = str(BASE_DIR / "data" / "raw")
    PROCESSED_DATA_DIR: str = str(BASE_DIR / "data" / "processed")
    IMAGE_DIR: str = str(BASE_DIR / "data" / "images")
    CHART_DIR: str = str(BASE_DIR / "data" / "charts")
    OUTPUT_DIR: str = str(BASE_DIR / "data" / "output")

    # LLM
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()