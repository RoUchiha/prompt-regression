# Prompt Regression Testing

> A CI/CD-integrated prompt regression testing framework. Define test cases in YAML, run 7 types of assertions against LLM outputs, gate merges when prompts regress, and track output drift over time — all without writing a single line of test logic.

---

## Academic Background

This project was built as a capstone application of concepts from the **[UT Austin AI & Machine Learning](https://onlineexeced.mccombs.utexas.edu/online-ai-machine-learning-course)** program (McCombs School of Business, 23-week executive program).

Specific modules applied:

| Module | Concept Applied |
|--------|----------------|
| **Course 03 — Generative AI for NLP** | Prompt engineering — the course teaches how to write effective prompts, but not how to *maintain* them. This project fills that gap with a regression testing framework for prompts |
| **Course 03 — Generative AI for NLP** | Responsible AI implementation — systematically verifying that prompts behave as expected is a core responsible AI practice |
| **Course 05 — Deploying AI Solutions** | CI/CD integration — the GitHub Actions workflow applies the deployment skills from Course 05 to automate quality gates on every code push |
| **Course 05 — Deploying AI Solutions** | Integrating LLM calls into production workflows, with structured output validation and latency tracking |
| **Tools: OpenAI / Anthropic APIs** | The LLM runner and `llm_judge` assertion type use the API patterns taught throughout the program |

The course teaches you to build AI solutions — this project solves the **production reliability problem** that comes after: when you change a prompt, how do you know you haven't broken anything? Prompt regression testing is how mature AI teams answer that question, and it directly applies the deployment discipline from Course 05.

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
