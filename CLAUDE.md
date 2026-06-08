# CLAUDE.md — Prompt Regression Testing

This file gives Claude Code full context for this project. Read it before making any changes.

---

## What This Project Does

A CI/CD-integrated prompt regression testing framework. Test cases are defined in YAML files under `tests/prompts/`. Each test case specifies a prompt template (Jinja2), input variables, and a list of assertions. The runner renders the template, calls the LLM, evaluates all assertions, and exits with code 1 if any fail — blocking CI merges on prompt regressions.

On first run, LLM outputs are saved to `baseline.json`. On subsequent runs, current outputs are diffed against the baseline and semantic drift is reported.

---

## Repository Layout

```
prompt-regression/
├── src/prompt_regression/
│   ├── models.py        # Pydantic: AssertionDef, TestCase, AssertionResult, TestResult, TestSuiteResult
│   ├── loader.py        # YAML test case discovery (rglob *.yaml in tests/prompts/)
│   ├── renderer.py      # Jinja2 template rendering (string + file modes)
│   ├── assertions.py    # All 7 assertion handlers + run_assertion() dispatcher
│   ├── runner.py        # PromptTestRunner: render → LLM call → run assertions
│   ├── baseline.py      # save_baseline(), load_baseline(), diff_baseline()
│   ├── reporter.py      # rich console table + JUnit XML (for GitHub Actions)
│   ├── cli.py           # typer: `run` subcommand with --update-baseline flag
│   └── __main__.py      # python -m prompt_regression entrypoint
├── tests/
│   ├── prompts/
│   │   ├── summarize.yaml   # tc-001: max_length, min_length, not_contains, regex
│   │   └── classify.yaml    # tc-002: json_schema, contains, latency_ms
│   └── test_assertions.py   # unit tests for all 7 assertion types (mocked LLM)
├── .github/workflows/
│   └── prompt-regression.yml  # GitHub Actions: runs on push/PR, uploads JUnit XML
└── pyproject.toml
```

---

## The 7 Assertion Types

| Type | Handler | Notes |
|------|---------|-------|
| `max_length` | `check_max_length` | Character count |
| `min_length` | `check_min_length` | Character count |
| `contains` | `check_contains` | Supports `case_insensitive: true` |
| `not_contains` | `check_not_contains` | Supports `case_insensitive: true` |
| `regex` | `check_regex` | Full Python regex |
| `json_schema` | `check_json_schema` | Validates JSON; optionally validates schema if `value` provided |
| `llm_judge` | `check_llm_judge` | Calls Claude Haiku; pass if `score >= threshold` |
| `latency_ms` | `check_latency` | Checked against measured wall-clock time |

`run_assertion(output, assertion, latency_ms)` dispatches to the right handler.

---

## Tech Stack

| Component | Library |
|-----------|---------|
| LLM under test | `anthropic` SDK |
| LLM judge (assertion) | `anthropic` SDK (Claude Haiku) |
| Template rendering | `jinja2` |
| Test case format | `pyyaml` + `pydantic` v2 |
| CLI | `typer` |
| Console output | `rich` |
| CI reporting | JUnit XML (stdlib `xml.etree`) |
| Tests | `pytest`, `pytest-cov` |

---

## Environment

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

## Commands

```bash
# Run all tests
python -m prompt_regression run

# Run and save JUnit XML (for CI)
python -m prompt_regression run --report junit.xml

# Accept current outputs as new baseline
python -m prompt_regression run --update-baseline

# Unit tests only (no API key needed)
pytest tests/test_assertions.py
```

---

## Test Case YAML Schema

```yaml
id: tc-001                          # unique identifier
name: "Human-readable test name"
prompt_template: "Summarize: {{ text }}"   # Jinja2; OR path to .jinja2 file
inputs:
  text: "The article content..."
assertions:
  - type: max_length
    value: 200
  - type: contains
    value: "key term"
    case_insensitive: true
  - type: llm_judge
    rubric: "Is this a good summary?"
    threshold: 0.7
```

---

## Key Design Decisions

- **Exit code 1 on failure**: critical for CI gating — GitHub Actions fails the check and blocks merge
- **Baseline diffing**: Jaccard word-set similarity as lightweight proxy; replace with embedding cosine similarity for production
- **`llm_judge` assertion**: calls a separate LLM judge, not the model under test — avoids circular evaluation
- **JUnit XML**: standard format — works with GitHub Actions test reporter, Allure, Jenkins, etc.

---

## Course Context

Built as part of the **UT Austin AI & Machine Learning** program (McCombs, 23-week executive program).
- **Course 03** — Prompt engineering: systematic prompt design and validation
- **Course 05** — Deploying AI Solutions: CI/CD integration, production reliability

---

## Stretch Goals (not yet implemented)

- `--model-a` vs `--model-b` flag for A/B model comparison
- Embedding-based baseline drift detection (replace Jaccard with cosine similarity)
- `promptfoo` export format
