from datetime import datetime
from typing import Any

from backend.database.db import fetch_all, fetch_one, run_transaction
from backend.utils.id_generator import format_document_id


RESOURCE_CONFIG: dict[str, dict[str, Any]] = {
    "accounts": {
        "table": "account",
        "id": "account_id",
        "filters": {"account_id", "status", "currency_code"},
        "dates": {"created_at", "updated_at"},
        "search": ("account_id", "account_name"),
        "sort": {"account_id", "account_name", "status", "created_at"},
        "children": {
            "quotes": ("quote", "account_id"),
            "sales_orders": ("sales_order", "account_id"),
            "invoices": ("invoice", "account_id"),
            "payments": ("payment", "account_id"),
            "disputes": ("dispute", "account_id"),
        },
    },
    "quotes": {
        "table": "quote",
        "id": "quote_id",
        "filters": {"quote_id", "account_id", "status", "currency_code"},
        "dates": {"quote_date", "valid_until"},
        "search": ("quote_id", "account_id"),
        "sort": {"quote_id", "quote_date", "valid_until", "status", "total_amount"},
        "children": {"lines": ("quote_line", "quote_id")},
    },
    "orders": {
        "table": "sales_order",
        "id": "sales_order_id",
        "filters": {"sales_order_id", "account_id", "quote_id", "status", "currency_code"},
        "dates": {"order_date", "requested_ship_date"},
        "search": ("sales_order_id", "account_id", "quote_id"),
        "sort": {"sales_order_id", "order_date", "status", "total_amount"},
        "children": {"lines": ("order_line", "sales_order_id")},
    },
    "shipments": {
        "table": "shipment",
        "id": "shipment_id",
        "filters": {"shipment_id", "sales_order_id", "status"},
        "dates": {"ship_date"},
        "search": ("shipment_id", "sales_order_id", "tracking_number", "carrier"),
        "sort": {"shipment_id", "sales_order_id", "ship_date", "status"},
        "children": {"lines": ("shipment_line", "shipment_id")},
    },
    "invoices": {
        "table": "invoice",
        "id": "invoice_id",
        "filters": {"invoice_id", "account_id", "sales_order_id", "status", "currency_code"},
        "dates": {"invoice_date", "due_date"},
        "search": ("invoice_id", "account_id", "sales_order_id"),
        "sort": {"invoice_id", "invoice_date", "due_date", "status", "total_amount", "open_amount"},
        "children": {"lines": ("invoice_line", "invoice_id")},
    },
    "payments": {
        "table": "payment",
        "id": "payment_id",
        "filters": {"payment_id", "account_id", "status", "method", "currency_code"},
        "dates": {"payment_date"},
        "search": ("payment_id", "account_id", "reference_number"),
        "sort": {"payment_id", "payment_date", "status", "amount"},
        "children": {"allocations": ("payment_allocation", "payment_id")},
    },
    "disputes": {
        "table": "dispute",
        "id": "dispute_id",
        "filters": {"dispute_id", "invoice_id", "account_id", "status", "reason_code"},
        "dates": {"opened_date", "resolved_date"},
        "search": ("dispute_id", "invoice_id", "account_id", "reason_code"),
        "sort": {"dispute_id", "opened_date", "status", "disputed_amount", "approved_credit_amount"},
        "children": {},
    },
    "events": {
        "table": "status_event",
        "id": "status_event_id",
        "filters": {"entity_type", "entity_id", "from_status", "to_status", "actor"},
        "dates": {"event_at"},
        "search": ("entity_id", "actor", "note"),
        "sort": {"status_event_id", "entity_type", "entity_id", "event_at", "to_status"},
        "children": {},
    },
}

DOCUMENT_PREFIX = {
    "accounts": "ACC",
    "quotes": "QTE",
    "orders": "SO",
    "shipments": "SHP",
    "invoices": "INV",
    "payments": "PAY",
    "disputes": "DSP",
}
STATUS_ENTITY = {
    "accounts": "ACCOUNT",
    "quotes": "QUOTE",
    "orders": "SALES_ORDER",
    "shipments": "SHIPMENT",
    "invoices": "INVOICE",
    "payments": "PAYMENT",
    "disputes": "DISPUTE",
}


