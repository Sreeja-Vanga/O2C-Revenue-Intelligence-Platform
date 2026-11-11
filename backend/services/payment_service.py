from typing import Any

from backend.services.transaction_service import get_record, list_records


def list_payments(args: Any) -> dict[str, Any]:
    return list_records("payments", args)


def get_payment(payment_id: str) -> dict[str, Any] | None:
    return get_record("payments", payment_id)