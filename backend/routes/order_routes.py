from backend.routes.resource_routes import build_resource_blueprint
from backend.services.order_service import get_order, list_orders


order_bp = build_resource_blueprint(
    "orders", "/api/orders", list_orders, get_order
)