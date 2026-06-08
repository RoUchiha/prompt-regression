"""Pydantic models for prompt regression testing."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel


class AssertionDef(BaseModel):
    type: Literal["max_length", "min_length", "contains", "not_contains", "regex", "json_schema", "llm_judge", "latency_ms"]
    value: Optional[Any] = None
    pattern: Optional[str] = None
    rubric: Optional[str] = None
    threshold: Optional[float] = None
    case_insensitive: bool = False


class TestCase(BaseModel):
    id: str
    name: str
    prompt_template: str
    inputs: Dict[str, Any] = {}
    assertions: List[AssertionDef]


class AssertionResult(BaseModel):
    assertion_type: str
    passed: bool
    actual: Any
    expected: Any
    message: str


class TestResult(BaseModel):
    test_id: str
    test_name: str
    passed: bool
    output: str
    latency_ms: int
    assertion_results: List[AssertionResult]


class TestSuiteResult(BaseModel):
    total: int
    passed: int
    failed: int
    results: List[TestResult]

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0
