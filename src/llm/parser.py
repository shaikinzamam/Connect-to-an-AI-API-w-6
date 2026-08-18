"""Safe extraction and validation of untrusted model output."""

from __future__ import annotations

import json

from pydantic import ValidationError

from src.llm.schema import TriageResponse


class ModelOutputError(ValueError):
    """Raised when model output cannot satisfy the response contract."""


def _extract_first_json_object(raw_output: str) -> dict[str, object]:
    """Find the first decodable JSON object, tolerating fences or surrounding text."""

    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw_output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ModelOutputError("No valid JSON object was found in the model output")


def parse_and_validate(raw_output: str) -> TriageResponse:
    """Extract JSON and validate every field against the closed output schema."""

    if not isinstance(raw_output, str) or not raw_output.strip():
        raise ModelOutputError("The model output was empty")
    try:
        payload = _extract_first_json_object(raw_output)
        return TriageResponse.model_validate(payload)
    except ModelOutputError:
        raise
    except ValidationError as exc:
        raise ModelOutputError(f"Output schema validation failed: {exc}") from exc
