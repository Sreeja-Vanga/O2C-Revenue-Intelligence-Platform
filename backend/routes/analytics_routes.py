from flask import Blueprint

from backend.services import analytics_service
from backend.services.detection_engine import run_all_rules
from backend.services.reconciliation_service import get_reconciliation_summary
from backend.utils.response import success_response


analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

ANALYTICS_ENDPOINTS = {
    "revenue-leakage": "Recorded exception leakage grouped by anomaly type.",
    "order-performance": "Sales order counts and values grouped by lifecycle status.",
    "invoice-performance": "Invoice balances grouped by status, including overdue totals.",
    "payment-performance": "Payment, allocation, and unapplied cash totals.",
    "trends": "Monthly invoice, payment, and exception trends.",
    "invoice-aging": "Open invoice balances grouped by age.",
    "dispute-analysis": "Dispute counts and amounts grouped by status.",
    "lifecycle-performance": "Quote conversion, fulfillment, and order-to-cash timing.",
    "outstanding-receivables": "Open invoice balances grouped by account.",
    "reconciliation": "Independent source-table findings grouped by anomaly type.",
    "reconciliation/details": "Detailed independent findings from source transaction tables.",
}


@analytics_bp.get("")
def analytics_index():
    return success_response({
        "message": "Choose an analytics resource from the available endpoints.",
        "endpoints": [
            {"path": f"/api/analytics/{path}", "description": description}
            for path, description in ANALYTICS_ENDPOINTS.items()
        ],
    })


@analytics_bp.get("/revenue-leakage")
def revenue_leakage():
    return success_response(analytics_service.get_revenue_leakage())


@analytics_bp.get("/order-performance")
def order_performance():
    return success_response(analytics_service.get_order_performance())


@analytics_bp.get("/invoice-performance")
def invoice_performance():
    return success_response(analytics_service.get_invoice_performance())


@analytics_bp.get("/payment-performance")
def payment_performance():
    return success_response(analytics_service.get_payment_performance())


@analytics_bp.get("/trends")
def trends():
    return success_response(analytics_service.get_trends())


@analytics_bp.get("/invoice-aging")
def invoice_aging():
    return success_response(analytics_service.get_invoice_aging())


@analytics_bp.get("/dispute-analysis")
def dispute_analysis():
    return success_response(analytics_service.get_dispute_analysis())


@analytics_bp.get("/lifecycle-performance")
def lifecycle_performance():
    return success_response(analytics_service.get_lifecycle_performance())


@analytics_bp.get("/outstanding-receivables")
def outstanding_receivables():
    return success_response(analytics_service.get_outstanding_receivables())


@analytics_bp.get("/reconciliation")
def reconciliation():
    return success_response(get_reconciliation_summary())


@analytics_bp.get("/reconciliation/details")
def reconciliation_details():
    return success_response({
        "items": run_all_rules(),
        "source": "transaction_tables",
    })