def _column_metadata(cursor: Any, resource: str) -> list[dict[str, Any]]:
    config = RESOURCE_CONFIG[resource]
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE,
               COLUMN_DEFAULT, EXTRA, COLUMN_KEY
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (config["table"],),
    )
    columns = cursor.fetchall()
    id_column = config["id"]
    return [
        {
            "name": column["COLUMN_NAME"],
            "data_type": column["DATA_TYPE"],
            "column_type": column["COLUMN_TYPE"],
            "nullable": column["IS_NULLABLE"] == "YES",
            "default": column["COLUMN_DEFAULT"],
            "generated": "GENERATED" in (column["EXTRA"] or "").upper(),
            "auto_increment": "auto_increment" in (column["EXTRA"] or "").lower(),
            "primary_key": column["COLUMN_KEY"] == "PRI",
            "writable": (
                column["COLUMN_NAME"] != id_column
                and column["COLUMN_NAME"] not in {"created_at", "updated_at"}
                and "GENERATED" not in (column["EXTRA"] or "").upper()
                and "auto_increment" not in (column["EXTRA"] or "").lower()
            ),
            "required": (
                column["IS_NULLABLE"] == "NO"
                and column["COLUMN_DEFAULT"] is None
                and "auto_increment" not in (column["EXTRA"] or "").lower()
                and "GENERATED" not in (column["EXTRA"] or "").upper()
            ),
        }
        for column in columns
    ]


def get_resource_schema(resource: str) -> dict[str, Any]:
    if resource not in RESOURCE_CONFIG:
        raise ValueError("Unsupported transaction resource.")
    from backend.database.db import connection_manager

    with connection_manager() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            return {
                "resource": resource,
                "id_field": RESOURCE_CONFIG[resource]["id"],
                "append_only": resource == "events",
                "fields": _column_metadata(cursor, resource),
            }
        finally:
            cursor.close()


def create_record(resource: str, values: dict[str, Any]) -> str:
    if resource not in RESOURCE_CONFIG:
        raise ValueError("This resource cannot be created through transaction management.")
    if not values:
        raise ValueError("Provide at least one field to create the record.")
    config = RESOURCE_CONFIG[resource]

    def insert(connection: Any) -> str:
        cursor = connection.cursor(dictionary=True)
        try:
            columns = _column_metadata(cursor, resource)
            writable = {column["name"] for column in columns if column["writable"]}
            unknown = set(values) - writable
            if unknown:
                raise ValueError(f"Unsupported field(s): {', '.join(sorted(unknown))}.")
            record_id = None
            lock_name = None
            if resource == "events":
                insert_values = values
            else:
                record_id, lock_name = _next_document_id(cursor, resource)
                insert_values = {config["id"]: record_id, **values}
            names = list(insert_values)
            sql = (
                f"INSERT INTO `{config['table']}` "
                f"({', '.join(f'`{name}`' for name in names)}) "
                f"VALUES ({', '.join(['%s'] * len(names))})"
            )
            try:
                cursor.execute(sql, tuple(insert_values[name] for name in names))
                return str(cursor.lastrowid) if resource == "events" else str(record_id)
            finally:
                if lock_name:
                    cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        finally:
            cursor.close()

    return run_transaction(insert)


def update_record(resource: str, record_id: str, values: dict[str, Any]) -> bool:
    if resource not in RESOURCE_CONFIG:
        raise ValueError("Unsupported transaction resource.")
    if resource == "events":
        raise ValueError("Status events are append-only and cannot be updated.")
    if not values:
        raise ValueError("Provide at least one field to update.")
    config = RESOURCE_CONFIG[resource]

    def update(connection: Any) -> bool:
        cursor = connection.cursor(dictionary=True)
        try:
            columns = _column_metadata(cursor, resource)
            writable = {column["name"] for column in columns if column["writable"]}
            unknown = set(values) - writable
            if unknown:
                raise ValueError(f"Unsupported field(s): {', '.join(sorted(unknown))}.")
            cursor.execute(
                f"SELECT * FROM `{config['table']}` WHERE `{config['id']}` = %s FOR UPDATE",
                (record_id,),
            )
            previous = cursor.fetchone()
            if previous is None:
                return False
            assignments = ", ".join(f"`{name}` = %s" for name in values)
            cursor.execute(
                f"UPDATE `{config['table']}` SET {assignments} "
                f"WHERE `{config['id']}` = %s",
                (*values.values(), record_id),
            )
            new_status = values.get("status")
            old_status = previous.get("status")
            if (
                new_status is not None
                and old_status != new_status
                and resource in STATUS_ENTITY
            ):
                cursor.execute(
                    """
                    INSERT INTO status_event
                        (entity_type, entity_id, from_status, to_status, event_at, actor, note)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
                    """,
                    (
                        STATUS_ENTITY[resource],
                        record_id,
                        old_status,
                        new_status,
                        "APPLICATION",
                        "Status updated through transaction management.",
                    ),
                )
            return True
        finally:
            cursor.close()

    return run_transaction(update)


