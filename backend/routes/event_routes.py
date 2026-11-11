from flask import Blueprint

from backend.routes.resource_routes import build_resource_blueprint
from backend.services.transaction_service import get_events_for_entity
from backend.utils.response import success_response


event_bp = build_resource_blueprint("events", "/api/events")
event_entity_bp = Blueprint("event_entity", __name__, url_prefix="/api/events")


@event_entity_bp.get("/entity/<entity_type>/<entity_id>")
def list_entity_events(entity_type: str, entity_id: str):
    return success_response(get_events_for_entity(entity_type, entity_id))