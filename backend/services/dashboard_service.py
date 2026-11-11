from typing import Any

from backend.repositories import dashboard_repository


def get_overview() -> dict[str, Any]:
    return dashboard_repository.get_overview()


def get_anomaly_summary() -> list[dict[str, Any]]:
    return dashboard_repository.get_anomaly_summary()


def get_revenue_summary() -> dict[str, Any]:
    return dashboard_repository.get_revenue_summary()


def get_lifecycle_summary() -> dict[str, Any]:
    return dashboard_repository.get_lifecycle_summary()