def delete_record(resource: str, record_id: str) -> bool:
    if resource not in RESOURCE_CONFIG:
        raise ValueError("Unsupported transaction resource.")
    if resource == "events":
        raise ValueError("Status events are append-only and cannot be deleted.")
    config = RESOURCE_CONFIG[resource]

    def delete(connection: Any) -> bool:
        cursor = connection.cursor(dictionary=True)
        try:
            entity_type = STATUS_ENTITY.get(resource)
            if entity_type:
                cursor.execute(
                    "SELECT COUNT(*) AS event_count FROM status_event "
                    "WHERE entity_type = %s AND entity_id = %s",
                    (entity_type, record_id),
                )
                if cursor.fetchone()["event_count"]:
                    raise ValueError("Records with status history cannot be deleted.")
            cursor.execute(
                f"DELETE FROM `{config['table']}` WHERE `{config['id']}` = %s",
                (record_id,),
            )
            return cursor.rowcount > 0
        finally:
            cursor.close()

    return run_transaction(delete)


def _next_document_id(cursor: Any, resource: str) -> tuple[str, str]:
    prefix = DOCUMENT_PREFIX[resource]
    year = datetime.now().year
    lock_name = f"o2c:{resource}:{year}"
    cursor.execute("SELECT GET_LOCK(%s, 10) AS acquired", (lock_name,))
    if cursor.fetchone()["acquired"] != 1:
        raise ValueError("Could not reserve a document ID; retry the operation.")
    config = RESOURCE_CONFIG[resource]
    cursor.execute(
        f"""
        SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(`{config['id']}`, '-', -1)
            AS UNSIGNED)), 0) AS last_sequence
        FROM `{config['table']}`
        WHERE `{config['id']}` LIKE %s
        """,
        (f"{prefix}-{year}-%",),
    )
    sequence = int(cursor.fetchone()["last_sequence"]) + 1
    return format_document_id(prefix, year, sequence), lock_name


