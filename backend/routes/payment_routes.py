from backend.routes.resource_routes import build_resource_blueprint
from backend.services.payment_service import get_payment, list_payments


payment_bp = build_resource_blueprint(
    "payments", "/api/payments", list_payments, get_payment
)