
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


def generate_payments():
    random.seed(RANDOM_SEED)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM payment")
        if cursor.fetchone()["total"] > 0:
            raise ValueError(
                "Payments already exist. Generation stopped to prevent duplicates."
            )

        cursor.execute("""
            SELECT
                invoice_id,
                account_id,
                invoice_date,
                due_date,
                total_amount
            FROM invoice
            WHERE status = 'ISSUED'
            ORDER BY invoice_id
        """)

        invoices = cursor.fetchall()

        if not invoices:
            print("No eligible invoices found.")
            return

        payment_count = 0
        allocation_count = 0

        methods = ["ACH", "WIRE", "CHECK", "CARD"]

        for invoice in invoices:

            # Not every invoice receives a payment
            if random.random() > 0.70:
                continue

            total_amount = money(invoice["total_amount"])

            # Some invoices receive full payment; others partial payment
            if random.random() < 0.65:
                allocated_amount = total_amount
            else:
                percentage = Decimal(
                    str(random.uniform(0.25, 0.80))
                )
                allocated_amount = money(total_amount * percentage)

            if allocated_amount <= 0:
                continue

            payment_id = f"PAY-2026-{payment_count + 1:06d}"

            payment_date = invoice["invoice_date"] + timedelta(
                days=random.randint(5, 45)
            )

            method = random.choice(methods)
            reference_number = f"REF-{payment_id}"

            # One payment is allocated to one invoice in baseline data
            cursor.execute("""
                INSERT INTO payment (
                    payment_id,
                    account_id,
                    payment_date,
                    amount,
                    unapplied_amount,
                    method,
                    reference_number,
                    status,
                    currency_code
                )
                SELECT
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    i.currency_code
                FROM invoice i
                WHERE i.invoice_id = %s
            """, (
                payment_id,
                invoice["account_id"],
                payment_date,
                allocated_amount,
                Decimal("0.00"),
                method,
                reference_number,
                "APPLIED",
                invoice["invoice_id"]
            ))

            cursor.execute("""
                INSERT INTO payment_allocation (
                    payment_id,
                    invoice_id,
                    allocated_amount
                )
                VALUES (%s, %s, %s)
            """, (
                payment_id,
                invoice["invoice_id"],
                allocated_amount
            ))

            new_amount_paid = allocated_amount

            new_status = (
                "PAID"
                if new_amount_paid >= total_amount
                else "PARTIALLY_PAID"
            )

            cursor.execute("""
                UPDATE invoice
                SET amount_paid = %s,
                    status = %s
                WHERE invoice_id = %s
            """, (
                new_amount_paid,
                new_status,
                invoice["invoice_id"]
            ))

            payment_count += 1
            allocation_count += 1

        conn.commit()

        print("Payment generation completed successfully!")
        print("Payments created:", payment_count)
        print("Payment allocations created:", allocation_count)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    generate_payments()
