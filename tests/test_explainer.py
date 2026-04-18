from unittest.mock import MagicMock, patch

from infracheck.explainer import (
    ExplanationResponse,
    FindingExplanation,
    _build_prompt,
    explain_findings,
)
from infracheck.models import CategoryScore, Report, RuleResult


def _make_report(findings: list[RuleResult]) -> Report:
    return Report(
        path="./infra",
        categories=[CategoryScore(name="security", score=5, findings=findings)],
        overall_score=5,
    )


def _make_finding(
    rule_id: str, passed: bool, resource: str | None = None, category: str = "security"
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category=category,
        severity="high",
        passed=passed,
        message="test message",
        resource=resource,
    )


def _mock_response(explanations: list[FindingExplanation]) -> MagicMock:
    response = MagicMock()
    response.parsed_output = ExplanationResponse(explanations=explanations)
    return response


class TestExplainFindings:
    def test_returns_report_unchanged_when_no_failures(self):
        report = _make_report([_make_finding("some_rule", passed=True)])

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            result = explain_findings(report)

        mock_anthropic.assert_not_called()
        assert result is report

    def test_populates_ai_explanation_on_failed_finding(self):
        finding = _make_finding("s3_public_access", passed=False, resource="my_bucket")
        report = _make_report([finding])

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.parse.return_value = _mock_response(
                [
                    FindingExplanation(
                        rule_id="s3_public_access",
                        resource="my_bucket",
                        explanation="Set block_public_acls = true.",
                    )
                ]
            )
            result = explain_findings(report)

        assert result.failed_findings[0].ai_explanation == "Set block_public_acls = true."

    def test_does_not_populate_ai_explanation_on_passed_findings(self):
        report = _make_report(
            [
                _make_finding("s3_public_access", passed=True),
                _make_finding("rds_multi_az", passed=False, resource="my_db"),
            ]
        )

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.parse.return_value = _mock_response(
                [
                    FindingExplanation(
                        rule_id="rds_multi_az", resource="my_db", explanation="Set multi_az = true."
                    )
                ]
            )
            result = explain_findings(report)

        assert all(finding.ai_explanation is None for finding in result.passed_findings)

    def test_matches_by_rule_id_and_resource(self):
        report = _make_report(
            [
                _make_finding("sqs_dlq", passed=False, resource="queue_a"),
                _make_finding("sqs_dlq", passed=False, resource="queue_b"),
            ]
        )

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.parse.return_value = _mock_response(
                [
                    FindingExplanation(
                        rule_id="sqs_dlq", resource="queue_a", explanation="Fix for queue_a."
                    ),
                    FindingExplanation(
                        rule_id="sqs_dlq", resource="queue_b", explanation="Fix for queue_b."
                    ),
                ]
            )
            result = explain_findings(report)

        explanations = {
            finding.resource: finding.ai_explanation for finding in result.failed_findings
        }
        assert explanations["queue_a"] == "Fix for queue_a."
        assert explanations["queue_b"] == "Fix for queue_b."

    def test_ai_explanation_is_none_when_missing_from_response(self):
        report = _make_report([_make_finding("unknown_rule", passed=False, resource="res")])

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.parse.return_value = _mock_response([])
            result = explain_findings(report)

        assert result.failed_findings[0].ai_explanation is None

    def test_category_filter_only_explains_matching_category(self):
        security_finding = _make_finding(
            "s3_public_access", passed=False, resource="bucket", category="security"
        )
        fault_finding = _make_finding(
            "sqs_dlq", passed=False, resource="queue", category="fault_tolerance"
        )

        from infracheck.models import CategoryScore

        report = Report(
            path="./infra",
            overall_score=5,
            categories=[
                CategoryScore(name="security", score=5, findings=[security_finding]),
                CategoryScore(name="fault_tolerance", score=5, findings=[fault_finding]),
            ],
        )

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.parse.return_value = _mock_response(
                [
                    FindingExplanation(
                        rule_id="s3_public_access",
                        resource="bucket",
                        explanation="Fix for security.",
                    )
                ]
            )
            result = explain_findings(report, categories={"security"})

        security_results = next(cat for cat in result.categories if cat.name == "security")
        fault_results = next(cat for cat in result.categories if cat.name == "fault_tolerance")

        assert security_results.findings[0].ai_explanation == "Fix for security."
        assert fault_results.findings[0].ai_explanation is None

    def test_category_filter_skips_api_call_when_no_matching_failures(self):
        finding = _make_finding(
            "s3_public_access", passed=False, resource="bucket", category="security"
        )
        report = _make_report([finding])

        with patch("infracheck.explainer.anthropic.Anthropic") as mock_anthropic:
            result = explain_findings(report, categories={"observability"})

        mock_anthropic.assert_not_called()
        assert result is report


class TestBuildPrompt:
    def test_includes_rule_id(self):
        finding = _make_finding("sqs_dlq_configured", passed=False, resource="my_queue")
        assert "sqs_dlq_configured" in _build_prompt([finding])

    def test_includes_resource_name(self):
        finding = _make_finding("sqs_dlq_configured", passed=False, resource="my_queue")
        assert "my_queue" in _build_prompt([finding])

    def test_includes_message(self):
        finding = _make_finding("sqs_dlq_configured", passed=False)
        assert finding.message in _build_prompt([finding])

    def test_handles_finding_without_resource(self):
        finding = _make_finding("some_rule", passed=False, resource=None)
        prompt = _build_prompt([finding])
        assert "some_rule" in prompt
        assert "None" not in prompt
