from backend.routes.resource_routes import build_resource_blueprint


account_bp = build_resource_blueprint("accounts", "/api/accounts")