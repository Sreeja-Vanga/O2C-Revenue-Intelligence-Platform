from backend.routes.resource_routes import build_resource_blueprint
from backend.services.quote_service import get_quote, list_quotes


quote_bp = build_resource_blueprint(
    "quotes", "/api/quotes", list_quotes, get_quote
)