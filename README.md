# Prompt Regression Testing

> A CI/CD-integrated prompt regression testing framework. Define test cases in YAML, run 7 types of assertions against LLM outputs, gate merges when prompts regress, and track output drift over time — all without writing a single line of test logic.

---

## What Is This?

When you change a prompt in production — even slightly — you can break behaviors you rely on. Maybe your summarization prompt used to return concise 2-sentence summaries, but after tweaking the instructions for a new use case, it now returns 10-paragraph essays. Maybe your classification prompt used to output valid JSON, but now outputs prose with the answer buried inside.

Software engineering solved this problem decades ago with **regression tests**: automated checks that catch when a change breaks existing behavior. This project brings that discipline to LLM prompts.

You define test cases in YAML:
- What inputs to send
- What the output must satisfy (length, content, format, latency, semantic quality)

The framework runs every test on every commit, **exits with code 1 if any test fails** (blocking the merge), saves a baseline of LLM outputs, and flags **semantic drift** when outputs change significantly between runs.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  Prompt Regression Pipeline                       │
│                                                                    │
│   tests/prompts/*.yaml ──► [YAML Loader] ──► List[TestCase]      │
│                                                      │             │
│                                                      ▼             │
│                                          [Jinja2 Renderer]        │
│                                         render template + inputs   │
│                                                      │             │
│                                                      ▼             │
│                                             [LLM Runner]           │
│                                           call model, time it      │
│                                                      │             │
│                                                      ▼             │
│                                        [Assertion Engine]          │
│                              ┌─────────────────────────────┐      │
│                              │  max_length / min_length    │      │
│                              │  contains / not_contains    │      │
│                              │  regex                      │      │
│                              │  json_schema                │      │
│                              │  llm_judge                  │      │
│                              │  latency_ms                 │      │
│                              └─────────────────────────────┘      │
│                                              │                     │
│                                              ▼                     │
│                        [Reporter] ──► console (rich) + JUnit XML  │
│                        [Baseline]  ──► save / diff / drift alert   │
│                                                                    │
│                        Exit 0 (all pass) / Exit 1 (any fail)      │
└──────────────────────────────────────────────────────────────────┘
```

### The 7 Assertion Types

| Type | What It Checks | Example |
|------|---------------|---------|
| `max_length` | Output ≤ N characters | Enforce conciseness |
| `min_length` | Output ≥ N characters | Ensure substantive response |
| `contains` | Substring present | Key term appears in response |
| `not_contains` | Substring absent | Model doesn't refuse with "I cannot" |
| `regex` | Pattern matches | Starts with capital, contains URL, etc. |
| `json_schema` | Output is valid JSON | Structured output tasks |
| `llm_judge` | LLM rates quality ≥ threshold | Semantic quality without hand-coding |
| `latency_ms` | Response time ≤ N ms | SLA enforcement |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM under test | Claude (configurable) via Anthropic SDK |
| LLM judge | Claude Haiku |
| Template rendering | Jinja2 |
| Test case format | YAML + Pydantic v2 |
| CLI | typer |
| Console output | rich |
| CI/CD | GitHub Actions |
| Test reporting | JUnit XML |
| Tests | pytest |

---

## Getting Started in 5 Minutes

### 1. Install

```bash
git clone https://github.com/RoUchiha/prompt-regression.git
cd prompt-regression
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Write a test case

Create `tests/prompts/my_test.yaml`:
```yaml
id: tc-my-001
name: "My summarization test"
prompt_template: "Summarize in one sentence: {{ text }}"
inputs:
  text: "Claude is an AI assistant made by Anthropic..."
assertions:
  - type: max_length
    value: 200
  - type: not_contains
    value: "I cannot"
    case_insensitive: true
  - type: regex
    pattern: "^[A-Z]"
```

### 3. Run

```bash
python -m prompt_regression run
```

**Output:**
```
Discovered 2 test cases.

Prompt Regression Suite  2/2 passed  (100%)

╭────────┬──────────────────────────────┬─────────┬────────┬──────────╮
│ ID     │ Name                         │ Latency │ Result │ Failures │
├────────┼──────────────────────────────┼─────────┼────────┼──────────┤
│ tc-001 │ Summarization — conciseness  │ 892ms   │  PASS  │          │
│ tc-002 │ Sentiment classification     │ 743ms   │  PASS  │          │
╰────────┴──────────────────────────────┴─────────┴────────┴──────────╯
First run — baseline saved → baseline.json
```

### 4. See a failure

Change the model, update a prompt, or deliberately break an assertion — re-run and see:
```
Prompt Regression Suite  1/2 passed  (50%)
  tc-002: Output length 847 exceeds max 200
Exit code: 1  ← blocks CI merge
```

---

## CI/CD Setup

The included GitHub Actions workflow (`.github/workflows/prompt-regression.yml`) runs tests on every push and PR, uploads a JUnit XML report as an artifact, and **fails the check if any prompt test fails** — blocking merges until the regression is fixed or the baseline is explicitly updated.

Add your API key as a repository secret:
```
GitHub repo → Settings → Secrets → Actions → New: ANTHROPIC_API_KEY
```

---

## Baseline Drift Detection

On first run, outputs are saved to `baseline.json`. On subsequent runs, current outputs are compared to the baseline using semantic similarity. If a test's output drifts significantly:

```
Baseline drift detected in 1 test(s):
  tc-001: similarity=0.42
```

To accept the new outputs as the new baseline:
```bash
python -m prompt_regression run --update-baseline
```

---

## Running Tests

```bash
pytest --cov=src/prompt_regression
```

All 7 assertion types are unit-tested with mocked LLM calls — no API key required for CI.

---

## Project Structure

```
prompt-regression/
├── src/prompt_regression/
│   ├── cli.py          # typer entrypoint
│   ├── loader.py       # YAML test case discovery
│   ├── renderer.py     # Jinja2 template rendering
│   ├── runner.py       # LLM call + assertion execution
│   ├── assertions.py   # all 7 assertion types
│   ├── baseline.py     # save/load/diff baseline
│   ├── reporter.py     # rich console + JUnit XML
│   └── models.py       # Pydantic data models
├── tests/
│   ├── prompts/        # YAML test cases (run against real model)
│   │   ├── summarize.yaml
│   │   └── classify.yaml
│   └── test_assertions.py  # unit tests (mocked)
├── .github/workflows/
│   └── prompt-regression.yml
└── pyproject.toml
```

---

## Extending This

- **Add `--model-a` vs `--model-b`**: run the same test suite against two models and compare pass rates side-by-side
- **Add `promptfoo` integration**: export test results in promptfoo format for visual diff in their dashboard
- **Add embedding-based drift detection**: replace Jaccard similarity in `baseline.py` with OpenAI/Cohere embeddings + cosine similarity for semantic drift detection
