from datetime import date

from flask import Blueprint, request

from backend.services import exception_service
from backend.utils.response import error_response, success_response
from backend.utils.validators import (
    EXCEPTION_SEVERITIES,
    EXCEPTION_STATUSES,
    ANOMALY_CODES,
    ValidationError,
    optional_enum,
    pagination_args,
    status_from_body,
)


exception_bp = Blueprint("exceptions", __name__, url_prefix="/api/exceptions")


@exception_bp.get("")
def list_exceptions():
    page, per_page = pagination_args(request)
    anomaly_code = optional_enum(
        request.args.get("anomaly_code"), ANOMALY_CODES, "anomaly_code"
    )
    severity = optional_enum(
        request.args.get("severity"), EXCEPTION_SEVERITIES, "severity"
    )
    status = optional_enum(
        request.args.get("status"), EXCEPTION_STATUSES, "status"
    )
    date_from = _date_arg("date_from")
    date_to = _date_arg("date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError("date_from must not be later than date_to.")
    search = request.args.get("search")
    if search is not None and len(search) > 200:
        raise ValidationError("search must be at most 200 characters.")
    data = exception_service.list_exceptions(
        anomaly_code,
        severity,
        status,
        page,
        per_page,
        request.args.get("sort_by", "detected_at"),
        request.args.get("sort_order", "desc"),
        date_from,
        date_to,
        search,
    )
    return success_response(data)


@exception_bp.get("/summary")
def summary():
    return success_response(exception_service.get_summary())


@exception_bp.get("/<exception_id>")
def get_exception(exception_id: str):
    row = exception_service.get_exception(exception_id)
    if row is None:
        return error_response("Exception not found.", 404)
    return success_response(row)


@exception_bp.get("/<exception_id>/source")
def get_exception_source(exception_id: str):
    source = exception_service.get_source(exception_id)
    if source is None:
        return error_response("Exception not found.", 404)
    return success_response(source)


@exception_bp.put("/<exception_id>/status")
def update_status(exception_id: str):
    status = status_from_body(request.get_json(silent=False))
    row = exception_service.update_status(exception_id, status)
    if row is None:
        return error_response("Exception not found.", 404)
    return success_response(row, "Exception status updated successfully.")


def _date_arg(field: str) -> str | None:
    value = request.args.get(field)
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValidationError(f"{field} must use YYYY-MM-DD format.") from exc