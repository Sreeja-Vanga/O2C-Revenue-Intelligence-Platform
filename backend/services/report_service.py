from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from backend.services import analytics_service
from backend.services.detection_engine import run_all_rules


_HEADER_FILL = PatternFill("solid", fgColor="17345B")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


def build_financial_workbook() -> BytesIO:
    leakage = analytics_service.get_revenue_leakage()
    receivables = analytics_service.get_outstanding_receivables()
    findings = run_all_rules()
    sheets: list[tuple[str, list[dict[str, Any]]]] = [
        ("Revenue leakage", leakage["items"]),
        ("Order performance", analytics_service.get_order_performance()["items"]),
        ("Invoice aging", analytics_service.get_invoice_aging()["items"]),
        ("Receivables", receivables["items"]),
        ("Payment performance", [analytics_service.get_payment_performance()]),
        ("Invoice performance", list(analytics_service.get_invoice_performance()["by_status"].values())),
        ("Disputes", analytics_service.get_dispute_analysis()["by_status"]),
        ("Reconciliation", findings),
    ]

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["O2C Revenue Intelligence — Financial Report"])
    summary.append([
        "Generated at (UTC)",
        datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
    ])
    summary.append([])
    summary.append(["Metric", "Value"])
    summary.append(["Recorded estimated leakage", _excel_value(leakage["total_estimated_leakage"])])
    summary.append(["Outstanding receivables", _excel_value(receivables["total_outstanding_amount"])])
    summary.append(["Independent reconciliation findings", len(findings)])
    summary.append(["Independent estimated exposure", _excel_value(sum(
        (_as_decimal(row.get("estimated_leakage", 0)) for row in findings),
        Decimal("0.00"),
    ))])

    for sheet_name, rows in sheets:
        sheet = workbook.create_sheet(sheet_name)
        _write_rows(sheet, rows)

    summary.freeze_panes = "A5"
    _format_sheet(summary, header_row=4)
    for sheet in workbook.worksheets[1:]:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        _format_sheet(sheet, header_row=1)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def _write_rows(sheet: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        sheet.append(["No records"])
        return
    headers = list(dict.fromkeys(key for row in rows for key in row))
    sheet.append(headers)
    for row in rows:
        sheet.append([_excel_value(row.get(header)) for header in headers])


def _excel_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list, tuple)):
        return str(value)
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _as_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _format_sheet(sheet: Any, header_row: int) -> None:
    for cell in sheet[header_row]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for column_cells in sheet.columns:
        column_index = column_cells[0].column
        longest = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=10,
        )
        sheet.column_dimensions[get_column_letter(column_index)].width = min(max(longest + 2, 12), 42)
    sheet.row_dimensions[header_row].height = 28
