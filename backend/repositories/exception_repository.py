from typing import Any

from backend.database.db import fetch_all, fetch_one, run_transaction


SORT_COLUMNS = {
    "exception_id": "exception_id",
    "anomaly_code": "anomaly_code",
    "severity": "severity",
    "status": "status",
    "detected_at": "detected_at",
    "created_at": "created_at",
    "variance_amount": "variance_amount",
}


def list_exceptions(
    filters: dict[str, str | None],
    page: int,
    per_page: int,
    sort_by: str,
    sort_order: str,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    where: list[str] = []
    params: list[Any] = []
    for column in ("anomaly_code", "severity", "status"):
        value = filters.get(column)
        if value is not None:
            where.append(f"{column} = %s")
            params.append(value)
    if date_from:
        where.append("detected_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("detected_at < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(date_to)
    if search:
        search_columns = (
            "exception_id",
            "sales_order_id",
            "invoice_id",
            "account_id",
            "payment_id",
            "dispute_id",
        )
        where.append("(" + " OR ".join(f"{column} LIKE %s" for column in search_columns) + ")")
        params.extend([f"%{search}%" for _ in search_columns])
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    count_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM exception{where_sql}",
        tuple(params),
    ) or {"total": 0}
    order_column = SORT_COLUMNS[sort_by]
    direction = "ASC" if sort_order == "asc" else "DESC"
    rows = fetch_all(
        f"""
        SELECT *
        FROM exception
        {where_sql}
        ORDER BY {order_column} {direction}, exception_id ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, (page - 1) * per_page]),
    )
    return rows, int(count_row["total"])


def get_exception(exception_id: str) -> dict[str, Any] | None:
    return fetch_one(
        "SELECT * FROM exception WHERE exception_id = %s",
        (exception_id,),
    )


def get_summary() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT anomaly_code, severity, status, COUNT(*) AS exception_count
        FROM exception
        GROUP BY anomaly_code, severity, status
        ORDER BY anomaly_code, severity, status
    """)


def update_status(exception_id: str, status: str) -> dict[str, Any] | None:
    def operation(connection: Any) -> dict[str, Any] | None:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status FROM exception WHERE exception_id = %s FOR UPDATE",
                (exception_id,),
            )
            current = cursor.fetchone()
            if current is None:
                return None
            old_status = current["status"]
            if old_status != status:
                cursor.execute(
                    """
                    UPDATE exception
                    SET status = %s,
                        resolved_at = CASE
                            WHEN %s = 'RESOLVED' THEN CURRENT_TIMESTAMP
                            ELSE NULL
                        END
                    WHERE exception_id = %s
                    """,
                    (status, status, exception_id),
                )
                cursor.execute(
                    """
                    INSERT INTO status_event (
                        entity_type, entity_id, from_status, to_status,
                        event_at, actor, note
                    )
                    VALUES ('EXCEPTION', %s, %s, %s, CURRENT_TIMESTAMP, 'API',
                            'Exception status updated through the API.')
                    """,
                    (exception_id, old_status, status),
                )
            cursor.execute(
                "SELECT * FROM exception WHERE exception_id = %s",
                (exception_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    return run_transaction(operation)
