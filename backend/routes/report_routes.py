from flask import Blueprint, send_file

from backend.services.report_service import build_financial_workbook


report_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@report_bp.get("/financial.xlsx")
def financial_report():
    workbook = build_financial_workbook()
    return send_file(
        workbook,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="o2c-financial-report.xlsx",
    )
