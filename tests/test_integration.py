from pathlib import Path

from infracheck.analyzers.engine import run
from infracheck.parsers.terraform import parse_directory

FIXTURES_PATH = str(Path(__file__).parent / "fixtures")


class TestIntegration:
    def setup_method(self):
        resources = parse_directory(FIXTURES_PATH)
        self.report = run(path=FIXTURES_PATH, resources=resources)

    def test_report_is_produced(self):
        assert self.report is not None

    def test_report_has_four_categories(self):
        assert len(self.report.categories) == 4

    def test_overall_score_is_below_ten(self):
        # The fixture has several intentional failures so the score should not be perfect
        assert self.report.overall_score < 10

    def test_has_failures(self):
        assert len(self.report.failed_findings) > 0

    def test_sqs_dlq_fails(self):
        finding = self._get_finding("sqs_dlq_configured")
        assert finding is not None
        assert finding.passed is False

    def test_rds_multi_az_fails(self):
        finding = self._get_finding("rds_multi_az_enabled")
        assert finding is not None
        assert finding.passed is False

    def test_rds_backup_retention_fails(self):
        finding = self._get_finding("rds_backup_retention")
        assert finding is not None
        assert finding.passed is False

    def test_s3_public_access_passes(self):
        finding = self._get_finding("s3_public_access_blocked")
        assert finding is not None
        assert finding.passed is True

    def test_cloudwatch_alarms_pass(self):
        finding = self._get_finding("cloudwatch_alarms_exist")
        assert finding is not None
        assert finding.passed is True

    def test_lambda_log_group_passes(self):
        finding = self._get_finding("lambda_log_group_exists")
        assert finding is not None
        assert finding.passed is True

    def test_vpc_flow_logs_pass(self):
        finding = self._get_finding("vpc_flow_logs_enabled")
        assert finding is not None
        assert finding.passed is True

    def test_ec2_imdsv2_passes(self):
        finding = self._get_finding("ec2_imdsv2_required")
        assert finding is not None
        assert finding.passed is True

    def _get_finding(self, rule_id: str):
        for category in self.report.categories:
            for finding in category.findings:
                if finding.rule_id == rule_id:
                    return finding
        return None
