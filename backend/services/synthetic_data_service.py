import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import mysql.connector

from backend.config import PROJECT_ROOT, database_config


logger = logging.getLogger(__name__)
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
_generation_lock = threading.Lock()

_TABLE_DDL = re.compile(
    r"CREATE\s+TABLE\s+.*?\)\s*ENGINE\s*=.*?;",
    re.IGNORECASE | re.DOTALL,
)
_TRIGGER_DDL = re.compile(
    r"CREATE\s+TRIGGER\b.*?MESSAGE_TEXT\s*=\s*'[^']*'\s*;",
    re.IGNORECASE | re.DOTALL,
)
_PROFILES = {
    "small": {"ACCOUNT_COUNT": "25", "QUOTE_COUNT": "60", "ORDER_COUNT": "40"},
    "demo": {"ACCOUNT_COUNT": "100", "QUOTE_COUNT": "250", "ORDER_COUNT": "150"},
}
_GENERATOR_MODULES = (
    "master_data",
    "transaction_data",
    "order_data",
    "shipment_data",
    "invoice_data",
    "payment_data",
    "dispute_data",
    "status_event_data",
)


def extract_safe_schema_ddl(schema_text: str) -> list[str]:
    """Return only table and trigger creation statements; never return DROP DDL."""
    tables = [match.group(0).strip() for match in _TABLE_DDL.finditer(schema_text)]
    triggers = [
        match.group(0).strip().rstrip(";")
        for match in _TRIGGER_DDL.finditer(schema_text)
    ]
    statements = tables + triggers
    if not tables or any(re.match(r"\s*DROP\b", item, re.IGNORECASE) for item in statements):
        raise RuntimeError("The schema did not contain safe table creation statements.")
    return statements


def start_generation(profile: str) -> dict[str, Any]:
    if profile not in _PROFILES:
        raise ValueError("profile must be 'small' or 'demo'.")
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "status": "queued",
        "profile": profile,
        "created_at": now,
        "updated_at": now,
        "database": None,
        "message": "Waiting to create an isolated sandbox database.",
        "tables": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    worker = threading.Thread(
        target=_run_generation,
        args=(job_id, profile),
        name=f"synthetic-data-{job_id[:8]}",
        daemon=True,
    )
    worker.start()
    return dict(job)


def get_generation_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update_job(job_id: str, **changes: Any) -> None:
    with _jobs_lock:
        _jobs[job_id].update(
            changes,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )


def _create_sandbox(database_name: str) -> None:
    config = database_config()
    config.pop("database", None)
    connection = mysql.connector.connect(**config)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        finally:
            cursor.close()
    finally:
        connection.close()

    schema_file = PROJECT_ROOT / "database" / "schema.sql"
    statements = extract_safe_schema_ddl(schema_file.read_text(encoding="utf-8"))
    sandbox_config = database_config()
    sandbox_config["database"] = database_name
    connection = mysql.connector.connect(**sandbox_config)
    try:
        cursor = connection.cursor()
        try:
            for statement in statements:
                cursor.execute(statement)
        finally:
            cursor.close()
    finally:
        connection.close()


def _run_generation(job_id: str, profile: str) -> None:
    if not _generation_lock.acquire(blocking=False):
        _update_job(job_id, status="failed", message="Another generation job is already running.")
        return

    database_name = f"o2c_ri_sandbox_{job_id[:12]}"
    try:
        configured_database = str(database_config()["database"])
        if database_name == configured_database:
            raise RuntimeError("Refusing to generate into the configured application database.")

        _update_job(job_id, status="running", database=database_name,
                    message="Creating a new isolated MySQL sandbox.")
        _create_sandbox(database_name)

        output_dir = PROJECT_ROOT / "data" / "generated_runs" / job_id
        environment = os.environ.copy()
        environment.update(_PROFILES[profile])
        environment.update({
            "DB_NAME": database_name,
            "O2C_GENERATOR_OUTPUT_DIR": str(output_dir),
            "PYTHONPATH": os.pathsep.join(
                (str(PROJECT_ROOT), str(PROJECT_ROOT / "data_generator"),
                 environment.get("PYTHONPATH", ""))
            ).rstrip(os.pathsep),
        })

        for module in _GENERATOR_MODULES:
            _update_job(job_id, message=f"Generating {module.replace('_', ' ')}.")
            result = subprocess.run(
                [sys.executable, "-m", f"data_generator.{module}"],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            if result.returncode:
                detail = (result.stderr or result.stdout or "Generator process failed.").strip()
                password = os.getenv("DB_PASSWORD", "")
                if password:
                    detail = detail.replace(password, "[redacted]")
                raise RuntimeError(f"{module} failed: {detail[-2000:]}")

        db_config = database_config()
        db_config["database"] = database_name
        connection = mysql.connector.connect(**db_config)
        try:
            cursor = connection.cursor()
            try:
                schema_text = (PROJECT_ROOT / "database" / "schema.sql").read_text(
                    encoding="utf-8"
                )
                table_names = [
                    match.group(1)
                    for statement in _TABLE_DDL.findall(schema_text)
                    if (match := re.search(r"CREATE\s+TABLE\s+`?([A-Za-z0-9_]+)", statement, re.I))
                ]
                tables = {}
                for table_name in table_names:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    tables[table_name] = int(cursor.fetchone()[0])
            finally:
                cursor.close()
        finally:
            connection.close()

        _update_job(
            job_id,
            status="completed",
            tables=tables,
            output_directory=str(output_dir),
            message="Synthetic O2C data was generated in the isolated sandbox.",
        )
    except Exception as exc:
        logger.error(
            "Synthetic data generation failed for job %s (%s).",
            job_id,
            type(exc).__name__,
        )
        message = str(exc)
        password = os.getenv("DB_PASSWORD", "")
        if password:
            message = message.replace(password, "[redacted]")
        _update_job(job_id, status="failed", message=message)
    finally:
        _generation_lock.release()
