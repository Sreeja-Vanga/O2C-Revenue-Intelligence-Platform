import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

from backend.app import app
from backend.services.report_service import build_financial_workbook
from backend.services.synthetic_data_service import extract_safe_schema_ddl
from backend.services import synthetic_data_service


class NewFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_sandbox_schema_extractor_never_returns_drop_statements(self):
        schema_path = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
        statements = extract_safe_schema_ddl(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(sum(statement.upper().startswith("CREATE TABLE") for statement in statements), 14)
        self.assertEqual(sum(statement.upper().startswith("CREATE TRIGGER") for statement in statements), 2)
        self.assertTrue(all(not statement.upper().startswith("DROP") for statement in statements))

    def test_synthetic_data_routes_validate_profile_and_job_id(self):
        invalid = self.client.post("/api/synthetic-data/jobs", json={"profile": "large"})
        self.assertEqual(invalid.status_code, 400)
        missing = self.client.get("/api/synthetic-data/jobs/not-a-job")
        self.assertEqual(missing.status_code, 404)

    def test_capabilities_and_write_gate(self):
        capabilities = self.client.get("/api/capabilities")
        self.assertTrue(capabilities.get_json()["success"])
        self.assertFalse(capabilities.get_json()["data"]["transaction_writes_enabled"])
        blocked = self.client.post("/api/orders", json={"status": "DRAFT"})
        self.assertEqual(blocked.status_code, 403)
        append_only = self.client.delete("/api/events/1")
        self.assertEqual(append_only.status_code, 409)

    def test_resource_schema_uses_live_mysql_columns(self):
        response = self.client.get("/api/resource-schema/orders")
        self.assertEqual(response.status_code, 200)
        fields = response.get_json()["data"]["fields"]
        names = {field["name"] for field in fields}
        self.assertIn("sales_order_id", names)
        self.assertIn("total_amount", names)
        self.assertTrue(next(field for field in fields if field["name"] == "sales_order_id")["primary_key"])

    @patch("backend.routes.resource_routes.TRANSACTION_WRITES_ENABLED", True)
    @patch("backend.routes.resource_routes.transaction_service.create_record")
    def test_transaction_create_endpoint_uses_write_service(self, create_record):
        create_record.return_value = {"account_id": "ACC-2026-000099"}
        response = self.client.post("/api/accounts", json={"account_name": "Test"})
        self.assertEqual(response.status_code, 201)
        create_record.assert_called_once_with("accounts", {"account_name": "Test"})

    @patch("backend.services.report_service.analytics_service.get_revenue_leakage")
    @patch("backend.services.report_service.analytics_service.get_outstanding_receivables")
    @patch("backend.services.report_service.analytics_service.get_order_performance")
    @patch("backend.services.report_service.analytics_service.get_invoice_aging")
    @patch("backend.services.report_service.analytics_service.get_payment_performance")
    @patch("backend.services.report_service.analytics_service.get_invoice_performance")
    @patch("backend.services.report_service.analytics_service.get_dispute_analysis")
    @patch("backend.services.report_service.run_all_rules")
    def test_financial_workbook_contains_operational_sheets(
        self, run_rules, dispute_analysis, invoice_performance,
        payment_performance, invoice_aging, order_performance,
        receivables, leakage,
    ):
        leakage.return_value = {"items": [{"anomaly_code": "PRICE_VARIANCE", "estimated_leakage": 12.5}], "total_estimated_leakage": 12.5}
        receivables.return_value = {"items": [{"account_id": "ACC-1", "outstanding_amount": 40}], "total_outstanding_amount": 40}
        order_performance.return_value = {"items": [{"status": "OPEN", "order_count": 1}]}
        invoice_aging.return_value = {"items": [{"aging_bucket": "CURRENT", "outstanding_amount": 40}]}
        payment_performance.return_value = {"payment_total": 10}
        invoice_performance.return_value = {"by_status": {"ISSUED": {"invoice_count": 1}}}
        dispute_analysis.return_value = {"by_status": [{"status": "OPEN", "dispute_count": 1}]}
        run_rules.return_value = [{"anomaly_code": "CASH_APPLICATION", "estimated_leakage": 2}]

        workbook_bytes = build_financial_workbook()
        workbook = load_workbook(BytesIO(workbook_bytes.getvalue()), read_only=True)
        self.assertEqual(
            workbook.sheetnames,
            ["Summary", "Revenue leakage", "Order performance", "Invoice aging",
             "Receivables", "Payment performance", "Invoice performance",
             "Disputes", "Reconciliation"],
        )
        self.assertEqual(workbook["Reconciliation"]["A2"].value, "CASH_APPLICATION")

    @patch("backend.services.synthetic_data_service.database_config")
    @patch("backend.services.synthetic_data_service.mysql.connector.connect")
    @patch("backend.services.synthetic_data_service.subprocess.run")
    @patch("backend.services.synthetic_data_service._create_sandbox")
    def test_generation_orchestrator_uses_new_sandbox_and_ordered_modules(
        self, create_sandbox, run_process, connect, db_config
    ):
        job_id = "a" * 32
        with synthetic_data_service._jobs_lock:
            synthetic_data_service._jobs[job_id] = {"job_id": job_id, "status": "queued"}
        db_config.return_value = {"database": "o2c_live", "host": "localhost"}
        run_process.return_value.returncode = 0
        connection = connect.return_value
        connection.cursor.return_value.fetchone.return_value = (7,)

        synthetic_data_service._run_generation(job_id, "small")
        result = synthetic_data_service.get_generation_job(job_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["database"], "o2c_ri_sandbox_aaaaaaaaaaaa")
        self.assertEqual(len(result["tables"]), 14)
        self.assertEqual(run_process.call_count, len(synthetic_data_service._GENERATOR_MODULES))
        self.assertEqual(
            [call.args[0][-1] for call in run_process.call_args_list],
            [f"data_generator.{name}" for name in synthetic_data_service._GENERATOR_MODULES],
        )
        self.assertEqual(connect.call_count, 1)
        create_sandbox.assert_called_once_with("o2c_ri_sandbox_aaaaaaaaaaaa")


if __name__ == "__main__":
    unittest.main()