def list_records(
    resource: str,
    filters: dict[str, str],
    page: int,
    per_page: int,
    sort_by: str,
    sort_order: str,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    config = RESOURCE_CONFIG[resource]
    table = config["table"]
    allowed_filters = config["filters"]
    where: list[str] = []
    params: list[Any] = []
    for column, value in filters.items():
        if column in allowed_filters and value:
            where.append(f"`{column}` = %s")
            params.append(value)
    date_columns = config["dates"]
    if date_from or date_to:
        date_column = next(
            (column for column in ("event_at", "invoice_date", "payment_date",
                                   "order_date", "ship_date", "opened_date",
                                   "quote_date", "created_at") if column in date_columns),
            None,
        )
        if date_column is None:
            raise ValueError(f"Date filtering is not supported for {resource}.")
        if date_from:
            where.append(f"`{date_column}` >= %s")
            params.append(date_from)
        if date_to:
            where.append(f"`{date_column}` < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(date_to)
    if search:
        searchable_columns = config["search"]
        where.append("(" + " OR ".join(f"`{column}` LIKE %s" for column in searchable_columns) + ")")
        params.extend([f"%{search}%" for _ in searchable_columns])
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    count = fetch_one(
        f"SELECT COUNT(*) AS total FROM `{table}`{where_sql}",
        tuple(params),
    ) or {"total": 0}
    sort_column = sort_by if sort_by in config["sort"] else config["id"]
    direction = "ASC" if sort_order == "asc" else "DESC"
    rows = fetch_all(
        f"""
        SELECT * FROM `{table}`{where_sql}
        ORDER BY `{sort_column}` {direction}, `{config['id']}` ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, (page - 1) * per_page]),
    )
    return rows, int(count["total"])


def get_record(resource: str, record_id: str) -> dict[str, Any] | None:
    config = RESOURCE_CONFIG[resource]
    record = fetch_one(
        f"SELECT * FROM `{config['table']}` WHERE `{config['id']}` = %s",
        (record_id,),
    )
    if record is None:
        return None
    for name, (table, key) in config["children"].items():
        record[name] = fetch_all(
            f"SELECT * FROM `{table}` WHERE `{key}` = %s ORDER BY 1",
            (record_id,),
        )
    return record


def get_related_exception_records(exception_id: str) -> dict[str, Any] | None:
    exception = fetch_one(
        "SELECT * FROM exception WHERE exception_id = %s",
        (exception_id,),
    )
    if exception is None:
        return None
    related = {
        "account": ("account", "account_id", exception.get("account_id")),
        "quote": ("quote", "quote_id", exception.get("quote_id")),
        "sales_order": ("sales_order", "sales_order_id", exception.get("sales_order_id")),
        "shipment": ("shipment", "shipment_id", exception.get("shipment_id")),
        "invoice": ("invoice", "invoice_id", exception.get("invoice_id")),
        "payment": ("payment", "payment_id", exception.get("payment_id")),
        "dispute": ("dispute", "dispute_id", exception.get("dispute_id")),
        "order_line": ("order_line", "order_line_id", exception.get("order_line_id")),
        "shipment_line": ("shipment_line", "shipment_line_id", exception.get("shipment_line_id")),
        "invoice_line": ("invoice_line", "invoice_line_id", exception.get("invoice_line_id")),
    }
    source: dict[str, Any] = {"exception": exception}
    for name, (table, column, value) in related.items():
        source[name] = (
            fetch_one(f"SELECT * FROM `{table}` WHERE `{column}` = %s", (value,))
            if value is not None
            else None
        )
    return source


def get_price_variances() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            ol.order_line_id, ol.sales_order_id, so.account_id,
            ol.quote_line_id, ql.quote_id, ol.product_code,
            ol.quantity_ordered, ql.net_unit_price AS quoted_net_unit_price,
            ol.net_unit_price
        FROM order_line ol
        JOIN quote_line ql ON ql.quote_line_id = ol.quote_line_id
        JOIN sales_order so ON so.sales_order_id = ol.sales_order_id
        WHERE ol.net_unit_price <> ql.net_unit_price
        ORDER BY ol.order_line_id
    """)


def get_shipment_overages() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            ol.order_line_id, ol.sales_order_id, so.account_id,
            ol.product_code, ol.quantity_ordered,
            COALESCE(SUM(sl.quantity_shipped), 0) AS quantity_shipped,
            MAX(ol.net_unit_price) AS net_unit_price,
            MIN(sl.shipment_line_id) AS representative_shipment_line_id,
            GROUP_CONCAT(sl.shipment_line_id ORDER BY sl.shipment_line_id)
                AS shipment_line_ids
        FROM order_line ol
        JOIN sales_order so ON so.sales_order_id = ol.sales_order_id
        LEFT JOIN shipment_line sl ON sl.order_line_id = ol.order_line_id
        GROUP BY ol.order_line_id, ol.sales_order_id, so.account_id,
                 ol.product_code, ol.quantity_ordered
        HAVING COALESCE(SUM(sl.quantity_shipped), 0) > ol.quantity_ordered
        ORDER BY ol.order_line_id
    """)


def get_billing_overages() -> list[dict[str, Any]]:
    shipped_lines = fetch_all("""
        SELECT
            'INVOICE_LINE' AS entity_type,
            MIN(il.invoice_line_id) AS entity_id,
            'SHIPPED' AS comparison_type,
            sl.shipment_line_id,
            sl.order_line_id, ol.sales_order_id, so.account_id,
            sl.quantity_shipped AS expected_quantity,
            SUM(il.quantity) AS actual_quantity,
            SUM(il.line_amount) AS billed_amount,
            GROUP_CONCAT(DISTINCT il.invoice_id ORDER BY il.invoice_id)
                AS invoice_ids,
            GROUP_CONCAT(il.invoice_line_id ORDER BY il.invoice_line_id)
                AS invoice_line_ids
        FROM shipment_line sl
        JOIN order_line ol ON ol.order_line_id = sl.order_line_id
        JOIN sales_order so ON so.sales_order_id = ol.sales_order_id
        JOIN invoice_line il ON il.shipment_line_id = sl.shipment_line_id
        GROUP BY sl.shipment_line_id, sl.order_line_id, ol.sales_order_id,
                 so.account_id, sl.quantity_shipped
        HAVING SUM(il.quantity) > sl.quantity_shipped
        ORDER BY sl.shipment_line_id
    """)
    unshipped_lines = fetch_all("""
        SELECT
            'INVOICE_LINE' AS entity_type,
            MIN(il.invoice_line_id) AS entity_id,
            'UNSHIPPED' AS comparison_type,
            NULL AS shipment_line_id,
            il.order_line_id, ol.sales_order_id, so.account_id,
            0 AS expected_quantity,
            SUM(il.quantity) AS actual_quantity,
            SUM(il.line_amount) AS billed_amount,
            GROUP_CONCAT(DISTINCT il.invoice_id ORDER BY il.invoice_id)
                AS invoice_ids,
            GROUP_CONCAT(il.invoice_line_id ORDER BY il.invoice_line_id)
                AS invoice_line_ids
        FROM invoice_line il
        JOIN order_line ol ON ol.order_line_id = il.order_line_id
        JOIN sales_order so ON so.sales_order_id = ol.sales_order_id
        WHERE il.shipment_line_id IS NULL
        GROUP BY il.order_line_id, ol.sales_order_id, so.account_id
        HAVING SUM(il.quantity) > 0
        ORDER BY il.order_line_id
    """)
    return shipped_lines + unshipped_lines


def get_payment_application_errors() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            p.payment_id, p.account_id, p.amount,
            p.unapplied_amount,
            COALESCE(SUM(pa.allocated_amount), 0) AS allocated_amount,
            GROUP_CONCAT(pa.allocation_id ORDER BY pa.allocation_id)
                AS allocation_ids
        FROM payment p
        LEFT JOIN payment_allocation pa ON pa.payment_id = p.payment_id
        WHERE p.status <> 'VOID'
        GROUP BY p.payment_id, p.account_id, p.amount, p.unapplied_amount
        HAVING COALESCE(SUM(pa.allocated_amount), 0) > p.amount
            OR ABS(
                p.amount - COALESCE(SUM(pa.allocated_amount), 0)
                - p.unapplied_amount
            ) > 0.01
        ORDER BY p.payment_id
    """)


def get_unapplied_dispute_credits() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            d.invoice_id, i.account_id,
            SUM(d.approved_credit_amount) AS approved_credit_amount,
            i.credit_amount,
            GROUP_CONCAT(d.dispute_id ORDER BY d.dispute_id) AS dispute_ids
        FROM dispute d
        JOIN invoice i ON i.invoice_id = d.invoice_id
        WHERE d.status = 'APPROVED'
        GROUP BY d.invoice_id, i.account_id, i.credit_amount
        HAVING SUM(d.approved_credit_amount) > i.credit_amount
        ORDER BY d.invoice_id
    """)


def get_closed_unpaid_orders() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            so.sales_order_id, so.account_id,
            SUM(GREATEST(i.open_amount, 0)) AS outstanding_amount,
            GROUP_CONCAT(i.invoice_id ORDER BY i.invoice_id) AS invoice_ids
        FROM sales_order so
        JOIN invoice i ON i.sales_order_id = so.sales_order_id
        WHERE so.status = 'CLOSED'
        GROUP BY so.sales_order_id, so.account_id
        HAVING SUM(GREATEST(i.open_amount, 0)) > 0
        ORDER BY so.sales_order_id
    """)


def get_skipped_order_transitions() -> list[dict[str, Any]]:
    return fetch_all("""
        SELECT
            status_event_id, entity_id AS sales_order_id,
            from_status, to_status, event_at, actor, note
        FROM status_event
        WHERE entity_type = 'SALES_ORDER'
          AND from_status = 'SHIPPED'
          AND to_status = 'CLOSED'
        ORDER BY event_at, status_event_id
    """)
