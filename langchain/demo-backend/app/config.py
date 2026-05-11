"""Configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    openrouter_api_key: str
    tinyfish_api_key: str
    openrouter_model: str = "openai/gpt-4o"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": str(_ENV_FILE)}
