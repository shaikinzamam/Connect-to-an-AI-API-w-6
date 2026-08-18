"""Structured logging helpers for the LLM integration."""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.llm.service_types import PROMPT_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUARANTINE_PATH = PROJECT_ROOT / "logs" / "quarantine.jsonl"
_QUARANTINE_LOCK = threading.Lock()


def log_llm_call(
    *,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: int,
    repair_count: int,
    status: str,
) -> None:
    """Write one machine-readable observability event to stdout."""

    event = {
        "event": "llm_call",
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repair_count": repair_count,
        "status": status,
    }
    print(json.dumps(event, ensure_ascii=False), file=sys.stdout, flush=True)


def quarantine_output(*, text: str, raw_output: str, error: str) -> None:
    """Append invalid output as one JSON line without exposing it to the caller."""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": text,
        "raw_output": raw_output,
        "error": error,
        "prompt_version": PROMPT_VERSION,
    }
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _QUARANTINE_LOCK:
        with QUARANTINE_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
