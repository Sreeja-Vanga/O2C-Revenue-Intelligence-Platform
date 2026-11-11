
import random
import mysql.connector
from faker import Faker

from .config import DB_CONFIG, RANDOM_SEED, VOLUMES

fake = Faker()
fake.seed_instance(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_accounts(count=None):
    if count is None:
        count = VOLUMES["accounts"]

    accounts = []

    for i in range(1, count + 1):
        account = {
            "account_id": f"ACC-2026-{i:06d}",
            "account_name": fake.company(),
            "payment_terms_days": random.choice([15, 30, 45, 60, 90]),
            "credit_limit": round(random.uniform(10000, 500000), 2),
            "currency_code": "USD",
            "status": random.choice(
                ["ACTIVE", "INACTIVE", "CREDIT_HOLD"]
            )
        }

        accounts.append(account)

    return accounts


def insert_accounts(accounts):
    if not accounts:
        print("No accounts to insert.")
        return

    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        query = """
            INSERT INTO account (
                account_id,
                account_name,
                payment_terms_days,
                credit_limit,
                currency_code,
                status
            )
            VALUES (
                %(account_id)s,
                %(account_name)s,
                %(payment_terms_days)s,
                %(credit_limit)s,
                %(currency_code)s,
                %(status)s
            )
        """

        cursor.executemany(query, accounts)
        connection.commit()

        print(f"Successfully inserted {cursor.rowcount} accounts.")

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


if __name__ == "__main__":
    accounts = generate_accounts()
    insert_accounts(accounts)
