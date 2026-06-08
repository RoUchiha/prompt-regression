"""YAML test case loader."""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from .models import AssertionDef, TestCase


def load_test_case(path: Path) -> TestCase:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assertions = [AssertionDef(**a) for a in raw.get("assertions", [])]
    return TestCase(
        id=raw["id"],
        name=raw["name"],
        prompt_template=raw["prompt_template"],
        inputs=raw.get("inputs", {}),
        assertions=assertions,
    )


def discover_test_cases(directory: Path) -> List[TestCase]:
    cases = []
    for yaml_file in sorted(directory.rglob("*.yaml")):
        cases.append(load_test_case(yaml_file))
    return cases
