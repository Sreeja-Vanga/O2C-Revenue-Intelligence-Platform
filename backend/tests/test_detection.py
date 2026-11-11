import unittest
from decimal import Decimal

from backend.services import detection_engine


class DetectionRuleTests(unittest.TestCase):
    def test_each_rule_detects_its_injected_transaction_anomaly(self):
        rule_expectations = (
            (
                detection_engine.detect_price_variance,
                "PRICE_VARIANCE",
                "ORDER_LINE",
                1,
                Decimal("946.02"),
                Decimal("1135.2240"),
            ),
            (
                detection_engine.detect_shipment_quantity,
                "SHIPMENT_QUANTITY",
                "SHIPMENT_LINE",
                2,
                Decimal("13"),
                Decimal("14"),
            ),
            (
                detection_engine.detect_billing_mismatch,
                "BILLING_MISMATCH",
                "INVOICE_LINE",
                1,
                Decimal("16"),
                Decimal("17"),
            ),
            (
                detection_engine.detect_cash_application,
                "CASH_APPLICATION",
                "PAYMENT",
                "PAY-2026-000002",
                Decimal("6717.88"),
                Decimal("7717.88"),
            ),
            (
                detection_engine.detect_dispute_leakage,
                "DISPUTE_LEAKAGE",
                "INVOICE",
                "INV-2026-000344",
                Decimal("0"),
                Decimal("4718.23"),
            ),
            (
                detection_engine.detect_order_closed_unpaid,
                "ORDER_CLOSED_UNPAID",
                "SALES_ORDER",
                "SO-2026-000026",
                Decimal("0"),
                Decimal("11370.05"),
            ),
            (
                detection_engine.detect_status_transition_skip,
                "STATUS_TRANSITION_SKIP",
                "SALES_ORDER",
                "SO-2026-000026",
                "DELIVERED",
                "CLOSED",
            ),
        )
        for rule, code, entity_type, entity_id, expected_value, actual_value in rule_expectations:
            with self.subTest(rule=code):
                findings = rule()
                matching = [
                    finding for finding in findings
                    if finding["anomaly_code"] == code
                    and finding["entity_type"] == entity_type
                    and str(finding["entity_id"]) == str(entity_id)
                ]
                self.assertTrue(matching, f"{code} was not detected from source data")
                self.assertEqual(matching[0]["severity"], "HIGH")
                self.assertEqual(matching[0]["expected_value"], expected_value)
                self.assertEqual(matching[0]["actual_value"], actual_value)
                self.assertIn("expected_value", matching[0])
                self.assertIn("actual_value", matching[0])
                self.assertIn("variance", matching[0])
                self.assertIn("explanation", matching[0])

    def test_detection_summary_is_built_from_detection_results(self):
        result = detection_engine.run_detection()
        summary = detection_engine.get_detection_summary()
        expected_codes = {
            "PRICE_VARIANCE",
            "SHIPMENT_QUANTITY",
            "BILLING_MISMATCH",
            "CASH_APPLICATION",
            "DISPUTE_LEAKAGE",
            "ORDER_CLOSED_UNPAID",
            "STATUS_TRANSITION_SKIP",
        }
        self.assertTrue(result["has_run"])
        self.assertTrue(expected_codes.issubset(summary["count_by_anomaly_type"]))
        self.assertEqual(
            result["total_detected"],
            sum(summary["count_by_anomaly_type"].values()),
        )
        self.assertGreater(summary["estimated_revenue_leakage"], 0)

    def test_repeated_detection_runs_do_not_duplicate_findings(self):
        first = detection_engine.run_all_rules()
        second = detection_engine.run_all_rules()
        first_keys = {
            (item["anomaly_code"], item["entity_type"], str(item["entity_id"]))
            for item in first
        }
        second_keys = {
            (item["anomaly_code"], item["entity_type"], str(item["entity_id"]))
            for item in second
        }
        self.assertEqual(first_keys, second_keys)
        self.assertEqual(len(first), len(first_keys))


if __name__ == "__main__":
    unittest.main()
