from collections.abc import Callable
from typing import Any

from flask import Blueprint, request

from backend.config import TRANSACTION_WRITES_ENABLED
from werkzeug.datastructures import ImmutableMultiDict

from backend.services import transaction_service
from backend.utils.response import error_response, success_response


ListService = Callable[[ImmutableMultiDict[str, str]], dict[str, Any]]
GetService = Callable[[str], dict[str, Any] | None]


def build_resource_blueprint(
    resource: str,
    url_prefix: str,
    list_service: ListService | None = None,
    get_service: GetService | None = None,
) -> Blueprint:
    blueprint = Blueprint(resource, __name__, url_prefix=url_prefix)

    def list_items():
        data = (
            list_service(request.args)
            if list_service is not None
            else transaction_service.list_records(resource, request.args)
        )
        return success_response(data)

    def get_item(record_id: str):
        record = (
            get_service(record_id)
            if get_service is not None
            else transaction_service.get_record(resource, record_id)
        )
        if record is None:
            return error_response("Record not found.", 404)
        return success_response(record)

    def create_item():
        if not TRANSACTION_WRITES_ENABLED:
            return error_response("Transaction writes are disabled. Enable TRANSACTION_WRITES_ENABLED to allow changes.", 403)
        try:
            row = transaction_service.create_record(resource, request.get_json(silent=False))
        except ValueError as exc:
            return error_response(str(exc), 400)
        return success_response(row, "Transaction record created.", 201)

    def update_item(record_id: str):
        if resource == "events":
            return error_response("Status event history is append-only.", 409)
        if not TRANSACTION_WRITES_ENABLED:
            return error_response("Transaction writes are disabled. Enable TRANSACTION_WRITES_ENABLED to allow changes.", 403)
        try:
            row = transaction_service.update_record(
                resource, record_id, request.get_json(silent=False)
            )
        except ValueError as exc:
            return error_response(str(exc), 400)
        if row is None:
            return error_response("Record not found.", 404)
        return success_response(row, "Transaction record updated.")

    def delete_item(record_id: str):
        if resource == "events":
            return error_response("Status event history is append-only.", 409)
        if not TRANSACTION_WRITES_ENABLED:
            return error_response("Transaction writes are disabled. Enable TRANSACTION_WRITES_ENABLED to allow changes.", 403)
        try:
            deleted = transaction_service.delete_record(resource, record_id)
        except ValueError as exc:
            return error_response(str(exc), 400)
        if not deleted:
            return error_response("Record not found.", 404)
        return success_response({"deleted": True, "id": record_id}, "Transaction record deleted.")

    list_items.__name__ = f"list_{resource}"
    get_item.__name__ = f"get_{resource[:-1] if resource.endswith('s') else resource}"
    create_item.__name__ = f"create_{resource}"
    update_item.__name__ = f"update_{resource}"
    delete_item.__name__ = f"delete_{resource}"
    blueprint.add_url_rule("", view_func=list_items, methods=["GET"])
    blueprint.add_url_rule("", view_func=create_item, methods=["POST"])
    blueprint.add_url_rule("/<record_id>", view_func=get_item, methods=["GET"])
    blueprint.add_url_rule("/<record_id>", view_func=update_item, methods=["PUT", "PATCH"])
    blueprint.add_url_rule("/<record_id>", view_func=delete_item, methods=["DELETE"])
    return blueprint
