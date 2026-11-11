from backend.routes.resource_routes import build_resource_blueprint


dispute_bp = build_resource_blueprint("disputes", "/api/disputes")