"""HTTP route for support-message triage."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from src.llm.schema import TriageRequest, TriageResponse
from src.llm.retry import LLMAuthenticationError, LLMProviderError, LLMTimeoutError
from src.llm.service import classify_message
from src.llm.service_types import InvalidModelOutputError

router = APIRouter()


def _is_true(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@router.post("/triage", response_model=TriageResponse)
def triage_message(request: TriageRequest) -> TriageResponse:
    """Classify one support message into the closed triage schema."""

    if not _is_true("LLM_ENABLED", default="true"):
        raise HTTPException(status_code=503, detail="LLM feature is currently disabled.")

    if _is_true("LLM_STUB"):
        return TriageResponse(
            category="other",
            urgency="normal",
            confidence=0.5,
            reason="Stub mode is enabled.",
        )

    try:
        return classify_message(request.text)
    except InvalidModelOutputError as exc:
        raise HTTPException(
            status_code=422,
            detail="The model could not produce a valid triage response.",
        ) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail="The LLM provider timed out.") from exc
    except LLMAuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM provider authentication failed.",
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail="The LLM provider could not complete the request.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="LLM configuration is unavailable.") from exc
