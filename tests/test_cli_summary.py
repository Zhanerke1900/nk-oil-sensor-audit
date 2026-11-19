from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main as entrypoint


class SavedSummaryChecks(unittest.TestCase):
    def test_saved_summary_can_be_shown_without_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "summary.json").write_text(json.dumps({
                "rows": 258387, "wells": 10, "active_series": 43,
                "missing_hourly_rows": 23349, "missing_percent": 8.29,
                "flagged_rows": 7041, "sql_queries": 12,
            }), encoding="utf-8")
            output = StringIO()
            with patch("main.OUTPUT", root), patch("sys.argv", ["main.py", "--summary"]), \
                 patch("main.execute") as execute, redirect_stdout(output):
                self.assertEqual(entrypoint.main(), 0)
            execute.assert_not_called()
            self.assertIn("Rows: 258,387", output.getvalue())

    def test_missing_summary_explains_next_step(self):
        with tempfile.TemporaryDirectory() as directory:
            error = StringIO()
            with patch("main.OUTPUT", Path(directory)), patch("sys.argv", ["main.py", "--summary"]), \
                 redirect_stderr(error):
                self.assertEqual(entrypoint.main(), 1)
            self.assertIn("Run python main.py --run first", error.getvalue())


if __name__ == "__main__":
    unittest.main()
