from collections import defaultdict
from decimal import Decimal
from typing import Any

from backend.database.db import fetch_all, fetch_one


def get_revenue_leakage() -> dict[str, Any]:
    rows = fetch_all("""
        SELECT
            anomaly_code,
            COUNT(*) AS exception_count,
            COALESCE(SUM(GREATEST(variance_amount, 0)), 0) AS estimated_leakage
        FROM exception
        GROUP BY anomaly_code
        ORDER BY anomaly_code
    """)
    return {
        "items": rows,
        "total_estimated_leakage": sum(
            (row["estimated_leakage"] for row in rows), Decimal("0.00")
        ),
    }


def get_order_performance() -> dict[str, Any]:
    rows = fetch_all("""
        SELECT status, COUNT(*) AS order_count,
               COALESCE(SUM(total_amount), 0) AS order_value
        FROM sales_order
        GROUP BY status
        ORDER BY status
    """)
    return {"items": rows, "total_orders": sum(row["order_count"] for row in rows)}


def get_invoice_performance() -> dict[str, Any]:
    rows = fetch_all("""
        SELECT
            status,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(total_amount), 0) AS invoice_amount,
            COALESCE(SUM(GREATEST(open_amount, 0)), 0) AS outstanding_amount
        FROM invoice
        GROUP BY status
        ORDER BY status
    """)
    overdue = fetch_one("""
        SELECT
            COUNT(*) AS invoice_count,
            COALESCE(SUM(GREATEST(open_amount, 0)), 0) AS outstanding_amount
        FROM invoice
        WHERE status IN ('ISSUED', 'PARTIALLY_PAID')
          AND due_date < CURRENT_DATE
          AND open_amount > 0
    """) or {"invoice_count": 0, "outstanding_amount": Decimal("0.00")}
    by_status = {row["status"]: row for row in rows}
    return {
        "by_status": by_status,
        "paid": by_status.get("PAID", {"invoice_count": 0, "invoice_amount": 0}),
        "partially_paid": by_status.get(
            "PARTIALLY_PAID", {"invoice_count": 0, "invoice_amount": 0}
        ),
        "issued": by_status.get("ISSUED", {"invoice_count": 0, "invoice_amount": 0}),
        "overdue": overdue,
    }


def get_payment_performance() -> dict[str, Any]:
    totals = fetch_one("""
        SELECT
            COUNT(*) AS payment_count,
            COALESCE(SUM(CASE WHEN status <> 'VOID' THEN amount ELSE 0 END), 0)
                AS payment_total,
            COALESCE(SUM(CASE WHEN status <> 'VOID' THEN unapplied_amount ELSE 0 END), 0)
                AS reported_unapplied_total
        FROM payment
    """) or {}
    allocation = fetch_one("""
        SELECT COALESCE(SUM(pa.allocated_amount), 0) AS allocation_total
        FROM payment_allocation pa
        JOIN payment p ON p.payment_id = pa.payment_id
        WHERE p.status <> 'VOID'
    """) or {"allocation_total": Decimal("0.00")}
    totals["allocation_total"] = allocation["allocation_total"]
    totals["calculated_unapplied_total"] = (
        totals.get("payment_total", Decimal("0.00"))
        - allocation["allocation_total"]
    )
    invoiced = fetch_one("""
        SELECT COALESCE(SUM(total_amount), 0) AS invoice_total
        FROM invoice
        WHERE status <> 'VOID'
    """) or {"invoice_total": Decimal("0.00")}
    invoice_total = invoiced["invoice_total"]
    totals["collection_rate_pct"] = (
        100 * totals["payment_total"] / invoice_total
        if invoice_total
        else Decimal("0.00")
    )
    return totals


def get_trends() -> dict[str, Any]:
    invoice_rows = fetch_all("""
        SELECT DATE_FORMAT(invoice_date, '%Y-%m') AS month,
               COUNT(*) AS invoice_count,
               COALESCE(SUM(total_amount), 0) AS invoiced_amount
        FROM invoice
        GROUP BY DATE_FORMAT(invoice_date, '%Y-%m')
        ORDER BY month
    """)
    payment_rows = fetch_all("""
        SELECT DATE_FORMAT(payment_date, '%Y-%m') AS month,
               COUNT(*) AS payment_count,
               COALESCE(SUM(amount), 0) AS payment_amount
        FROM payment
        WHERE status <> 'VOID'
        GROUP BY DATE_FORMAT(payment_date, '%Y-%m')
        ORDER BY month
    """)
    exception_rows = fetch_all("""
        SELECT DATE_FORMAT(detected_at, '%Y-%m') AS month,
               COUNT(*) AS exception_count
        FROM exception
        GROUP BY DATE_FORMAT(detected_at, '%Y-%m')
        ORDER BY month
    """)

    months: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "invoice_count": 0,
        "invoiced_amount": Decimal("0.00"),
        "payment_count": 0,
        "payment_amount": Decimal("0.00"),
        "exception_count": 0,
    })
    for row in invoice_rows:
        months[row["month"]].update({
            "invoice_count": row["invoice_count"],
            "invoiced_amount": row["invoiced_amount"],
        })
    for row in payment_rows:
        months[row["month"]].update({
            "payment_count": row["payment_count"],
            "payment_amount": row["payment_amount"],
        })
    for row in exception_rows:
        months[row["month"]]["exception_count"] = row["exception_count"]
    return {"items": [{"month": month, **months[month]} for month in sorted(months)]}


