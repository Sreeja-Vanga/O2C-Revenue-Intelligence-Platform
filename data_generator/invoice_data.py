
import random
import mysql.connector
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from config import DB_CONFIG, RANDOM_SEED


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_invoices():
    random.seed(RANDOM_SEED)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        # Prevent accidental duplicate generation
        cursor.execute("SELECT COUNT(*) AS total FROM invoice")
        if cursor.fetchone()["total"] > 0:
            raise ValueError(
                "Invoices already exist. Generation stopped to prevent duplicates."
            )

        # Get shipment lines with their corresponding order details
        cursor.execute("""
            SELECT
                s.shipment_id,
                s.sales_order_id,
                s.ship_date,
                so.account_id,
                so.currency_code,
                sl.shipment_line_id,
                sl.order_line_id,
                sl.quantity_shipped,
                ol.product_code,
                ol.product_name,
                ol.net_unit_price
            FROM shipment s
            JOIN sales_order so
                ON s.sales_order_id = so.sales_order_id
            JOIN shipment_line sl
                ON s.shipment_id = sl.shipment_id
            JOIN order_line ol
                ON sl.order_line_id = ol.order_line_id
                AND ol.sales_order_id = so.sales_order_id
            WHERE s.status IN ('SHIPPED', 'DELIVERED')
            ORDER BY s.ship_date, s.shipment_id
        """)

        shipment_lines = cursor.fetchall()

        if not shipment_lines:
            print("No eligible shipped quantities found.")
            return

        # Group shipment lines by shipment
        shipments = {}

        for line in shipment_lines:
            shipment_id = line["shipment_id"]
            shipments.setdefault(shipment_id, []).append(line)

        invoice_count = 0
        invoice_line_count = 0

        for shipment_id, lines in shipments.items():

            first = lines[0]

            invoice_id = f"INV-2026-{invoice_count + 1:06d}"

            invoice_date = first["ship_date"]
            payment_terms = 30
            due_date = invoice_date + timedelta(days=payment_terms)

            subtotal = Decimal("0.00")

            prepared_lines = []

            for index, line in enumerate(lines, start=1):

                quantity = Decimal(str(line["quantity_shipped"]))
                unit_price = Decimal(str(line["net_unit_price"]))

                line_amount = money(quantity * unit_price)
                subtotal += line_amount

                prepared_lines.append({
                    "order_line_id": line["order_line_id"],
                    "shipment_line_id": line["shipment_line_id"],
                    "line_number": index,
                    "product_code": line["product_code"],
                    "product_name": line["product_name"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_amount": line_amount
                })

            subtotal = money(subtotal)
            discount_amount = Decimal("0.00")
            tax_amount = money(subtotal * Decimal("0.10"))
            total_amount = money(subtotal + tax_amount)

            invoice_status = "ISSUED"

            # Payment figures are initialized to zero.
            # Payment generation will update these later.
            cursor.execute("""
                INSERT INTO invoice (
                    invoice_id,
                    account_id,
                    sales_order_id,
                    invoice_date,
                    due_date,
                    payment_terms_days,
                    status,
                    currency_code,
                    subtotal,
                    discount_amount,
                    tax_amount,
                    total_amount,
                    amount_paid,
                    credit_amount
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                invoice_id,
                first["account_id"],
                first["sales_order_id"],
                invoice_date,
                due_date,
                payment_terms,
                invoice_status,
                first["currency_code"],
                subtotal,
                discount_amount,
                tax_amount,
                total_amount,
                Decimal("0.00"),
                Decimal("0.00")
            ))

            for item in prepared_lines:
                cursor.execute("""
                    INSERT INTO invoice_line (
                        invoice_id,
                        order_line_id,
                        shipment_line_id,
                        line_number,
                        product_code,
                        product_name,
                        quantity,
                        unit_price,
                        line_amount
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    invoice_id,
                    item["order_line_id"],
                    item["shipment_line_id"],
                    item["line_number"],
                    item["product_code"],
                    item["product_name"],
                    item["quantity"],
                    item["unit_price"],
                    item["line_amount"]
                ))

                invoice_line_count += 1

            invoice_count += 1

        conn.commit()

        print("Invoice generation completed successfully!")
        print("Invoices created:", invoice_count)
        print("Invoice lines created:", invoice_line_count)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    generate_invoices()
