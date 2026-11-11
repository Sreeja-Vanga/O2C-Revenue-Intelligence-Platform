from datetime import date
from typing import Any

from backend.repositories import transaction_repository
from backend.utils.validators import ValidationError, pagination_args


def _validate_date(value: str | None, field: str) -> str | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValidationError(f"{field} must use YYYY-MM-DD format.") from exc


def list_records(
    resource: str,
    args: Any,
) -> dict[str, Any]:
    config = transaction_repository.RESOURCE_CONFIG[resource]
    try:
        page = int(args.get("page", "1"))
        per_page = int(args.get("per_page", "50"))
    except ValueError as exc:
        raise ValidationError("page and per_page must be integers.") from exc
    if page < 1:
        raise ValidationError("page must be at least 1.")
    if not 1 <= per_page <= 200:
        raise ValidationError("per_page must be between 1 and 200.")

    sort_by = args.get("sort_by", config["id"])
    if sort_by not in config["sort"]:
        raise ValidationError("Invalid sort_by field.")
    sort_order = args.get("sort_order", "asc").lower()
    if sort_order not in {"asc", "desc"}:
        raise ValidationError("sort_order must be asc or desc.")
    date_from = _validate_date(args.get("date_from"), "date_from")
    date_to = _validate_date(args.get("date_to"), "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError("date_from must not be later than date_to.")
    if (date_from or date_to) and not config["dates"]:
        raise ValidationError(f"Date filtering is not supported for {resource}.")

    filters = {
        key: value
        for key in config["filters"]
        if (value := args.get(key)) is not None
    }
    search = args.get("search")
    if search is not None and len(search) > 200:
        raise ValidationError("search must be at most 200 characters.")
    rows, total = transaction_repository.list_records(
        resource,
        filters,
        page,
        per_page,
        sort_by,
        sort_order,
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


def get_record(resource: str, record_id: str) -> dict[str, Any] | None:
    if resource == "events":
        try:
            record_id = str(int(record_id))
        except ValueError as exc:
            raise ValidationError("status_event_id must be an integer.") from exc
    return transaction_repository.get_record(resource, record_id)


def get_resource_schema(resource: str) -> dict[str, Any]:
    try:
        return transaction_repository.get_resource_schema(resource)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def create_record(resource: str, values: Any) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise ValidationError("A JSON object is required.")
    try:
        record_id = transaction_repository.create_record(resource, values)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    record = transaction_repository.get_record(resource, record_id)
    if record is None:
        raise RuntimeError("The record was created but could not be retrieved.")
    return record


def update_record(resource: str, record_id: str, values: Any) -> dict[str, Any] | None:
    if not isinstance(values, dict):
        raise ValidationError("A JSON object is required.")
    try:
        updated = transaction_repository.update_record(resource, record_id, values)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return transaction_repository.get_record(resource, record_id) if updated else None


def delete_record(resource: str, record_id: str) -> bool:
    try:
        return transaction_repository.delete_record(resource, record_id)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def get_events_for_entity(entity_type: str, entity_id: str) -> dict[str, Any]:
    return list_records(
        "events",
        {
            "entity_type": entity_type.strip().upper(),
            "entity_id": entity_id,
            "page": "1",
            "per_page": "200",
            "sort_by": "event_at",
            "sort_order": "asc",
        },
    )


def get_exception_source(exception_id: str) -> dict[str, Any] | None:
    return transaction_repository.get_related_exception_records(exception_id)
