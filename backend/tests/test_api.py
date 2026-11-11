import unittest
from unittest.mock import patch

from backend.app import app
from backend.database.db import DatabaseUnavailable


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def assert_success_json(self, response):
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsInstance(body, dict)
        self.assertTrue(body["success"])
        self.assertIn("message", body)
        self.assertIn("data", body)
        return body["data"]

    def test_health(self):
        data = self.assert_success_json(self.client.get("/api/health"))
        self.assertEqual(data["backend_status"], "running")
        self.assertEqual(data["database_status"], "connected")

    def test_health_reports_database_unavailable(self):
        with patch("backend.app.check_connection", side_effect=DatabaseUnavailable):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json()["data"]["database_status"], "unavailable"
        )

    def test_root_returns_api_information(self):
        data = self.assert_success_json(self.client.get("/"))
        self.assertEqual(data["service"], "O2C Revenue Intelligence API")
        self.assertEqual(data["health_url"], "/api/health")

    def test_exception_list_and_filters(self):
        data = self.assert_success_json(
            self.client.get("/api/exceptions?anomaly_code=PRICE_VARIANCE&per_page=5")
        )
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(data["items"][0]["anomaly_code"], "PRICE_VARIANCE")

    def test_exception_summary_and_missing_id(self):
        summary = self.assert_success_json(self.client.get("/api/exceptions/summary"))
        self.assertGreaterEqual(summary["total_exceptions"], 7)
        details = self.assert_success_json(
            self.client.get("/api/exceptions/EXC-2026-000001")
        )
        self.assertEqual(details["anomaly_code"], "PRICE_VARIANCE")
        response = self.client.get("/api/exceptions/EXC-2099-999999")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_valid_exception_status_update_response_without_database_write(self):
        expected = {
            "exception_id": "EXC-2026-000001",
            "status": "ACKNOWLEDGED",
        }
        with patch(
            "backend.routes.exception_routes.exception_service.update_status",
            return_value=expected,
        ) as update_status:
            response = self.client.put(
                "/api/exceptions/EXC-2026-000001/status",
                json={"status": "ACKNOWLEDGED"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], expected)
        update_status.assert_called_once_with("EXC-2026-000001", "ACKNOWLEDGED")

    def test_detection_endpoints(self):
        detected = self.assert_success_json(self.client.post("/api/detection/run"))
        self.assertGreaterEqual(detected["total_detected"], 7)
        self.assertTrue(self.assert_success_json(
            self.client.get("/api/detection/results")
        )["has_run"])
        summary = self.assert_success_json(self.client.get("/api/detection/summary"))
        self.assertGreaterEqual(summary["total_detected_anomalies"], 7)

    def test_all_analytics_endpoints(self):
        for name in (
            "revenue-leakage",
            "order-performance",
            "invoice-performance",
            "payment-performance",
            "trends",
            "invoice-aging",
            "dispute-analysis",
            "lifecycle-performance",
            "outstanding-receivables",
            "reconciliation",
            "reconciliation/details",
        ):
            with self.subTest(endpoint=name):
                self.assert_success_json(self.client.get(f"/api/analytics/{name}"))

    def test_analytics_root_lists_available_endpoints(self):
        data = self.assert_success_json(self.client.get("/api/analytics"))
        paths = {endpoint["path"] for endpoint in data["endpoints"]}
        self.assertIn("/api/analytics/trends", paths)
        self.assertIn("/api/analytics/reconciliation/details", paths)

    def test_dashboard_lifecycle_and_dispute_count(self):
        overview = self.assert_success_json(
            self.client.get("/api/dashboard/overview")
        )
        self.assertIn("total_disputes", overview)
        lifecycle = self.assert_success_json(
            self.client.get("/api/dashboard/lifecycle-summary")
        )
        self.assertIn("orders_by_status", lifecycle)

    def test_transaction_list_and_detail_endpoints(self):
        resources = (
            ("accounts", "ACC-2026-000001"),
            ("quotes", "QTE-2026-000001"),
            ("orders", "SO-2026-000001"),
            ("shipments", "SHP-2026-000001"),
            ("invoices", "INV-2026-000001"),
            ("payments", "PAY-2026-000001"),
            ("disputes", "DSP-2026-000001"),
            ("events", "1"),
        )
        for resource, record_id in resources:
            with self.subTest(resource=resource):
                listing = self.assert_success_json(
                    self.client.get(f"/api/{resource}?per_page=2")
                )
                self.assertEqual(len(listing["items"]), 2)
                detail = self.assert_success_json(
                    self.client.get(f"/api/{resource}/{record_id}")
                )
                self.assertIsInstance(detail, dict)

        entity_events = self.assert_success_json(
            self.client.get(
                "/api/events/entity/SALES_ORDER/SO-2026-000026?per_page=10"
            )
        )
        self.assertGreaterEqual(entity_events["pagination"]["total"], 1)

    def test_transaction_filters_and_source_exception(self):
        filtered = self.assert_success_json(
            self.client.get(
                "/api/orders?status=CLOSED&date_from=2026-01-01"
            )
        )
        self.assertGreaterEqual(filtered["pagination"]["total"], 1)
        searched = self.assert_success_json(
            self.client.get("/api/exceptions?search=SO-2026-000026")
        )
        self.assertGreaterEqual(searched["pagination"]["total"], 1)
        source = self.assert_success_json(
            self.client.get("/api/exceptions/EXC-2026-000001/source")
        )
        self.assertEqual(source["exception"]["exception_id"], "EXC-2026-000001")
        self.assertIsNotNone(source["order_line"])

    def test_invalid_requests_use_json_errors(self):
        invalid_requests = (
            self.client.get("/api/exceptions?page=0"),
            self.client.get("/api/exceptions?per_page=201"),
            self.client.get("/api/exceptions?sort_by=does_not_exist"),
            self.client.get("/api/exceptions?severity=URGENT"),
            self.client.get("/api/exceptions?date_from=not-a-date"),
            self.client.get("/api/orders?date_from=2026-03-01&date_to=2026-02-01"),
            self.client.put(
                "/api/exceptions/EXC-2026-000001/status",
                json={"status": "NOT_A_STATUS"},
            ),
            self.client.get("/api/not-a-route"),
        )
        for response in invalid_requests:
            with self.subTest(status=response.status_code):
                self.assertGreaterEqual(response.status_code, 400)
                body = response.get_json()
                self.assertIsInstance(body, dict)
                self.assertFalse(body["success"])
                self.assertIsNone(body["data"])

    def test_update_missing_exception_does_not_change_records(self):
        with patch(
            "backend.routes.exception_routes.exception_service.update_status",
            return_value=None,
        ):
            response = self.client.put(
                "/api/exceptions/EXC-2099-999999/status",
                json={"status": "RESOLVED"},
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
