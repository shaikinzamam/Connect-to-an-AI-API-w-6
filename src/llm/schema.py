"""Validated request and response shapes for triage."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Category(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text", mode="before")
    @classmethod
    def reject_blank_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must contain at least one non-whitespace character")
        return value


class TriageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def require_one_short_sentence(cls, value: str) -> str:
        cleaned = value.strip()
        if "\n" in cleaned or "\r" in cleaned:
            raise ValueError("must be one sentence on one line")
        if re.search(r"[.!?]\s+\S", cleaned):
            raise ValueError("must contain only one sentence")
        return cleaned

    @model_validator(mode="after")
    def enforce_unsure_rule(self) -> "TriageResponse":
        if self.confidence < 0.5 and self.category is not Category.OTHER:
            raise ValueError('confidence below 0.5 requires category "other"')
        return self
