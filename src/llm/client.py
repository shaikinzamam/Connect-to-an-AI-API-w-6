"""OpenAI-compatible provider client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

MAX_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class LLMConfig:
    """Provider settings loaded from environment variables."""

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = MAX_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls) -> "LLMConfig":
        load_dotenv()
        missing = [
            name
            for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
            if not os.getenv(name)
        ]
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required LLM configuration: {names}")

        requested_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", MAX_TIMEOUT_SECONDS))
        timeout_seconds = min(max(requested_timeout, 0.1), MAX_TIMEOUT_SECONDS)
        return cls(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            model=os.environ["LLM_MODEL"],
            timeout_seconds=timeout_seconds,
        )


def create_client(config: LLMConfig) -> OpenAI:
    """Create a client with an explicit timeout and no SDK-level retries."""

    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout_seconds,
        max_retries=0,
    )
