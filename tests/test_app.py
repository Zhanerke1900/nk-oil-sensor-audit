"""Dashboard regressions: display filters must not fabricate missing readings."""
from pathlib import Path
import tempfile
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        rows = [
            ("NK-7", "sucker_rod_pump", 0, "SPM", 4., "strokes/min", 6, "", "train"),
            ("NK-7", "sucker_rod_pump", 2, "SPM", 4., "strokes/min", 6, "", "train"),
            ("NK-7", "sucker_rod_pump", 3, "SPM", 9.2, "strokes/min", 6, "spm_outlier", "test"),
            ("NK-76", "fountain", 0, "tubing_pressure", 3., "atm", 12, "", "train"),
            ("NK-76", "fountain", 5, "tubing_pressure", 3., "atm", 12, "", "test"),
        ]
        frame = pd.DataFrame(rows, columns=["well_id", "well_type", "timestamp", "parameter",
                                          "value", "unit", "n_obs", "flag", "split"])
        frame["timestamp"] = pd.Timestamp("2026-01-01") + pd.to_timedelta(frame["timestamp"], unit="h")
        self.file = self.root / "observations.parquet"
        frame.to_parquet(self.file, index=False)
        self.script = f'''import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("nk_dashboard", {str(APP)!r})
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
app.ROOT = Path({str(self.root)!r})
app.DATA_FILE = Path({str(self.file)!r})
app.main()
'''

    def tearDown(self):
        self.temporary.cleanup()

    def test_flag_filter_preserves_coverage_and_boundary_gaps(self):
        app = AppTest.from_string(self.script, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["6", "3", "3", "1", "50,00%"])
        flag_choice = next(s for s in app.sidebar.selectbox if s.label == "Флаги на графике")
        flag_choice.select("Только с флагами").run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["6", "3", "3", "1", "50,00%"])
        split_choice = next(s for s in app.sidebar.selectbox if s.label == "Выборка")
        split_choice.select("test").run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["3", "1", "2", "1", "33,33%"])

    def test_structurally_absent_parameter_is_not_offered(self):
        app = AppTest.from_string(self.script, default_timeout=30).run()
        next(s for s in app.sidebar.selectbox if s.label == "Скважина").select("NK-76").run()
        self.assertFalse(app.exception)
        options = next(s for s in app.sidebar.selectbox if s.label == "Параметр").options
        self.assertEqual(options, ["tubing_pressure"])

    def test_missing_file_provides_run_instructions(self):
        self.file.unlink()
        app = AppTest.from_string(self.script, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("python main.py --run" in c.value for c in app.code))


if __name__ == "__main__":
    unittest.main()
