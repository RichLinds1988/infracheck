import os
import sys
from enum import Enum

import typer

from infracheck.analyzers.engine import run
from infracheck.output.formatter import print_json, print_report
from infracheck.parsers.terraform import parse_directory

VALID_CATEGORIES = {"fault_tolerance", "scalability", "security", "observability"}


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


def analyze(
    path: str = typer.Argument(
        default=None,
        help="Path to the directory containing Terraform files.",
    ),
    explain: str = typer.Option(
        None,
        "--explain",
        help=(
            "Use Claude to explain failing checks. "
            "Optionally filter to one category "
            "(fault_tolerance, scalability, security, observability). "
            "Omit a value to explain all failures."
        ),
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.text,
        "--output",
        "-o",
        help="Output format: text (default) or json.",
    ),
) -> None:
    """Analyze a Terraform directory and score it across four categories."""
    # Resolve path: CLI argument → INFRACHECK_PATH env var → ./infra
    resolved_path = path or os.getenv("INFRACHECK_PATH", "./infra")

    if not os.path.isdir(resolved_path):
        typer.echo(
            typer.style(f"Error: '{resolved_path}' is not a directory.", fg="red"),
            err=True,
        )
        raise typer.Exit(code=1)

    json_mode = output == OutputFormat.json

    typer.echo(f"Analyzing {resolved_path}...", err=json_mode)

    resources = parse_directory(resolved_path)

    if not resources:
        typer.echo(
            typer.style("No Terraform resources found.", fg="yellow"),
            err=True,
        )
        raise typer.Exit(code=1)

    report = run(path=resolved_path, resources=resources)

    if explain is not None:
        if explain not in VALID_CATEGORIES and explain != "":
            typer.echo(
                typer.style(
                    f"Error: unknown category '{explain}'. "
                    f"Valid options: {', '.join(sorted(VALID_CATEGORIES))}",
                    fg="red",
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        if not os.getenv("ANTHROPIC_API_KEY"):
            typer.echo(
                typer.style(
                    "Error: ANTHROPIC_API_KEY is not set. Export it to use --explain.",
                    fg="red",
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        categories = {explain} if explain else None
        typer.echo("Generating explanations...", err=json_mode)
        from infracheck.explainer import explain_findings

        report = explain_findings(report, categories=categories)

    if json_mode:
        print_json(report)
    else:
        print_report(report)

    # Exit with a non-zero code if the overall score is below 5
    if report.overall_score < 5:
        sys.exit(2)


def main() -> None:
    typer.run(analyze)
