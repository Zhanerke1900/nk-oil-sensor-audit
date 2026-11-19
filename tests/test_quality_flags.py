import unittest
import pandas as pd

from src.quality import coverage_table


class QualityChecks(unittest.TestCase):
    def test_reversed_coverage_interval_is_rejected(self):
        frame = pd.DataFrame(columns=["well_id", "parameter", "timestamp"])
        with self.assertRaisesRegex(ValueError, "Coverage start"):
            coverage_table(frame, "2026-01-02", "2026-01-01", [("NK-7", "SPM")])


if __name__ == "__main__":
    unittest.main()
