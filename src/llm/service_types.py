"""Shared constants and exceptions without import cycles."""

PROMPT_VERSION = "triage-v1"


class InvalidModelOutputError(Exception):
    """The initial and repaired outputs both failed validation."""
