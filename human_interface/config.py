from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    openai_model: str
    openai_base_url: str | None
    money_service_base_url: str


def load_config() -> Config:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigError("OPENAI_API_KEY is not set (see .env.example)")
    return Config(
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        money_service_base_url=os.getenv("MONEY_SERVICE_BASE_URL", "http://127.0.0.1:5000"),
    )
