"""Compatibility exports for code importing the legacy database module."""

from backend.database.db import (
    DatabaseUnavailable,
    check_connection,
    connection_manager,
    fetch_all,
    fetch_one,
    run_transaction,
)


__all__ = [
    "DatabaseUnavailable",
    "check_connection",
    "connection_manager",
    "fetch_all",
    "fetch_one",
    "run_transaction",
]