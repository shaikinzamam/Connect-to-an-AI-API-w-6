"""Run the eight labeled cases against a running API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

CASES_PATH = Path(__file__).with_name("cases.json")
API_URL = os.getenv("TRIAGE_API_URL", "http://127.0.0.1:8000/triage")


def load_cases() -> list[dict[str, str]]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) != 8:
        raise ValueError("evals/cases.json must contain exactly 8 cases")
    return cases


def main() -> None:
    cases = load_cases()
    passed = 0

    with httpx.Client(timeout=35.0) as client:
        for index, case in enumerate(cases, start=1):
            expected = case["expected_category"]
            try:
                response = client.post(API_URL, json={"text": case["text"]})
                response.raise_for_status()
                actual = response.json().get("category")
                is_pass = actual == expected
                detail = f"expected={expected}, actual={actual}"
            except (httpx.HTTPError, ValueError) as exc:
                is_pass = False
                detail = f"request failed: {exc}"

            if is_pass:
                passed += 1
            print(f"Case {index}: {'PASS' if is_pass else 'FAIL'} ({detail})")

    accuracy = (passed / len(cases)) * 100
    print(f"\nScore: {passed}/{len(cases)}")
    print(f"Accuracy: {accuracy:.1f}%")


if __name__ == "__main__":
    main()
