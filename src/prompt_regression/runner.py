"""Test runner — renders templates, calls LLM, runs assertions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

import anthropic

from .assertions import run_assertion
from .models import TestCase, TestResult, TestSuiteResult
from .renderer import render_template


class PromptTestRunner:
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def _call_llm(self, prompt: str) -> tuple[str, int]:
        start = time.monotonic()
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        return message.content[0].text, latency_ms

    def run_test(self, test_case: TestCase) -> TestResult:
        prompt = render_template(test_case.prompt_template, test_case.inputs)
        output, latency_ms = self._call_llm(prompt)

        assertion_results = [
            run_assertion(output, a, latency_ms) for a in test_case.assertions
        ]
        passed = all(r.passed for r in assertion_results)

        return TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            passed=passed,
            output=output,
            latency_ms=latency_ms,
            assertion_results=assertion_results,
        )

    def run_suite(self, test_cases: List[TestCase]) -> TestSuiteResult:
        results = [self.run_test(tc) for tc in test_cases]
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            results=results,
        )
