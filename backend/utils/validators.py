from typing import Any

from flask import Request


EXCEPTION_STATUSES = {
    "OPEN",
    "ACKNOWLEDGED",
    "RESOLVED",
    "FALSE_POSITIVE",
}
EXCEPTION_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
ANOMALY_CODES = {
    "PRICE_VARIANCE",
    "SHIPMENT_QUANTITY",
    "BILLING_MISMATCH",
    "CASH_APPLICATION",
    "DISPUTE_LEAKAGE",
    "ORDER_CLOSED_UNPAID",
    "STATUS_TRANSITION_SKIP",
}


class ValidationError(ValueError):
    """Raised for invalid API input."""


def optional_enum(value: str | None, allowed: set[str], field: str) -> str | None:
    if value is None or value == "":
        return None
    normalized = value.strip().upper()
    if normalized not in allowed:
        raise ValidationError(f"Invalid {field}.")
    return normalized


def pagination_args(request: Request) -> tuple[int, int]:
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "50"))
    except ValueError as exc:
        raise ValidationError("page and per_page must be integers.") from exc
    if page < 1:
        raise ValidationError("page must be at least 1.")
    if per_page < 1 or per_page > 200:
        raise ValidationError("per_page must be between 1 and 200.")
    return page, per_page


def status_from_body(body: Any) -> str:
    if not isinstance(body, dict):
        raise ValidationError("A JSON object containing status is required.")
    status = body.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValidationError("status is required.")
    normalized = status.strip().upper()
    if normalized not in EXCEPTION_STATUSES:
        raise ValidationError("Invalid exception status.")
    return normalized