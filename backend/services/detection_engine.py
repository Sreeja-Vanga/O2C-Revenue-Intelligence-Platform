import logging
from datetime import datetime
from decimal import Decimal
from threading import Lock
from typing import Any, Callable

from backend.repositories import transaction_repository as repository


logger = logging.getLogger(__name__)
_results_lock = Lock()
_latest_results: dict[str, Any] = {
    "has_run": False,
    "run_at": None,
    "total_detected": 0,
    "results": [],
}

SEVERITY_BY_CODE = {
    "PRICE_VARIANCE": "HIGH",
    "SHIPMENT_QUANTITY": "HIGH",
    "BILLING_MISMATCH": "HIGH",
    "CASH_APPLICATION": "HIGH",
    "DISPUTE_LEAKAGE": "HIGH",
    "ORDER_CLOSED_UNPAID": "HIGH",
    "STATUS_TRANSITION_SKIP": "HIGH",
}


def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _finding(
    anomaly_code: str,
    entity_type: str,
    entity_id: Any,
    expected: Any,
    actual: Any,
    variance: Any,
    explanation: str,
    estimated_leakage: Any,
    **details: Any,
) -> dict[str, Any]:
    return {
        "anomaly_code": anomaly_code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "severity": SEVERITY_BY_CODE[anomaly_code],
        "expected_value": expected,
        "actual_value": actual,
        "variance": variance,
        "estimated_leakage": estimated_leakage,
        "explanation": explanation,
        "details": details,
    }


def detect_price_variance() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_price_variances():
        expected = _decimal(row["quoted_net_unit_price"])
        actual = _decimal(row["net_unit_price"])
        quantity = _decimal(row["quantity_ordered"])
        difference = actual - expected
        findings.append(_finding(
            "PRICE_VARIANCE", "ORDER_LINE", row["order_line_id"],
            expected, actual, difference,
            "Order net unit price differs from the corresponding quote line.",
            abs(difference * quantity),
            sales_order_id=row["sales_order_id"],
            account_id=row["account_id"],
            quote_id=row["quote_id"],
            quote_line_id=row["quote_line_id"],
            product_code=row["product_code"],
            quantity_ordered=quantity,
        ))
    return findings


def detect_shipment_quantity() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_shipment_overages():
        expected = _decimal(row["quantity_ordered"])
        actual = _decimal(row["quantity_shipped"])
        excess = actual - expected
        findings.append(_finding(
            "SHIPMENT_QUANTITY", "SHIPMENT_LINE",
            row["representative_shipment_line_id"],
            expected, actual, excess,
            "Cumulative shipment quantity exceeds the ordered quantity.",
            excess * _decimal(row["net_unit_price"]),
            sales_order_id=row["sales_order_id"],
            account_id=row["account_id"],
            order_line_id=row["order_line_id"],
            product_code=row["product_code"],
            shipment_line_ids=row["shipment_line_ids"],
        ))
    return findings


def detect_billing_mismatch() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_billing_overages():
        expected = _decimal(row["expected_quantity"])
        actual = _decimal(row["actual_quantity"])
        excess = actual - expected
        average_billed_unit_amount = (
            _decimal(row["billed_amount"]) / actual if actual else Decimal("0")
        )
        findings.append(_finding(
            "BILLING_MISMATCH", row["entity_type"], row["entity_id"],
            expected, actual, excess,
            "Invoice quantity billed against the shipment exceeds the shipped quantity."
            if row["comparison_type"] == "SHIPPED"
            else "Invoice quantity was billed without a corresponding shipment.",
            excess * average_billed_unit_amount,
            sales_order_id=row["sales_order_id"],
            account_id=row["account_id"],
            order_line_id=row["order_line_id"],
            shipment_line_id=row["shipment_line_id"],
            invoice_ids=row["invoice_ids"],
            invoice_line_ids=row["invoice_line_ids"],
        ))
    return findings


