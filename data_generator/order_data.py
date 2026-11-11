
import os
import random
import mysql.connector
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from config import DB_CONFIG, RANDOM_SEED

random.seed(RANDOM_SEED)

ORDER_COUNT = int(os.getenv("ORDER_COUNT", "700"))

PRODUCTS = [
    ("PRD-001", "Enterprise Software License"),
    ("PRD-002", "Cloud Infrastructure Service"),
    ("PRD-003", "Data Analytics Platform"),
    ("PRD-004", "IT Consulting Service"),
    ("PRD-005", "Cybersecurity Package"),
    ("PRD-006", "Network Equipment"),
    ("PRD-007", "Technical Support Package"),
    ("PRD-008", "Business Intelligence Tool")
]


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_direct_lines(order_id):
    """Generate order lines for orders without an associated quote."""

    lines = []
    line_count = random.randint(1, 4)

    for number in range(1, line_count + 1):

        code, name = random.choice(PRODUCTS)

        quantity = Decimal(random.randint(1, 20))

        unit_price = (
            Decimal(random.randint(5000, 100000))
            / Decimal("100")
        )

        discount = Decimal(
            random.choice([0, 5, 10, 15])
        )

        net_price = (
            unit_price *
            (Decimal("1") - discount / Decimal("100"))
        ).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP
        )

        line_amount = money(quantity * net_price)

        lines.append({
            "sales_order_id": order_id,
            "quote_line_id": None,
            "line_number": number,
            "product_code": code,
            "product_name": name,
            "quantity_ordered": quantity,
            "unit_price": unit_price,
            "discount_pct": discount,
            "net_unit_price": net_price,
            "quoted_net_unit_price": None,
            "line_amount": line_amount
        })

    return lines


def generate_order_records():

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    try:

        # -------------------------------------------------
        # STEP 1: Fetch valid approved quotes
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                q.quote_id,
                q.account_id,
                q.quote_date,
                q.currency_code
            FROM quote q
            JOIN account a
                ON q.account_id = a.account_id
            WHERE q.status = 'APPROVED'
              AND q.valid_until >= CURDATE()
              AND a.status = 'ACTIVE'
            ORDER BY q.quote_id
        """)

        approved_quotes = cursor.fetchall()

        if len(approved_quotes) > ORDER_COUNT:
            raise ValueError(
                "Approved quote count exceeds the order target."
            )

        # -------------------------------------------------
        # STEP 2: Fetch quote lines
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                quote_line_id,
                quote_id,
                line_number,
                product_code,
                product_name,
                quantity,
                unit_price,
                discount_pct,
                net_unit_price,
                line_amount
            FROM quote_line
            ORDER BY quote_id, line_number
        """)

        all_quote_lines = cursor.fetchall()

        quote_line_map = {}

        for line in all_quote_lines:

            quote_line_map.setdefault(
                line["quote_id"], []
            ).append(line)

        orders = []
        order_lines = []

        # -------------------------------------------------
        # STEP 3: Convert approved quotes into sales orders
        # -------------------------------------------------

        for index, quote in enumerate(
            approved_quotes,
            start=1
        ):

            order_id = f"SO-2026-{index:06d}"

            lines = quote_line_map.get(
                quote["quote_id"], []
            )

            if not lines:
                raise ValueError(
                    f"No quote lines found for {quote['quote_id']}"
                )

            subtotal = money(sum(
                (
                    Decimal(str(line["line_amount"]))
                    for line in lines
                ),
                Decimal("0.00")
            ))

            tax = money(subtotal * Decimal("0.08"))

            discount_amount = Decimal("0.00")

            total = money(subtotal + tax)

            order_date = quote["quote_date"]

            orders.append({
                "sales_order_id": order_id,
                "account_id": quote["account_id"],
                "quote_id": quote["quote_id"],
                "order_date": order_date,
                "requested_ship_date": (
                    order_date + timedelta(days=14)
                ),
                "status": "CONFIRMED",
                "currency_code": quote["currency_code"],
                "subtotal": subtotal,
                "discount_amount": discount_amount,
                "tax_amount": tax,
                "total_amount": total
            })

            for line in lines:

                order_lines.append({
                    "sales_order_id": order_id,
                    "quote_line_id": line["quote_line_id"],
                    "line_number": line["line_number"],
                    "product_code": line["product_code"],
                    "product_name": line["product_name"],
                    "quantity_ordered": line["quantity"],
                    "unit_price": line["unit_price"],
                    "discount_pct": line["discount_pct"],
                    "net_unit_price": line["net_unit_price"],
                    "quoted_net_unit_price": line["net_unit_price"],
                    "line_amount": line["line_amount"]
                })

        # -------------------------------------------------
        # STEP 4: Generate direct orders without quotes
        # -------------------------------------------------

        direct_count = ORDER_COUNT - len(approved_quotes)

        accounts = []

        if direct_count > 0:

            cursor.execute("""
                SELECT account_id
                FROM account
                WHERE status = 'ACTIVE'
                ORDER BY account_id
            """)

            accounts = cursor.fetchall()

            if not accounts:
                raise ValueError(
                    "No active accounts found for direct orders."
                )

        for index in range(
            len(approved_quotes) + 1,
            ORDER_COUNT + 1
        ):

            order_id = f"SO-2026-{index:06d}"

            account = random.choice(accounts)

            order_date = date.today() - timedelta(
                days=random.randint(1, 120)
            )

            lines = generate_direct_lines(order_id)

            subtotal = money(sum(
                (
                    line["line_amount"]
                    for line in lines
                ),
                Decimal("0.00")
            ))

            tax = money(subtotal * Decimal("0.08"))

            total = money(subtotal + tax)

            orders.append({
                "sales_order_id": order_id,
                "account_id": account["account_id"],
                "quote_id": None,
                "order_date": order_date,
                "requested_ship_date": (
                    order_date + timedelta(days=14)
                ),
                "status": "CONFIRMED",
                "currency_code": "USD",
                "subtotal": subtotal,
                "discount_amount": Decimal("0.00"),
                "tax_amount": tax,
                "total_amount": total
            })

            order_lines.extend(lines)

        return (
            orders,
            order_lines,
            len(approved_quotes),
            direct_count
        )

    finally:
        cursor.close()
        connection.close()


