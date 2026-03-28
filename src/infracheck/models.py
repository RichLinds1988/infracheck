from pydantic import BaseModel


class RuleResult(BaseModel):
    rule_id: str
    category: str
    severity: str  # high, medium, low
    passed: bool
    message: str
    resource: str | None = None
    ai_explanation: str | None = None


class CategoryScore(BaseModel):
    name: str
    score: int  # 0-10
    findings: list[RuleResult]


class Report(BaseModel):
    path: str
    categories: list[CategoryScore]
    overall_score: int

    @property
    def failed_findings(self) -> list[RuleResult]:
        return [
            finding for cat in self.categories for finding in cat.findings if not finding.passed
        ]

    @property
    def passed_findings(self) -> list[RuleResult]:
        return [finding for cat in self.categories for finding in cat.findings if finding.passed]
