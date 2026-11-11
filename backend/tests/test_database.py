import unittest

from backend.database.db import check_connection, fetch_one
from backend.utils.id_generator import format_document_id


class DatabaseConnectionTests(unittest.TestCase):
    def test_mysql_connection_and_dictionary_cursor(self):
        self.assertTrue(check_connection())
        row = fetch_one("SELECT DATABASE() AS database_name")
        self.assertEqual(row["database_name"], "o2c_revenue_intelligence")

    def test_document_id_format_matches_schema(self):
        self.assertEqual(
            format_document_id("so", 2026, 1),
            "SO-2026-000001",
        )
        with self.assertRaises(ValueError):
            format_document_id("unknown", 2026, 1)


if __name__ == "__main__":
    unittest.main()
