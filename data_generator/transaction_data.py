
import random
import mysql.connector
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from config import DB_CONFIG, QUOTE_COUNT, RANDOM_SEED

random.seed(RANDOM_SEED)

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
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_quotes(accounts, count=QUOTE_COUNT):
    quotes = []
    quote_lines = []

    for i in range(1, count + 1):

        quote_id = f"QTE-2026-{i:06d}"
        account = random.choice(accounts)

        quote_date = date.today() - timedelta(
            days=random.randint(1, 180)
        )

        valid_until = quote_date + timedelta(days=30)

        if valid_until < date.today():
            status = random.choices(
                ["EXPIRED", "APPROVED", "REJECTED"],
                weights=[70, 20, 10]
            )[0]
        else:
            status = random.choice(
                ["DRAFT", "OPEN", "APPROVED", "REJECTED"]
            )

        line_count = random.randint(1, 4)
        subtotal = Decimal("0.00")

        current_quote_lines = []

        for line_number in range(1, line_count + 1):

            product_code, product_name = random.choice(PRODUCTS)

            quantity = Decimal(
                str(random.randint(1, 20))
            )

            unit_price = Decimal(
                str(random.randint(5000, 100000))
            ) / Decimal("100")

            discount_pct = Decimal(
                str(random.choice([0, 5, 10, 15, 20]))
            )

            net_unit_price = (
                unit_price * (Decimal("1") - discount_pct / Decimal("100"))
            ).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP
            )

            line_amount = money(quantity * net_unit_price)

            subtotal += line_amount

            current_quote_lines.append({
                "quote_id": quote_id,
                "line_number": line_number,
                "product_code": product_code,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "net_unit_price": net_unit_price,
                "line_amount": line_amount
            })

        subtotal = money(subtotal)
        discount_amount = Decimal("0.00")
        tax_amount = money(subtotal * Decimal("0.08"))
        total_amount = money(
            subtotal - discount_amount + tax_amount
        )

        quotes.append({
            "quote_id": quote_id,
            "account_id": account["account_id"],
            "quote_date": quote_date,
            "valid_until": valid_until,
            "status": status,
            "currency_code": "USD",
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "total_amount": total_amount
        })

        quote_lines.extend(current_quote_lines)

    return quotes, quote_lines


def insert_quotes(quotes, quote_lines):

    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        quote_query = """
            INSERT INTO quote (
                quote_id, account_id, quote_date, valid_until,
                status, currency_code, subtotal,
                discount_amount, tax_amount, total_amount
            )
            VALUES (
                %(quote_id)s, %(account_id)s, %(quote_date)s,
                %(valid_until)s, %(status)s, %(currency_code)s,
                %(subtotal)s, %(discount_amount)s,
                %(tax_amount)s, %(total_amount)s
            )
        """

        line_query = """
            INSERT INTO quote_line (
                quote_id, line_number, product_code, product_name,
                quantity, unit_price, discount_pct,
                net_unit_price, line_amount
            )
            VALUES (
                %(quote_id)s, %(line_number)s, %(product_code)s,
                %(product_name)s, %(quantity)s, %(unit_price)s,
                %(discount_pct)s, %(net_unit_price)s, %(line_amount)s
            )
        """

        cursor.executemany(quote_query, quotes)
        cursor.executemany(line_query, quote_lines)

        connection.commit()

        print(f"Successfully inserted {len(quotes)} quotes.")
        print(f"Successfully inserted {len(quote_lines)} quote lines.")

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        print("Database error:", error)
        raise

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def run_quote_generation():

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
        "SELECT account_id FROM account "
        "WHERE status = 'ACTIVE' ORDER BY account_id"
        )
        accounts = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    if not accounts:
        raise ValueError("No accounts found. Generate accounts first.")

    quotes, quote_lines = generate_quotes(accounts)
    insert_quotes(quotes, quote_lines)


if __name__ == "__main__":
    run_quote_generation()
