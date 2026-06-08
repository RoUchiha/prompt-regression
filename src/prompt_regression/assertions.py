"""All assertion type implementations."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import anthropic

from .models import AssertionDef, AssertionResult


def _ok(assertion_type: str, actual: Any, expected: Any, message: str = "") -> AssertionResult:
    return AssertionResult(assertion_type=assertion_type, passed=True, actual=actual, expected=expected, message=message or "PASS")


def _fail(assertion_type: str, actual: Any, expected: Any, message: str) -> AssertionResult:
    return AssertionResult(assertion_type=assertion_type, passed=False, actual=actual, expected=expected, message=message)


def check_max_length(output: str, assertion: AssertionDef) -> AssertionResult:
    length = len(output)
    if length <= assertion.value:
        return _ok("max_length", length, assertion.value)
    return _fail("max_length", length, assertion.value, f"Output length {length} exceeds max {assertion.value}")


def check_min_length(output: str, assertion: AssertionDef) -> AssertionResult:
    length = len(output)
    if length >= assertion.value:
        return _ok("min_length", length, assertion.value)
    return _fail("min_length", length, assertion.value, f"Output length {length} below min {assertion.value}")


def check_contains(output: str, assertion: AssertionDef) -> AssertionResult:
    haystack = output.lower() if assertion.case_insensitive else output
    needle = str(assertion.value).lower() if assertion.case_insensitive else str(assertion.value)
    if needle in haystack:
        return _ok("contains", output[:50], assertion.value)
    return _fail("contains", output[:50], assertion.value, f"Output does not contain '{assertion.value}'")


def check_not_contains(output: str, assertion: AssertionDef) -> AssertionResult:
    haystack = output.lower() if assertion.case_insensitive else output
    needle = str(assertion.value).lower() if assertion.case_insensitive else str(assertion.value)
    if needle not in haystack:
        return _ok("not_contains", output[:50], assertion.value)
    return _fail("not_contains", output[:50], assertion.value, f"Output should NOT contain '{assertion.value}'")


def check_regex(output: str, assertion: AssertionDef) -> AssertionResult:
    flags = re.IGNORECASE if assertion.case_insensitive else 0
    pattern = assertion.pattern or str(assertion.value)
    match = re.search(pattern, output, flags)
    if match:
        return _ok("regex", match.group(0), pattern)
    return _fail("regex", output[:50], pattern, f"Regex '{pattern}' did not match output")


def check_json_schema(output: str, assertion: AssertionDef) -> AssertionResult:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        return _fail("json_schema", output[:50], "valid JSON", f"Output is not valid JSON: {e}")
    if assertion.value:
        try:
            import jsonschema  # type: ignore
            jsonschema.validate(data, assertion.value)
        except Exception as e:
            return _fail("json_schema", str(data)[:50], assertion.value, str(e))
    return _ok("json_schema", str(data)[:50], "valid JSON")


def check_latency(latency_ms: int, assertion: AssertionDef) -> AssertionResult:
    if latency_ms <= assertion.value:
        return _ok("latency_ms", latency_ms, assertion.value)
    return _fail("latency_ms", latency_ms, assertion.value, f"Latency {latency_ms}ms exceeds max {assertion.value}ms")


def check_llm_judge(output: str, assertion: AssertionDef) -> AssertionResult:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rubric = assertion.rubric or "Is this a good response?"
    threshold = assertion.threshold or 0.7

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": (
                f"Evaluate the following response against this rubric:\n"
                f"Rubric: {rubric}\n\n"
                f"Response:\n{output}\n\n"
                f"Respond ONLY with JSON: {{\"score\": <float 0.0-1.0>, \"reasoning\": \"<one sentence>\"}}"
            ),
        }],
    )
    data = json.loads(message.content[0].text.strip())
    score = float(data["score"])
    if score >= threshold:
        return _ok("llm_judge", score, threshold, data["reasoning"])
    return _fail("llm_judge", score, threshold, f"LLM judge score {score:.2f} < threshold {threshold}: {data['reasoning']}")


ASSERTION_HANDLERS = {
    "max_length": check_max_length,
    "min_length": check_min_length,
    "contains": check_contains,
    "not_contains": check_not_contains,
    "regex": check_regex,
    "json_schema": check_json_schema,
    "llm_judge": check_llm_judge,
}


def run_assertion(output: str, assertion: AssertionDef, latency_ms: int = 0) -> AssertionResult:
    if assertion.type == "latency_ms":
        return check_latency(latency_ms, assertion)
    handler = ASSERTION_HANDLERS.get(assertion.type)
    if not handler:
        return _fail(assertion.type, None, None, f"Unknown assertion type: {assertion.type}")
    return handler(output, assertion)
