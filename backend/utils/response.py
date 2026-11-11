from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import jsonify


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def success_response(
    data: Any,
    message: str = "Data retrieved successfully",
    status: int = 200,
):
    return jsonify({
        "success": True,
        "message": message,
        "data": to_jsonable(data),
    }), status


def error_response(message: str, status: int):
    return jsonify({
        "success": False,
        "message": message,
        "data": None,
    }), status
