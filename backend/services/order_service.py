from typing import Any

from backend.services.transaction_service import get_record, list_records


def list_orders(args: Any) -> dict[str, Any]:
    return list_records("orders", args)


def get_order(sales_order_id: str) -> dict[str, Any] | None:
    return get_record("orders", sales_order_id)