from flask import Blueprint

from backend.services import detection_engine
from backend.utils.response import success_response


detection_bp = Blueprint("detection", __name__, url_prefix="/api/detection")


@detection_bp.post("/run")
def run_detection():
    return success_response(
        detection_engine.run_detection(),
        "Independent anomaly detection completed successfully.",
    )


@detection_bp.get("/results")
def detection_results():
    return success_response(detection_engine.get_latest_results())


@detection_bp.get("/summary")
def detection_summary():
    return success_response(detection_engine.get_detection_summary())