def insert_order_records(orders, order_lines):

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # STEP 5: Insert sales orders
        # -------------------------------------------------

        order_query = """
            INSERT INTO sales_order (
                sales_order_id,
                account_id,
                quote_id,
                order_date,
                requested_ship_date,
                status,
                currency_code,
                subtotal,
                discount_amount,
                tax_amount,
                total_amount
            )
            VALUES (
                %(sales_order_id)s,
                %(account_id)s,
                %(quote_id)s,
                %(order_date)s,
                %(requested_ship_date)s,
                %(status)s,
                %(currency_code)s,
                %(subtotal)s,
                %(discount_amount)s,
                %(tax_amount)s,
                %(total_amount)s
            )
        """

        # -------------------------------------------------
        # STEP 6: Insert order lines
        # -------------------------------------------------

        line_query = """
            INSERT INTO order_line (
                sales_order_id,
                quote_line_id,
                line_number,
                product_code,
                product_name,
                quantity_ordered,
                unit_price,
                discount_pct,
                net_unit_price,
                quoted_net_unit_price,
                line_amount
            )
            VALUES (
                %(sales_order_id)s,
                %(quote_line_id)s,
                %(line_number)s,
                %(product_code)s,
                %(product_name)s,
                %(quantity_ordered)s,
                %(unit_price)s,
                %(discount_pct)s,
                %(net_unit_price)s,
                %(quoted_net_unit_price)s,
                %(line_amount)s
            )
        """

        cursor.executemany(order_query, orders)

        cursor.executemany(line_query, order_lines)

        connection.commit()

        print("\nSales order generation completed.")

        print(
            f"Successfully inserted {len(orders)} sales orders."
        )

        print(
            f"Successfully inserted {len(order_lines)} order lines."
        )

    except Exception as error:

        connection.rollback()

        print("Order insertion failed:", error)

        raise

    finally:

        cursor.close()
        connection.close()


# -------------------------------------------------
# MAIN EXECUTION
# -------------------------------------------------

if __name__ == "__main__":

    orders, lines, quote_count, direct_count = (
        generate_order_records()
    )

    print("\nPrepared sales orders:")

    print("Quote-based orders:", quote_count)

    print("Direct orders:", direct_count)

    print("Total orders:", len(orders))

    insert_order_records(orders, lines)
