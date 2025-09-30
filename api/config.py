"""Application configuration utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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

    @property
    def require_openai_key(self) -> bool:
        return any(
            provider == "openai"
            for provider in (self.stt_provider.lower(), self.llm_provider.lower())
        )


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
    )
    return settings


settings = get_settings()
