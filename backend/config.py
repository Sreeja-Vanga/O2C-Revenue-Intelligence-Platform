import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_PREFIX = "/api"
FRONTEND_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
)
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
TRANSACTION_WRITES_ENABLED = os.getenv("TRANSACTION_WRITES_ENABLED", "false").strip().lower() == "true"


def database_config() -> dict[str, object]:
    """Return connector settings without logging or exposing secret values."""
    required = ("DB_HOST", "DB_USER", "DB_NAME")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing required database configuration: " + ", ".join(missing)
        )
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be an integer.") from exc

    return {
        "host": os.environ["DB_HOST"],
        "port": port,
        "user": os.environ["DB_USER"],
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.environ["DB_NAME"],
        "connection_timeout": 5,
    }