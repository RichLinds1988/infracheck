import anthropic
from pydantic import BaseModel

from infracheck.models import Report, RuleResult


class FindingExplanation(BaseModel):
    rule_id: str
    resource: str | None
    explanation: str


class ExplanationResponse(BaseModel):
    explanations: list[FindingExplanation]


def _build_prompt(findings: list[RuleResult]) -> str:
    lines = []
    for finding in findings:
        resource_tag = f" on resource '{finding.resource}'" if finding.resource else ""
        lines.append(f"- [{finding.severity}] {finding.rule_id}{resource_tag}: {finding.message}")

    findings_text = "\n".join(lines)

    return (
        "You are an AWS infrastructure expert reviewing Terraform configurations.\n"
        "For each failing check below, provide a concise 1-2 sentence remediation: "
        "the specific Terraform change the user needs to make to fix it.\n\n"
        "Focus only on the fix - do not re-explain the problem, it is already shown to the user.\n"
        "Be specific (include attribute names, recommended values where applicable).\n"
        "Use only plain ASCII characters in your response.\n\n"
        f"Failing checks:\n{findings_text}"
    )


def explain_findings(report: Report, categories: set[str] | None = None) -> Report:
    """Call Claude to add plain-language explanations to failed findings in a report.

    Returns a new Report with ai_explanation populated on each failed RuleResult.
    Requires ANTHROPIC_API_KEY to be set in the environment.

    Args:
        report: The report to enrich.
        categories: If provided, only explain findings from these categories.
                    If None, explain all failed findings.
    """
    failed_findings = [
        finding
        for finding in report.failed_findings
        if categories is None or finding.category in categories
    ]

    if not failed_findings:
        return report

    client = anthropic.Anthropic()

    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": _build_prompt(failed_findings)}],
        output_format=ExplanationResponse,
    )

    # Build a lookup keyed by (rule_id, resource) for fast matching
    explanation_map: dict[tuple[str, str | None], str] = {
        (item.rule_id, item.resource): item.explanation
        for item in response.parsed_output.explanations
    }

    for finding in failed_findings:
        finding.ai_explanation = explanation_map.get((finding.rule_id, finding.resource))

    return report
