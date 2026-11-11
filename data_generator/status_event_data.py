
import mysql.connector

from config import DB_CONFIG


ENTITY_CONFIG = [
    ("ACCOUNT", "account", "account_id"),
    ("QUOTE", "quote", "quote_id"),
    ("SALES_ORDER", "sales_order", "sales_order_id"),
    ("SHIPMENT", "shipment", "shipment_id"),
    ("INVOICE", "invoice", "invoice_id"),
    ("PAYMENT", "payment", "payment_id"),
    ("DISPUTE", "dispute", "dispute_id"),
]


def generate_status_events():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    total_events = 0

    try:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM status_event"
        )

        if cursor.fetchone()["total"] > 0:
            raise ValueError(
                "Status events already exist. "
                "Generation stopped to prevent duplicates."
            )

        for entity_type, table_name, id_column in ENTITY_CONFIG:

            query = f"""
                SELECT
                    {id_column} AS entity_id,
                    status AS current_status,
                    created_at
                FROM {table_name}
                WHERE status IS NOT NULL
            """

            cursor.execute(query)
            records = cursor.fetchall()

            for record in records:
                cursor.execute("""
                    INSERT INTO status_event (
                        entity_type,
                        entity_id,
                        from_status,
                        to_status,
                        event_at,
                        actor,
                        note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    entity_type,
                    record["entity_id"],
                    None,
                    record["current_status"],
                    record["created_at"],
                    "SYSTEM",
                    "Initial status snapshot generated."
                ))

                total_events += 1

            print(
                f"{entity_type}: {len(records)} events created"
            )

        conn.commit()

        print("\nStatus event generation completed!")
        print("Total events created:", total_events)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    generate_status_events()