def detect_cash_application() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_payment_application_errors():
        expected = _decimal(row["amount"])
        actual = _decimal(row["allocated_amount"])
        unreported_cash = expected - actual - _decimal(row["unapplied_amount"])
        overage = max(actual - expected, Decimal("0"))
        leakage = max(overage, abs(unreported_cash))
        findings.append(_finding(
            "CASH_APPLICATION", "PAYMENT", row["payment_id"],
            expected, actual, actual - expected,
            "Payment allocations exceed the received payment or do not reconcile "
            "to its reported unapplied amount.",
            leakage,
            payment_id=row["payment_id"],
            account_id=row["account_id"],
            reported_unapplied_amount=row["unapplied_amount"],
            allocation_ids=row["allocation_ids"],
        ))
    return findings


def detect_dispute_leakage() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_unapplied_dispute_credits():
        expected = _decimal(row["credit_amount"])
        actual = _decimal(row["approved_credit_amount"])
        findings.append(_finding(
            "DISPUTE_LEAKAGE", "INVOICE", row["invoice_id"],
            expected, actual, actual - expected,
            "Approved dispute credits exceed the credit amount posted to the invoice.",
            actual - expected,
            invoice_id=row["invoice_id"],
            account_id=row["account_id"],
            dispute_ids=row["dispute_ids"],
        ))
    return findings


def detect_order_closed_unpaid() -> list[dict[str, Any]]:
    findings = []
    for row in repository.get_closed_unpaid_orders():
        outstanding = _decimal(row["outstanding_amount"])
        findings.append(_finding(
            "ORDER_CLOSED_UNPAID", "SALES_ORDER", row["sales_order_id"],
            Decimal("0.00"), outstanding, outstanding,
            "Sales order is closed while one or more linked invoices have an "
            "outstanding balance.",
            outstanding,
            sales_order_id=row["sales_order_id"],
            account_id=row["account_id"],
            invoice_ids=row["invoice_ids"],
        ))
    return findings


def detect_status_transition_skip() -> list[dict[str, Any]]:
    findings = []
    seen_orders: set[str] = set()
    for row in repository.get_skipped_order_transitions():
        order_id = row["sales_order_id"]
        if order_id in seen_orders:
            continue
        seen_orders.add(order_id)
        findings.append(_finding(
            "STATUS_TRANSITION_SKIP", "SALES_ORDER", order_id,
            "DELIVERED", row["to_status"], None,
            "Sales order transitioned directly from SHIPPED to CLOSED, "
            "skipping the verified DELIVERED lifecycle state.",
            Decimal("0.00"),
            sales_order_id=order_id,
            status_event_id=row["status_event_id"],
            from_status=row["from_status"],
            to_status=row["to_status"],
            event_at=row["event_at"],
            actor=row["actor"],
            note=row["note"],
        ))
    return findings


DETECTION_RULES: tuple[Callable[[], list[dict[str, Any]]], ...] = (
    detect_price_variance,
    detect_shipment_quantity,
    detect_billing_mismatch,
    detect_cash_application,
    detect_dispute_leakage,
    detect_order_closed_unpaid,
    detect_status_transition_skip,
)


def run_all_rules() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rule in DETECTION_RULES:
        for finding in rule():
            identity = (
                finding["anomaly_code"],
                finding["entity_type"],
                str(finding["entity_id"]),
            )
            if identity not in seen:
                seen.add(identity)
                results.append(finding)
    logger.info("Detection completed: %d independent findings.", len(results))
    return results


def run_detection() -> dict[str, Any]:
    results = run_all_rules()
    snapshot = {
        "has_run": True,
        "run_at": datetime.now().astimezone().isoformat(),
        "total_detected": len(results),
        "results": results,
    }
    with _results_lock:
        _latest_results.update(snapshot)
        return dict(_latest_results)


def get_latest_results() -> dict[str, Any]:
    with _results_lock:
        return {
            **_latest_results,
            "results": list(_latest_results["results"]),
        }


def get_detection_summary() -> dict[str, Any]:
    snapshot = get_latest_results()
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    leakage = Decimal("0.00")
    for finding in snapshot["results"]:
        code = finding["anomaly_code"]
        severity = finding["severity"]
        by_type[code] = by_type.get(code, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1
        leakage += _decimal(finding["estimated_leakage"])
    return {
        "has_run": snapshot["has_run"],
        "run_at": snapshot["run_at"],
        "total_detected_anomalies": snapshot["total_detected"],
        "count_by_anomaly_type": by_type,
        "count_by_severity": by_severity,
        "estimated_revenue_leakage": leakage,
    }
