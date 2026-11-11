import unittest

from backend.app import app


class DashboardApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_dashboard_overview_contains_kpis(self):
        response = self.client.get("/api/dashboard/overview")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertGreaterEqual(body["data"]["total_accounts"], 1)
        self.assertGreaterEqual(body["data"]["total_exceptions"], 7)
        self.assertIn("total_revenue_leakage", body["data"])

    def test_dashboard_summaries(self):
        for path in (
            "/api/dashboard/anomaly-summary",
            "/api/dashboard/revenue-summary",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
