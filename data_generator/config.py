
import os
from pathlib import Path
from dotenv import load_dotenv

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("O2C_GENERATOR_OUTPUT_DIR", BASE_DIR / "data"))
GENERATED_DIR = DATA_DIR / "generated"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Reproducibility
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "20261022"))

# Data volumes
VOLUMES = {
    "accounts": int(os.getenv("ACCOUNT_COUNT", "1000")),
    "quotes": int(os.getenv("QUOTE_COUNT", "10000")),
    "sales_orders": int(os.getenv("ORDER_COUNT", "7000")),
    "shipments": int(os.getenv("SHIPMENT_COUNT", "700")),
    "invoices": int(os.getenv("INVOICE_COUNT", "8000")),
    "payments": int(os.getenv("PAYMENT_COUNT", "7500")),
    "status_events": int(os.getenv("STATUS_EVENT_COUNT", "7500")),
}
QUOTE_COUNT = VOLUMES["quotes"]

# Anomaly rates
ANOMALY_RATES = {
    "PRICE_VARIANCE": 0.02,
    "SHIPMENT_QUANTITY": 0.02,
    "BILLING_MISMATCH": 0.02,
    "CASH_APPLICATION": 0.02,
    "DISPUTE_LEAKAGE": 0.02,
    "ORDER_CLOSED_UNPAID": 0.02,
    "STATUS_TRANSITION_SKIP": 0.02,
}

# MySQL configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "o2c_revenue_intelligence"),
}

# Create output directories
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
