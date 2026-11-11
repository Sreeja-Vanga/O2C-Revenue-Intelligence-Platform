from typing import Any

from backend.services.transaction_service import get_record, list_records


def list_quotes(args: Any) -> dict[str, Any]:
    return list_records("quotes", args)


def get_quote(quote_id: str) -> dict[str, Any] | None:
    return get_record("quotes", quote_id)