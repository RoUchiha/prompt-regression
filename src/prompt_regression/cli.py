"""CLI entrypoint for prompt regression testing."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import sys

import typer
from rich.console import Console

app = typer.Typer(help="Prompt regression testing for LLM applications.")
console = Console()


@app.command()
def run(
    tests_dir: Path = typer.Option(Path("tests/prompts"), help="Directory containing YAML test cases."),
    model: str = typer.Option("claude-haiku-4-5-20251001", help="LLM model to test."),
    report: Optional[Path] = typer.Option(None, help="Save JUnit XML report to this path."),
    baseline_path: Path = typer.Option(Path("baseline.json"), help="Path to baseline JSON file."),
    update_baseline: bool = typer.Option(False, "--update-baseline", help="Save current outputs as new baseline."),
) -> None:
    """Discover and run all YAML prompt test cases."""
    from .loader import discover_test_cases
    from .runner import PromptTestRunner
    from .reporter import render_console, save_junit_xml
    from .baseline import diff_baseline, load_baseline, save_baseline

    test_cases = discover_test_cases(tests_dir)
    if not test_cases:
        console.print(f"[yellow]No test cases found in {tests_dir}[/yellow]")
        raise typer.Exit(0)

    console.print(f"[cyan]Discovered {len(test_cases)} test cases.[/cyan]")

    runner = PromptTestRunner(model=model)
    suite = runner.run_suite(test_cases)

    render_console(suite)

    baseline = load_baseline(baseline_path)
    if baseline:
        drifted = diff_baseline(suite.results, baseline)
        if drifted:
            console.print(f"\n[yellow]Baseline drift detected in {len(drifted)} test(s):[/yellow]")
            for d in drifted:
                console.print(f"  {d['test_id']}: similarity={d.get('similarity', 'N/A')}")

    if update_baseline:
        save_baseline(suite.results, baseline_path)
        console.print(f"[green]Baseline updated → {baseline_path}[/green]")
    elif not baseline_path.exists():
        save_baseline(suite.results, baseline_path)
        console.print(f"[dim]First run — baseline saved → {baseline_path}[/dim]")

    if report:
        save_junit_xml(suite, report)

    if suite.failed > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
