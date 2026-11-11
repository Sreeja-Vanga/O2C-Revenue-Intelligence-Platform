from flask import Blueprint, request

from backend.services import synthetic_data_service
from backend.utils.response import error_response, success_response


synthetic_data_bp = Blueprint("synthetic_data", __name__, url_prefix="/api/synthetic-data")


@synthetic_data_bp.post("/jobs")
def create_generation_job():
    body = request.get_json(silent=False)
    if not isinstance(body, dict):
        return error_response("A JSON object is required.", 400)
    try:
        job = synthetic_data_service.start_generation(body.get("profile", "small"))
    except ValueError as exc:
        return error_response(str(exc), 400)
    return success_response(job, "Sandbox generation job accepted.", 202)


@synthetic_data_bp.get("/jobs/<job_id>")
def get_generation_job(job_id: str):
    job = synthetic_data_service.get_generation_job(job_id)
    if job is None:
        return error_response("Generation job not found.", 404)
    return success_response(job)
