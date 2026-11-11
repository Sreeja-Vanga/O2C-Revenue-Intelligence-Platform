from decimal import Decimal
from typing import Any

from backend.services.detection_engine import run_all_rules


def get_reconciliation_summary() -> dict[str, Any]:
    """Summarize source-table reconciliation findings without persisting them."""
    findings = run_all_rules()
    by_type: dict[str, dict[str, Any]] = {}
    total_exposure = Decimal("0.00")
    for finding in findings:
        anomaly_code = finding["anomaly_code"]
        row = by_type.setdefault(anomaly_code, {
            "anomaly_code": anomaly_code,
            "finding_count": 0,
            "estimated_exposure": Decimal("0.00"),
        })
        row["finding_count"] += 1
        exposure = finding["estimated_leakage"]
        if not isinstance(exposure, Decimal):
            exposure = Decimal(str(exposure))
        row["estimated_exposure"] += exposure
        total_exposure += exposure
    return {
        "total_findings": len(findings),
        "total_estimated_exposure": total_exposure,
        "by_anomaly_type": list(by_type.values()),
    }