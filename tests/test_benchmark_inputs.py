import unittest
import pandas as pd
from src.benchmarks import benchmark_gaps


class BenchmarkInputChecks(unittest.TestCase):
    def test_invalid_repeat_counts_fail_before_query(self):
        for repeats in (0, -1, True, 2.5):
            with self.subTest(repeats=repeats):
                with self.assertRaisesRegex(ValueError, "Benchmark repeats"):
                    benchmark_gaps(pd.DataFrame(), repeats=repeats)


if __name__ == "__main__":
    unittest.main()
