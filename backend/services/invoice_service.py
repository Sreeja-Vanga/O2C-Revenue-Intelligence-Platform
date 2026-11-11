from typing import Any

from backend.services.transaction_service import get_record, list_records


def list_invoices(args: Any) -> dict[str, Any]:
    return list_records("invoices", args)


def get_invoice(invoice_id: str) -> dict[str, Any] | None:
    return get_record("invoices", invoice_id)