from typing import Any

from backend.services.transaction_service import get_record, list_records


def list_shipments(args: Any) -> dict[str, Any]:
    return list_records("shipments", args)


def get_shipment(shipment_id: str) -> dict[str, Any] | None:
    return get_record("shipments", shipment_id)