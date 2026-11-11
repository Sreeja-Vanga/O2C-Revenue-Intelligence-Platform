
import random
import mysql.connector
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from config import DB_CONFIG, RANDOM_SEED

random.seed(RANDOM_SEED)

CARRIERS = [
    "DHL",
    "FedEx",
    "UPS",
    "Blue Dart",
    "Delhivery"
]


def generate_shipments():

    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        # Prevent accidental duplicate generation.
        cursor.execute("SELECT COUNT(*) AS total FROM shipment")
        existing_shipments = cursor.fetchone()["total"]

        if existing_shipments > 0:
            raise ValueError(
                f"{existing_shipments} shipments already exist. "
                "Do not run this generator again without resetting "
                "the shipment data first."
            )

        # Fetch confirmed orders.
        cursor.execute("""
            SELECT sales_order_id, order_date
            FROM sales_order
            WHERE status = 'CONFIRMED'
            ORDER BY sales_order_id
        """)

        orders = cursor.fetchall()

        if not orders:
            raise ValueError(
                "No CONFIRMED sales orders found. "
                "Generate sales orders first."
            )

        # Fetch all order lines.
        cursor.execute("""
            SELECT
                order_line_id,
                sales_order_id,
                quantity_ordered
            FROM order_line
            ORDER BY sales_order_id, line_number
        """)

        all_lines = cursor.fetchall()

        lines_by_order = {}

        for line in all_lines:
            lines_by_order.setdefault(
                line["sales_order_id"], []
            ).append(line)

        shipments = []
        shipment_lines = []
        order_updates = []

        shipment_number = 1

        for order in orders:

            order_id = order["sales_order_id"]

            order_lines = lines_by_order.get(order_id, [])

            if not order_lines:
                continue

            # Keep approximately 15% of orders unfulfilled.
            if random.random() < 0.15:
                continue

            # Decide whether the order is partially fulfilled.
            is_partial = random.random() < 0.30

            # Partial orders may have one or two shipments.
            shipment_count = 1

            if is_partial and random.random() < 0.50:
                shipment_count = 2

            shipment_id_list = []

            # Generate shipment headers first.
            for shipment_index in range(shipment_count):

                shipment_id = (
                    f"SHP-2026-{shipment_number:06d}"
                )

                tracking_number = (
                    f"TRK{shipment_number:010d}"
                )

                shipment_date = (
                    order["order_date"]
                    + timedelta(days=random.randint(1, 20))
                )

                shipment_status = random.choice([
                    "SHIPPED",
                    "DELIVERED"
                ])

                shipments.append({
                    "shipment_id": shipment_id,
                    "sales_order_id": order_id,
                    "ship_date": shipment_date,
                    "status": shipment_status,
                    "carrier": random.choice(CARRIERS),
                    "tracking_number": tracking_number
                })

                shipment_id_list.append(shipment_id)

                shipment_number += 1

            # Allocate quantities to shipment lines.
            for line in order_lines:

                ordered_qty = Decimal(
                    str(line["quantity_ordered"])
                )

                if is_partial:
                    shipped_total = (
                        ordered_qty * Decimal("0.60")
                    ).quantize(
                        Decimal("0.001"),
                        rounding=ROUND_HALF_UP
                    )

                    shipped_total = min(
                        shipped_total,
                        ordered_qty
                    )

                else:
                    shipped_total = ordered_qty

                if shipped_total <= 0:
                    continue

                # Split the shipped quantity across two shipments
                # when the order has two partial shipments.
                if shipment_count == 2:

                    first_qty = (
                        shipped_total / Decimal("2")
                    ).quantize(
                        Decimal("0.001"),
                        rounding=ROUND_HALF_UP
                    )

                    second_qty = shipped_total - first_qty

                    quantities = [
                        first_qty,
                        second_qty
                    ]

                else:
                    quantities = [shipped_total]

                for index, quantity in enumerate(quantities):

                    if quantity <= 0:
                        continue

                    shipment_lines.append({
                        "shipment_id": shipment_id_list[index],
                        "order_line_id": line["order_line_id"],
                        "quantity_shipped": quantity
                    })

            # Update order fulfillment status.
            new_status = (
                "PARTIALLY_SHIPPED"
                if is_partial
                else "SHIPPED"
            )

            order_updates.append((
                new_status,
                order_id
            ))

        # Insert all shipment records and update orders
        # within one database transaction.

        if shipments:
            cursor.executemany("""
                INSERT INTO shipment (
                    shipment_id,
                    sales_order_id,
                    ship_date,
                    status,
                    carrier,
                    tracking_number
                )
                VALUES (
                    %(shipment_id)s,
                    %(sales_order_id)s,
                    %(ship_date)s,
                    %(status)s,
                    %(carrier)s,
                    %(tracking_number)s
                )
            """, shipments)

        if shipment_lines:
            cursor.executemany("""
                INSERT INTO shipment_line (
                    shipment_id,
                    order_line_id,
                    quantity_shipped
                )
                VALUES (
                    %(shipment_id)s,
                    %(order_line_id)s,
                    %(quantity_shipped)s
                )
            """, shipment_lines)

        if order_updates:
            cursor.executemany("""
                UPDATE sales_order
                SET status = %s
                WHERE sales_order_id = %s
            """, order_updates)

        connection.commit()

        print("\nShipment generation completed successfully!")
        print("---------------------------------------------")
        print("Total orders processed:", len(orders))
        print("Total shipments created:", len(shipments))
        print("Total shipment lines created:", len(shipment_lines))
        print("Orders updated:", len(order_updates))
        print("---------------------------------------------")

    except Exception as error:

        if connection:
            connection.rollback()

        print("Shipment generation failed:", error)
        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    generate_shipments()
