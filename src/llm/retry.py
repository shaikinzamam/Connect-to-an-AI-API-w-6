"""Bounded retry policy for OpenAI-compatible provider calls."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
from openai import APIConnectionError, APITimeoutError

T = TypeVar("T")
MAX_RETRIES = 3


class LLMTimeoutError(Exception):
    """The provider timed out after bounded retries."""


class LLMAuthenticationError(Exception):
    """The provider rejected its configured credentials."""


class LLMProviderError(Exception):
    """The provider failed or rejected the request."""


def _status_code(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _is_timeout(exc: Exception) -> bool:
    return isinstance(exc, (APITimeoutError, httpx.TimeoutException, TimeoutError))


def _is_retryable(exc: Exception) -> bool:
    status = _status_code(exc)
    return (
        _is_timeout(exc)
        or isinstance(exc, APIConnectionError)
        or status == 429
        or (status is not None and 500 <= status <= 599)
    )


def _raise_safe_error(exc: Exception) -> None:
    status = _status_code(exc)
    if _is_timeout(exc):
        raise LLMTimeoutError from exc
    if status in {401, 403}:
        raise LLMAuthenticationError from exc
    raise LLMProviderError from exc


def call_with_retries(
    operation: Callable[[], T],
    *,
    max_retries: int = MAX_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = lambda: random.uniform(0.0, 0.25),
) -> T:
    """Retry only transient failures using 1s, 2s, 4s plus small jitter."""

    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as exc:
            if not _is_retryable(exc) or attempt == max_retries:
                _raise_safe_error(exc)
            sleep((2**attempt) + jitter())
    raise AssertionError("retry loop ended unexpectedly")
