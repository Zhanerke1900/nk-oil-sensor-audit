from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.database import export_queries, query_definitions


class DatabaseExportChecks(unittest.TestCase):
    def test_query_collection_contains_twelve_queries_and_window_function(self):
        definitions = query_definitions()
        self.assertEqual(len(definitions), 12)
        self.assertIn("LAG(", definitions["04_interior_gaps_lag"])
        self.assertIn("HAVING", definitions["06_wells_with_many_flagged_hours"])

    def test_missing_database_cannot_be_silently_created(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not_created.db"
            with patch("src.database.DB_PATH", missing):
                with self.assertRaisesRegex(FileNotFoundError, "Run python main.py --run"):
                    export_queries()
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
