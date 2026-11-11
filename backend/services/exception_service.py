from typing import Any

from backend.repositories import exception_repository, transaction_repository
from backend.utils.validators import (
    ANOMALY_CODES,
    EXCEPTION_SEVERITIES,
    EXCEPTION_STATUSES,
    ValidationError,
)


def list_exceptions(
    anomaly_code: str | None,
    severity: str | None,
    status: str | None,
    page: int,
    per_page: int,
    sort_by: str,
    sort_order: str,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    if anomaly_code is not None and anomaly_code not in ANOMALY_CODES:
        raise ValidationError("Invalid anomaly_code.")
    if severity is not None and severity not in EXCEPTION_SEVERITIES:
        raise ValidationError("Invalid severity.")
    if status is not None and status not in EXCEPTION_STATUSES:
        raise ValidationError("Invalid status.")
    if sort_by not in exception_repository.SORT_COLUMNS:
        raise ValidationError("Invalid sort_by field.")
    normalized_order = sort_order.lower()
    if normalized_order not in {"asc", "desc"}:
        raise ValidationError("sort_order must be asc or desc.")
    rows, total = exception_repository.list_exceptions(
        {"anomaly_code": anomaly_code, "severity": severity, "status": status},
        page,
        per_page,
        sort_by,
        normalized_order,
        date_from,
        date_to,
        search,
    )
    return {
        "items": rows,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


def get_exception(exception_id: str) -> dict[str, Any] | None:
    return exception_repository.get_exception(exception_id)


def get_summary() -> dict[str, Any]:
    rows = exception_repository.get_summary()
    by_anomaly: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total = 0
    for row in rows:
        count = int(row["exception_count"])
        total += count
        by_anomaly[row["anomaly_code"]] = by_anomaly.get(row["anomaly_code"], 0) + count
        by_severity[row["severity"]] = by_severity.get(row["severity"], 0) + count
        by_status[row["status"]] = by_status.get(row["status"], 0) + count
    return {
        "total_exceptions": total,
        "count_by_anomaly_type": by_anomaly,
        "count_by_severity": by_severity,
        "count_by_status": by_status,
    }


def update_status(exception_id: str, status: str) -> dict[str, Any] | None:
    if status not in EXCEPTION_STATUSES:
        raise ValidationError("Invalid exception status.")
    return exception_repository.update_status(exception_id, status)


def get_source(exception_id: str) -> dict[str, Any] | None:
    return transaction_repository.get_related_exception_records(exception_id)