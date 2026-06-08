"""Unit tests for all 7 assertion types."""

from unittest.mock import MagicMock, patch

import pytest

from prompt_regression.assertions import run_assertion
from prompt_regression.models import AssertionDef


def test_max_length_pass():
    a = AssertionDef(type="max_length", value=100)
    r = run_assertion("Hello world", a)
    assert r.passed


def test_max_length_fail():
    a = AssertionDef(type="max_length", value=5)
    r = run_assertion("Hello world", a)
    assert not r.passed
    assert "exceeds" in r.message


def test_min_length_pass():
    a = AssertionDef(type="min_length", value=5)
    r = run_assertion("Hello world", a)
    assert r.passed


def test_min_length_fail():
    a = AssertionDef(type="min_length", value=100)
    r = run_assertion("Hi", a)
    assert not r.passed


def test_contains_pass():
    a = AssertionDef(type="contains", value="world")
    r = run_assertion("Hello world", a)
    assert r.passed


def test_contains_case_insensitive():
    a = AssertionDef(type="contains", value="WORLD", case_insensitive=True)
    r = run_assertion("Hello world", a)
    assert r.passed


def test_contains_fail():
    a = AssertionDef(type="contains", value="banana")
    r = run_assertion("Hello world", a)
    assert not r.passed


def test_not_contains_pass():
    a = AssertionDef(type="not_contains", value="banana")
    r = run_assertion("Hello world", a)
    assert r.passed


def test_not_contains_fail():
    a = AssertionDef(type="not_contains", value="Hello")
    r = run_assertion("Hello world", a)
    assert not r.passed


def test_regex_pass():
    a = AssertionDef(type="regex", pattern=r"^[A-Z]")
    r = run_assertion("Hello world", a)
    assert r.passed


def test_regex_fail():
    a = AssertionDef(type="regex", pattern=r"^\d")
    r = run_assertion("Hello world", a)
    assert not r.passed


def test_json_schema_valid_json():
    a = AssertionDef(type="json_schema")
    r = run_assertion('{"key": "value"}', a)
    assert r.passed


def test_json_schema_invalid_json():
    a = AssertionDef(type="json_schema")
    r = run_assertion("not json", a)
    assert not r.passed


def test_latency_pass():
    a = AssertionDef(type="latency_ms", value=1000)
    r = run_assertion("output", a, latency_ms=500)
    assert r.passed


def test_latency_fail():
    a = AssertionDef(type="latency_ms", value=100)
    r = run_assertion("output", a, latency_ms=500)
    assert not r.passed


@patch("prompt_regression.assertions.anthropic.Anthropic")
def test_llm_judge_pass(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"score": 0.9, "reasoning": "Excellent response."}')]
    mock_client.messages.create.return_value = mock_msg

    a = AssertionDef(type="llm_judge", rubric="Is this helpful?", threshold=0.7)
    r = run_assertion("A very helpful response.", a)
    assert r.passed


@patch("prompt_regression.assertions.anthropic.Anthropic")
def test_llm_judge_fail(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"score": 0.3, "reasoning": "Poor response."}')]
    mock_client.messages.create.return_value = mock_msg

    a = AssertionDef(type="llm_judge", rubric="Is this helpful?", threshold=0.7)
    r = run_assertion("A bad response.", a)
    assert not r.passed
