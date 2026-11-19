import unittest
import pandas as pd

from src.quality import coverage_table, source_flag_tables


class QualityChecks(unittest.TestCase):
    def test_reversed_coverage_interval_is_rejected(self):
        frame = pd.DataFrame(columns=["well_id", "parameter", "timestamp"])
        with self.assertRaisesRegex(ValueError, "Coverage start"):
            coverage_table(frame, "2026-01-02", "2026-01-01", [("NK-7", "SPM")])

    def test_compound_flags_strip_whitespace_and_ignore_empty_tokens(self):
        frame = pd.DataFrame({
            "observation_id": [1, 2], "well_id": ["NK-7", "NK-7"],
            "parameter": ["SPM", "SPM"],
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "split": ["train", "train"],
            "flag": ["high ; low;high;; ", "  "],
        })
        exploded, counts = source_flag_tables(frame)
        self.assertEqual(set(exploded["flag_name"]), {"high", "low"})
        self.assertEqual(len(exploded), 2)
        self.assertEqual(counts["flag_occurrences"].sum(), 2)
        self.assertEqual(frame.loc[0, "flag"], "high ; low;high;; ")


if __name__ == "__main__":
    unittest.main()
