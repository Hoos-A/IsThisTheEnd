"""Application configuration utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: Optional[str]
    openai_api_base: Optional[str]
    openai_model_stt: str
    openai_model_llm: str
    stt_provider: str
    llm_provider: str
    data_dir: Path
    ssl_certfile: Optional[Path]
    ssl_keyfile: Optional[Path]
    ssl_ca_bundle: Optional[Path]

    @property
    def require_openai_key(self) -> bool:
        return any(
            provider == "openai"
            for provider in (self.stt_provider.lower(), self.llm_provider.lower())
        )


def _optional_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    return Path(value).expanduser().resolve()


def get_settings() -> Settings:
    data_dir = Path(os.getenv("DATA_DIR", "../data")).resolve()
    settings = Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE"),
        openai_model_stt=os.getenv("OPENAI_MODEL_STT", "whisper-1"),
        openai_model_llm=os.getenv("OPENAI_MODEL_LLM", "gpt-4o-mini"),
        stt_provider=os.getenv("STT_PROVIDER", "openai"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        data_dir=data_dir,
        ssl_certfile=_optional_path(os.getenv("API_SSL_CERT")),
        ssl_keyfile=_optional_path(os.getenv("API_SSL_KEY")),
        ssl_ca_bundle=_optional_path(os.getenv("API_SSL_CA_BUNDLE")),
    )
    return settings


settings = get_settings()
