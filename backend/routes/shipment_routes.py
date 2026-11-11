from backend.routes.resource_routes import build_resource_blueprint
from backend.services.fulfillment_service import get_shipment, list_shipments


shipment_bp = build_resource_blueprint(
    "shipments", "/api/shipments", list_shipments, get_shipment
)
