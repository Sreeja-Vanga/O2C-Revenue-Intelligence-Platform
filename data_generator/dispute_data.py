
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


def generate_disputes():
    random.seed(RANDOM_SEED)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM dispute")
        if cursor.fetchone()["total"] > 0:
            raise ValueError(
                "Disputes already exist. Generation stopped to prevent duplicates."
            )

        cursor.execute("""
            SELECT invoice_id, account_id, invoice_date, total_amount
            FROM invoice
            ORDER BY invoice_id
        """)
        invoices = cursor.fetchall()

        if not invoices:
            print("No invoices found.")
            return

        reasons = [
            "PRICE",
            "QUANTITY",
            "DUPLICATE_BILLING",
            "TAX",
            "QUALITY",
            "SHORT_PAY",
            "OTHER"
        ]

        statuses = [
            "OPEN",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "CLOSED"
        ]

        dispute_count = 0

        for invoice in invoices:
            # Generate disputes for approximately 8% of invoices
            if random.random() > 0.08:
                continue

            dispute_count += 1
            dispute_id = f"DSP-2026-{dispute_count:06d}"

            invoice_amount = money(invoice["total_amount"])
            disputed_amount = money(
                invoice_amount * Decimal(
                    str(random.uniform(0.10, 0.50))
                )
            )

            status = random.choice(statuses)
            opened_date = invoice["invoice_date"] + timedelta(
                days=random.randint(1, 30)
            )

            resolved_date = None
            approved_credit = Decimal("0.00")

            if status in ["APPROVED", "REJECTED", "CLOSED"]:
                resolved_date = opened_date + timedelta(
                    days=random.randint(2, 20)
                )

            if status == "APPROVED":
                approved_credit = money(
                    disputed_amount * Decimal(
                        str(random.uniform(0.50, 1.00))
                    )
                )

            resolution_note = (
                "Dispute resolved after review."
                if resolved_date else None
            )

            cursor.execute("""
                INSERT INTO dispute (
                    dispute_id,
                    invoice_id,
                    account_id,
                    opened_date,
                    resolved_date,
                    reason_code,
                    disputed_amount,
                    approved_credit_amount,
                    status,
                    resolution_note
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                dispute_id,
                invoice["invoice_id"],
                invoice["account_id"],
                opened_date,
                resolved_date,
                random.choice(reasons),
                disputed_amount,
                approved_credit,
                status,
                resolution_note
            ))

        conn.commit()

        print("Dispute generation completed successfully!")
        print("Disputes created:", dispute_count)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    generate_disputes()
