"""Prompt loading and support-message classification service."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.llm.client import LLMConfig, create_client
from src.llm.logger import log_llm_call, quarantine_output
from src.llm.parser import ModelOutputError, parse_and_validate
from src.llm.retry import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMTimeoutError,
    call_with_retries,
)
from src.llm.schema import TriageResponse
from src.llm.service_types import InvalidModelOutputError, PROMPT_VERSION

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / f"{PROMPT_VERSION}.md"


def load_system_prompt() -> str:
    """Load the versioned prompt from disk instead of embedding it in route code."""

    return PROMPT_PATH.read_text(encoding="utf-8")


@dataclass(frozen=True)
class ModelCallResult:
    raw_output: str
    input_tokens: int | None
    output_tokens: int | None


def _token_count(usage: object | None, name: str) -> int | None:
    value = getattr(usage, name, None)
    return value if isinstance(value, int) else None


def _call_model(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    repair_count: int,
) -> ModelCallResult:
    """Make one logical call, including bounded transient transport retries."""

    started = time.perf_counter()
    try:
        completion = call_with_retries(
            lambda: client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=messages,
            )
        )
    except LLMTimeoutError:
        status = "timeout"
        raise
    except LLMAuthenticationError:
        status = "authentication_error"
        raise
    except LLMProviderError:
        status = "provider_error"
        raise
    else:
        status = "success"
    finally:
        if "status" in locals() and status != "success":
            log_llm_call(
                model=model,
                input_tokens=None,
                output_tokens=None,
                duration_ms=round((time.perf_counter() - started) * 1000),
                repair_count=repair_count,
                status=status,
            )

    usage = getattr(completion, "usage", None)
    choices = getattr(completion, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    result = ModelCallResult(
        raw_output=content if isinstance(content, str) else "",
        input_tokens=_token_count(usage, "prompt_tokens"),
        output_tokens=_token_count(usage, "completion_tokens"),
    )
    log_llm_call(
        model=model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        duration_ms=round((time.perf_counter() - started) * 1000),
        repair_count=repair_count,
        status=status,
    )
    return result


def _repair_message(text: str, raw_output: str, error: str) -> str:
    """Keep repair data in a user message and JSON-encode the original input."""

    return (
        "Your previous answer was rejected for the following reason.\n"
        f"{error}\n\n"
        "Return only corrected JSON matching the required schema. Do not use Markdown.\n\n"
        f"Original customer message: {json.dumps(text, ensure_ascii=False)}\n\n"
        f"Invalid output:\n{raw_output}"
    )


def classify_message(text: str) -> TriageResponse:
    """Call, validate, repair exactly once if needed, then quarantine failure."""

    config = LLMConfig.from_environment()
    client = create_client(config)
    system_prompt = load_system_prompt()
    first_call = _call_model(
        client,
        model=config.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        repair_count=0,
    )
    try:
        return parse_and_validate(first_call.raw_output)
    except ModelOutputError as first_error:
        repair_call = _call_model(
            client,
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _repair_message(
                        text, first_call.raw_output, str(first_error)
                    ),
                },
            ],
            repair_count=1,
        )
        try:
            return parse_and_validate(repair_call.raw_output)
        except ModelOutputError as second_error:
            quarantine_output(
                text=text,
                raw_output=repair_call.raw_output,
                error=str(second_error),
            )
            raise InvalidModelOutputError from second_error
