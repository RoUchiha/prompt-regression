"""Console and JUnit XML report generation."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from rich.console import Console
from rich.table import Table
from rich import box

from .models import TestSuiteResult

console = Console()


def render_console(suite: TestSuiteResult) -> None:
    color = "green" if suite.failed == 0 else "red"
    console.print(
        f"\n[bold]Prompt Regression Suite[/bold]  "
        f"[{color}]{suite.passed}/{suite.total} passed[/{color}]  "
        f"({suite.pass_rate:.0%})\n"
    )

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Latency", justify="right")
    table.add_column("Result", justify="center")
    table.add_column("Failures")

    for r in suite.results:
        failures = "; ".join(
            ar.message for ar in r.assertion_results if not ar.passed
        )
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(r.test_id, r.test_name[:40], f"{r.latency_ms}ms", status, failures[:60])

    console.print(table)


def save_junit_xml(suite: TestSuiteResult, path: Path) -> None:
    root = ET.Element("testsuites")
    ts = ET.SubElement(root, "testsuite", name="prompt-regression",
                       tests=str(suite.total), failures=str(suite.failed))
    for r in suite.results:
        tc = ET.SubElement(ts, "testcase", name=r.test_name, classname=r.test_id,
                           time=str(r.latency_ms / 1000))
        if not r.passed:
            for ar in r.assertion_results:
                if not ar.passed:
                    f = ET.SubElement(tc, "failure", message=ar.message, type=ar.assertion_type)
                    f.text = ar.message
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="unicode", xml_declaration=True)
    console.print(f"[dim]JUnit XML saved → {path}[/dim]")
