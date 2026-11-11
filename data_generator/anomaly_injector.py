
import mysql.connector
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from config import DB_CONFIG
from ground_truth import save_ground_truth


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def price4(value):
    return Decimal(str(value)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP
    )


def inject_price_variance(cursor, ground_truth):

    cursor.execute("""
        SELECT
            ol.order_line_id,
            ol.sales_order_id,
            ol.quote_id,
            ol.quote_line_id,
            ol.quoted_net_unit_price,
            ol.net_unit_price,
            ol.unit_price,
            ol.discount_pct,
            ol.quantity_ordered,
            so.account_id,
            so.subtotal,
            so.total_amount
        FROM order_line ol
        JOIN sales_order so
            ON ol.sales_order_id = so.sales_order_id
        WHERE ol.quote_line_id IS NOT NULL
          AND ol.quoted_net_unit_price IS NOT NULL
          AND ol.net_unit_price = ol.quoted_net_unit_price
        ORDER BY ol.order_line_id
        LIMIT 1
        FOR UPDATE
    """)

    record = cursor.fetchone()

    if not record:
        raise ValueError("No eligible order line found.")

    old_net_price = Decimal(str(record["net_unit_price"]))
    discount_pct = Decimal(str(record["discount_pct"]))
    quantity = Decimal(str(record["quantity_ordered"]))

    # Increase the net selling price by 20%.
    new_net_price = price4(old_net_price * Decimal("1.20"))

    # Preserve the existing discount percentage.
    discount_factor = Decimal("1") - (
        discount_pct / Decimal("100")
    )

    if discount_factor <= 0:
        raise ValueError("Invalid discount percentage.")

    new_unit_price = price4(new_net_price / discount_factor)

    # Recalculate the actual net price after rounding.
    new_net_price = price4(new_unit_price * discount_factor)

    old_line_amount = money(
        quantity * old_net_price
    )

    new_line_amount = money(
        quantity * new_net_price
    )

    line_delta = new_line_amount - old_line_amount

    # Update the affected order line.
    cursor.execute("""
        UPDATE order_line
        SET unit_price = %s,
            net_unit_price = %s,
            line_amount = %s
        WHERE order_line_id = %s
    """, (
        new_unit_price,
        new_net_price,
        new_line_amount,
        record["order_line_id"]
    ))

    # Keep the parent sales order financially reconciled.
    cursor.execute("""
        UPDATE sales_order
        SET subtotal = subtotal + %s,
            total_amount = total_amount + %s
        WHERE sales_order_id = %s
    """, (
        line_delta,
        line_delta,
        record["sales_order_id"]
    ))

    expected = money(old_net_price)
    actual = money(new_net_price)
    variance = money(actual - expected)

    cursor.execute("""
        INSERT INTO exception (
            exception_id,
            anomaly_code,
            severity,
            status,
            account_id,
            quote_id,
            sales_order_id,
            order_line_id,
            expected_amount,
            actual_amount,
            variance_amount,
            description,
            detected_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
    """, (
        "EXC-2026-000001",
        "PRICE_VARIANCE",
        "HIGH",
        "OPEN",
        record["account_id"],
        record["quote_id"],
        record["sales_order_id"],
        record["order_line_id"],
        expected,
        actual,
        variance,
        "Order net unit price differs from the quoted net unit price.",
        datetime.now()
    ))

    ground_truth.append({
        "exception_id": "EXC-2026-000001",
        "anomaly_code": "PRICE_VARIANCE",
        "entity_type": "ORDER_LINE",
        "entity_id": record["order_line_id"],
        "sales_order_id": record["sales_order_id"],
        "quote_id": record["quote_id"],
        "expected_amount": expected,
        "actual_amount": actual,
        "variance_amount": variance,
        "description": "Order net unit price increased by approximately 20% compared with the quoted price."
    })

    print("PRICE_VARIANCE injected successfully!")
    print("Order line:", record["order_line_id"])
    print("Original net price:", old_net_price)
    print("Updated net price:", new_net_price)
    print("Line amount difference:", line_delta)


def inject_anomalies():

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    ground_truth = []

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM exception
            WHERE anomaly_code = 'PRICE_VARIANCE'
        """)

        if cursor.fetchone()["total"] > 0:
            raise ValueError(
                "PRICE_VARIANCE already exists. Injection stopped."
            )

        inject_price_variance(cursor, ground_truth)

        # Save database changes first.
        conn.commit()

        # Save the matching ground-truth record.
        save_ground_truth(ground_truth)

        print("\nAnomaly injection completed successfully!")

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    inject_anomalies()
