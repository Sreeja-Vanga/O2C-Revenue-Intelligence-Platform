from typing import Any

from backend.database.db import fetch_all, fetch_one


def get_overview() -> dict[str, Any]:
    query = """
        SELECT
            (SELECT COUNT(*) FROM account) AS total_accounts,
            (SELECT COUNT(*) FROM quote) AS total_quotes,
            (SELECT COUNT(*) FROM sales_order) AS total_sales_orders,
            (SELECT COUNT(*) FROM shipment) AS total_shipments,
            (SELECT COUNT(*) FROM invoice) AS total_invoices,
            (SELECT COUNT(*) FROM payment) AS total_payments,
            (SELECT COUNT(*) FROM dispute) AS total_disputes,
            (SELECT COUNT(*) FROM exception) AS total_exceptions,
            (SELECT COUNT(*) FROM exception WHERE status = 'OPEN') AS open_exceptions,
            (SELECT COUNT(*) FROM exception WHERE severity = 'HIGH') AS high_severity_exceptions,
            COALESCE((SELECT SUM(total_amount) FROM invoice), 0) AS total_revenue,
            COALESCE((SELECT SUM(GREATEST(open_amount, 0)) FROM invoice), 0) AS total_outstanding_amount,
            COALESCE((
                SELECT SUM(GREATEST(variance_amount, 0))
                FROM exception
            ), 0) AS total_revenue_leakage
    """
    return fetch_one(query) or {}


def get_anomaly_summary() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT anomaly_code, severity, COUNT(*) AS exception_count
        FROM exception
        GROUP BY anomaly_code, severity
        ORDER BY anomaly_code, severity
    """)


def get_revenue_summary() -> dict[str, Any]:
    row = fetch_one("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_invoiced_amount,
            COALESCE(SUM(amount_paid), 0) AS invoice_amount_paid,
            COALESCE(SUM(GREATEST(open_amount, 0)), 0) AS outstanding_amount,
            COALESCE(SUM(credit_amount), 0) AS credit_amount
        FROM invoice
    """) or {}
    payment_row = fetch_one("""
        SELECT COALESCE(SUM(amount), 0) AS total_collected_amount
        FROM payment
        WHERE status <> 'VOID'
    """) or {}
    leakage_row = fetch_one("""
        SELECT COALESCE(SUM(GREATEST(variance_amount, 0)), 0) AS revenue_leakage_amount
        FROM exception
    """) or {}
    row["total_collected_amount"] = payment_row["total_collected_amount"]
    row["revenue_leakage_amount"] = leakage_row["revenue_leakage_amount"]
    row.pop("invoice_amount_paid", None)
    return row


def get_lifecycle_summary() -> dict[str, Any]:
    quote_counts = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM quote
        GROUP BY status
        ORDER BY status
    """)
    order_counts = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM sales_order
        GROUP BY status
        ORDER BY status
    """)
    shipment_counts = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM shipment
        GROUP BY status
        ORDER BY status
    """)
    invoice_counts = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM invoice
        GROUP BY status
        ORDER BY status
    """)
    return {
        "quotes_by_status": quote_counts,
        "orders_by_status": order_counts,
        "shipments_by_status": shipment_counts,
        "invoices_by_status": invoice_counts,
    }
