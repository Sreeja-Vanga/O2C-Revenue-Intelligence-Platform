from flask import Blueprint

from backend.services import dashboard_service
from backend.utils.response import success_response


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/overview")
def overview():
    return success_response(dashboard_service.get_overview())


@dashboard_bp.get("/anomaly-summary")
def anomaly_summary():
    return success_response(dashboard_service.get_anomaly_summary())


@dashboard_bp.get("/revenue-summary")
def revenue_summary():
    return success_response(dashboard_service.get_revenue_summary())


@dashboard_bp.get("/lifecycle-summary")
def lifecycle_summary():
    return success_response(dashboard_service.get_lifecycle_summary())