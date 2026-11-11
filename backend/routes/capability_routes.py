from flask import Blueprint

from backend.config import TRANSACTION_WRITES_ENABLED
from backend.repositories import transaction_repository
from backend.utils.response import success_response
from backend.utils.validators import ValidationError


capability_bp = Blueprint("capabilities", __name__, url_prefix="/api")


@capability_bp.get("/capabilities")
def capabilities():
    return success_response({
        "transaction_writes_enabled": TRANSACTION_WRITES_ENABLED,
        "append_only_resources": ["events"],
    })


@capability_bp.get("/resource-schema/<resource>")
def resource_schema(resource: str):
    try:
        schema = transaction_repository.get_resource_schema(resource)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return success_response(schema)
