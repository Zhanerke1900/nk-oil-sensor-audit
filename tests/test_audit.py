"""Small behavioral checks for costly audit mistakes; python -m unittest discover -s tests."""
import unittest
import sqlite3
from contextlib import closing
import pandas as pd
from src.config import active_pairs
from src.quality import coverage_table
from src.ingestion import validate_splits
from src.benchmarks import python_gaps, pandas_gaps
from src.database import query_definitions


class AuditChecks(unittest.TestCase):
    def test_structural_absence(self):
        self.assertEqual(len(active_pairs()), 43)
        self.assertNotIn(("NK-76", "casing_pressure"), active_pairs())

    def test_boundary_and_interior_hours(self):
        data = pd.DataFrame({"well_id": ["NK-7", "NK-7"], "parameter": ["SPM", "SPM"],
                             "timestamp": pd.to_datetime(["2026-01-01 01:00", "2026-01-01 03:00"])})
        coverage, boundaries = coverage_table(data, "2026-01-01 00:00", "2026-01-01 04:00", [("NK-7", "SPM")])
        self.assertEqual(coverage.iloc[0]["missing_hours"], 3)
        self.assertEqual(boundaries["missing_hours"].sum(), 2)
        self.assertEqual(set(boundaries["kind"]), {"leading", "trailing"})

    def test_no_cross_series_gap(self):
        records = [("NK-7", "SPM", 1), ("NK-7", "SPM", 4), ("NK-7", "pump_fillage", 10)]
        data = pd.DataFrame(records, columns=["well_id", "parameter", "hour"])
        expected = [("NK-7", "SPM", 1, 4, 2)]
        self.assertEqual(python_gaps(records), expected)
        self.assertEqual(pandas_gaps(data), expected)

    def test_overlapping_splits_rejected(self):
        train = pd.DataFrame({"well_id": ["NK-7"], "parameter": ["SPM"],
                              "timestamp": pd.to_datetime(["2026-08-08 22:00"])})
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_splits(train, train.copy())

    def test_sql_includes_an_entirely_absent_day(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE observations(timestamp TEXT, well_id TEXT)")
            conn.execute("INSERT INTO observations VALUES ('2026-01-02 00:00:00','NK-7')")
            result = pd.read_sql_query(query_definitions()["08_daily_collection_coverage"], conn)
        first = result[result["date"] == "2026-01-01"].iloc[0]
        self.assertEqual(len(result), 273)
        self.assertEqual(first["observed_rows"], 0)
        self.assertEqual(first["missing_rows"], 1032)


if __name__ == "__main__":
    unittest.main()
