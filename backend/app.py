import logging

from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import FLASK_HOST, FLASK_PORT, FRONTEND_ORIGINS
from backend.database.db import DatabaseConflict, DatabaseUnavailable, check_connection
from backend.routes.analytics_routes import analytics_bp
from backend.routes.capability_routes import capability_bp
from backend.routes.account_routes import account_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.detection_routes import detection_bp
from backend.routes.dispute_routes import dispute_bp
from backend.routes.event_routes import event_bp, event_entity_bp
from backend.routes.exception_routes import exception_bp
from backend.routes.invoice_routes import invoice_bp
from backend.routes.order_routes import order_bp
from backend.routes.payment_routes import payment_bp
from backend.routes.report_routes import report_bp
from backend.routes.quote_routes import quote_bp
from backend.routes.shipment_routes import shipment_bp
from backend.routes.synthetic_data_routes import synthetic_data_bp
from backend.utils.logger import configure_logging
from backend.utils.response import error_response, success_response
from backend.utils.validators import ValidationError


logger = logging.getLogger(__name__)


def create_app() -> Flask:
    configure_logging()
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": list(FRONTEND_ORIGINS)}})
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(exception_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(quote_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(dispute_bp)
    app.register_blueprint(shipment_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(event_entity_bp)
    app.register_blueprint(synthetic_data_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(capability_bp)

    @app.get("/")
    def index():
        return success_response({
            "service": "O2C Revenue Intelligence API",
            "health_url": "/api/health",
            "api_base_url": "/api",
        })

    @app.get("/api/health")
    def health():
        try:
            connected = check_connection()
        except DatabaseUnavailable:
            return success_response(
                {
                    "backend_status": "running",
                    "database_status": "unavailable",
                },
                "Backend is running but the database is unavailable.",
                503,
            )
        return success_response({
            "backend_status": "running",
            "database_status": "connected" if connected else "unavailable",
        })

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return error_response(str(error), 400)

    @app.errorhandler(DatabaseUnavailable)
    def handle_database_error(error: DatabaseUnavailable):
        logger.warning("Database request failed (%s).", type(error).__name__)
        return error_response("The database operation could not be completed.", 503)

    @app.errorhandler(DatabaseConflict)
    def handle_database_conflict(error: DatabaseConflict):
        return error_response(str(error), 409)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return error_response(error.description, error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.error("Unhandled API error (%s).", type(error).__name__)
        return error_response("An unexpected server error occurred.", 500)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT)