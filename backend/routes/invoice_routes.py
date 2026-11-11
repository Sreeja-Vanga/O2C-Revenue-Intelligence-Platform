from backend.routes.resource_routes import build_resource_blueprint
from backend.services.invoice_service import get_invoice, list_invoices


invoice_bp = build_resource_blueprint(
    "invoices", "/api/invoices", list_invoices, get_invoice
)