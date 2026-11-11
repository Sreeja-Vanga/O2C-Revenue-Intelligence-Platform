
import json
from datetime import datetime
from decimal import Decimal

from config import GROUND_TRUTH_DIR


GROUND_TRUTH_FILE = GROUND_TRUTH_DIR / "ground_truth.json"


def convert_values(value):
    """Convert Decimal and datetime objects into JSON-compatible values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def save_ground_truth(anomalies):
    """Save anomaly records without creating duplicates."""

    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    existing = []

    if GROUND_TRUTH_FILE.exists():
        with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as file:
            existing = json.load(file)

    existing_ids = {
        record.get("exception_id")
        for record in existing
        if record.get("exception_id")
    }

    new_records = []

    for anomaly in anomalies:
        exception_id = anomaly.get("exception_id")

        if exception_id and exception_id in existing_ids:
            print(f"Skipping duplicate anomaly: {exception_id}")
            continue

        new_records.append(anomaly)

        if exception_id:
            existing_ids.add(exception_id)

    existing.extend(new_records)

    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as file:
        json.dump(
            existing,
            file,
            indent=4,
            default=convert_values
        )

    print(f"Ground truth saved: {len(new_records)} new records")
    print(f"Total ground truth records: {len(existing)}")


def load_ground_truth():
    """Load all ground truth records."""

    if not GROUND_TRUTH_FILE.exists():
        return []

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":

    # Add SHIPMENT_QUANTITY anomaly if it is not already present.
    shipment_anomaly = {
        "exception_id": "EXC-2026-000002",
        "anomaly_code": "SHIPMENT_QUANTITY",
        "entity_type": "SHIPMENT_LINE",
        "entity_id": 2,
        "sales_order_id": "SO-2026-000001",
        "expected_quantity": 13.0,
        "actual_quantity": 14.0,
        "description": "Shipment quantity exceeds the ordered quantity by one unit."
    }

    billing_anomaly = {
        "exception_id": "EXC-2026-000003",
        "anomaly_code": "BILLING_MISMATCH",
        "entity_type": "INVOICE_LINE",
        "entity_id": 1,
        "sales_order_id": "SO-2026-000184",
        "invoice_id": "INV-2026-000001",
        "expected_quantity": 16.0,
        "actual_quantity": 17.0,
        "description": "Invoice quantity exceeds shipped quantity by one unit."
    }

    cash_anomaly = {
        "exception_id": "EXC-2026-000004",
        "anomaly_code": "CASH_APPLICATION",
        "entity_type": "PAYMENT_ALLOCATION",
        "entity_id": 2,
        "payment_id": "PAY-2026-000002",
        "invoice_id": "INV-2026-000003",
        "expected_amount": 6717.88,
        "actual_amount": 7717.88,
        "variance_amount": 1000.00,
        "description": "Payment allocation exceeds the actual payment amount by 1000.00."
    }

    dispute_anomaly = {
        "exception_id": "EXC-2026-000005",
        "anomaly_code": "DISPUTE_LEAKAGE",
        "entity_type": "DISPUTE",
        "entity_id": "DSP-2026-000034",
        "dispute_id": "DSP-2026-000034",
        "invoice_id": "INV-2026-000344",
        "expected_amount": 0.00,
        "actual_amount": 4718.23,
        "variance_amount": 4718.23,
        "description": "Approved dispute credit has not been applied to the corresponding invoice."
    }

    order_closed_anomaly = {
        "exception_id": "EXC-2026-000006",
        "anomaly_code": "ORDER_CLOSED_UNPAID",
        "entity_type": "SALES_ORDER",
        "entity_id": "SO-2026-000026",
        "sales_order_id": "SO-2026-000026",
        "invoice_id": "INV-2026-000002",
        "expected_amount": 11370.05,
        "actual_amount": 0.00,
        "description": "Sales order closed while its invoice has an outstanding unpaid balance."
    }

    status_anomaly = {
        "exception_id": "EXC-2026-000007",
        "anomaly_code": "STATUS_TRANSITION_SKIP",
        "entity_type": "SALES_ORDER",
        "entity_id": "SO-2026-000026",
        "sales_order_id": "SO-2026-000026",
        "expected_status": "DELIVERED",
        "actual_status": "CLOSED",
        "description": "Sales order transitioned directly from SHIPPED to CLOSED, skipping DELIVERED."
    }
    save_ground_truth([
    shipment_anomaly,
    billing_anomaly,
    cash_anomaly,
    dispute_anomaly,
    order_closed_anomaly,
    status_anomaly
])
    # Display all saved records.
    records = load_ground_truth()

    print("\nGround Truth Summary")
    print("--------------------")
    print(f"Total records: {len(records)}")

    for record in records:
        print(
            f"{record.get('exception_id')} | "
            f"{record.get('anomaly_code')}"
        )