def get_invoice_aging() -> dict[str, Any]:
    rows = fetch_all("""
        SELECT
            CASE
                WHEN due_date >= CURRENT_DATE THEN 'CURRENT'
                WHEN DATEDIFF(CURRENT_DATE, due_date) BETWEEN 1 AND 30 THEN '1_30_DAYS'
                WHEN DATEDIFF(CURRENT_DATE, due_date) BETWEEN 31 AND 60 THEN '31_60_DAYS'
                WHEN DATEDIFF(CURRENT_DATE, due_date) BETWEEN 61 AND 90 THEN '61_90_DAYS'
                ELSE 'OVER_90_DAYS'
            END AS aging_bucket,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(GREATEST(open_amount, 0)), 0) AS outstanding_amount
        FROM invoice
        WHERE open_amount > 0 AND status <> 'VOID'
        GROUP BY aging_bucket
        ORDER BY FIELD(
            aging_bucket, 'CURRENT', '1_30_DAYS', '31_60_DAYS',
            '61_90_DAYS', 'OVER_90_DAYS'
        )
    """)
    return {"items": rows}


def get_dispute_analysis() -> dict[str, Any]:
    by_status = fetch_all("""
        SELECT
            status,
            COUNT(*) AS dispute_count,
            COALESCE(SUM(disputed_amount), 0) AS disputed_amount,
            COALESCE(SUM(approved_credit_amount), 0) AS approved_credit_amount
        FROM dispute
        GROUP BY status
        ORDER BY status
    """)
    unapplied = fetch_one("""
        SELECT COUNT(*) AS invoice_count,
               COALESCE(SUM(approved_credit_amount - credit_amount), 0)
                   AS unapplied_approved_credit
        FROM (
            SELECT d.invoice_id,
                   SUM(d.approved_credit_amount) AS approved_credit_amount,
                   MAX(i.credit_amount) AS credit_amount
            FROM dispute d
            JOIN invoice i ON i.invoice_id = d.invoice_id
            WHERE d.status = 'APPROVED'
            GROUP BY d.invoice_id
            HAVING SUM(d.approved_credit_amount) > MAX(i.credit_amount)
        ) AS unapplied_credits
    """) or {"invoice_count": 0, "unapplied_approved_credit": Decimal("0.00")}
    return {"by_status": by_status, "unapplied_approved_credits": unapplied}


def get_lifecycle_performance() -> dict[str, Any]:
    conversion = fetch_one("""
        SELECT
            COUNT(*) AS quote_count,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) AS converted_quotes,
            COALESCE(
                100.0 * SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0),
                0
            ) AS quote_conversion_rate_pct
        FROM quote
    """) or {}
    fulfillment = fetch_one("""
        SELECT
            COUNT(DISTINCT so.sales_order_id) AS order_count,
            COUNT(DISTINCT CASE WHEN s.shipment_id IS NOT NULL
                                THEN so.sales_order_id END) AS orders_with_shipments,
            COUNT(DISTINCT CASE WHEN s.status = 'DELIVERED'
                                THEN so.sales_order_id END) AS delivered_orders
        FROM sales_order so
        LEFT JOIN shipment s ON s.sales_order_id = so.sales_order_id
    """) or {}
    timing = fetch_one("""
        SELECT
            (
                SELECT AVG(DATEDIFF(first_invoice.invoice_date, so.order_date))
                FROM sales_order so
                JOIN (
                    SELECT sales_order_id, MIN(invoice_date) AS invoice_date
                    FROM invoice
                    GROUP BY sales_order_id
                ) AS first_invoice ON first_invoice.sales_order_id = so.sales_order_id
            ) AS avg_order_to_invoice_days,
            (
                SELECT AVG(DATEDIFF(first_payment.payment_date, i.invoice_date))
                FROM invoice i
                JOIN (
                    SELECT pa.invoice_id, MIN(p.payment_date) AS payment_date
                    FROM payment_allocation pa
                    JOIN payment p ON p.payment_id = pa.payment_id
                    WHERE p.status <> 'VOID'
                    GROUP BY pa.invoice_id
                ) AS first_payment ON first_payment.invoice_id = i.invoice_id
            ) AS avg_invoice_to_payment_days
    """) or {}
    return {
        "quotes": conversion,
        "fulfillment": fulfillment,
        "timing": timing,
    }


def get_outstanding_receivables() -> dict[str, Any]:
    rows = fetch_all("""
        SELECT
            i.account_id,
            a.account_name,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(GREATEST(i.open_amount, 0)), 0) AS outstanding_amount
        FROM invoice i
        JOIN account a ON a.account_id = i.account_id
        WHERE i.open_amount > 0 AND i.status <> 'VOID'
        GROUP BY i.account_id, a.account_name
        ORDER BY outstanding_amount DESC, i.account_id
    """)
    return {
        "items": rows,
        "total_outstanding_amount": sum(
            (row["outstanding_amount"] for row in rows), Decimal("0.00")
        ),
    }