"""Source definitions, paths, and the documented monitoring horizon."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "outputs"
SQL_DIR = ROOT / "sql"
START = "2026-01-01 00:00:00"
END = "2026-09-30 23:00:00"
TRAIN_END = "2026-08-08 22:00:00"
TEST_START = "2026-08-08 23:00:00"
KEY = ["well_id", "parameter", "timestamp"]
WELL_TYPES = {
    "NK-75": "fountain", "NK-76": "fountain", "NK-83": "fountain",
    "NK-7": "sucker_rod_pump", "NK-68": "sucker_rod_pump",
    "NK-77": "sucker_rod_pump", "NK-82": "sucker_rod_pump",
    "NK-86": "sucker_rod_pump", "NK-91": "sucker_rod_pump",
    "NK-93": "sucker_rod_pump",
}
PARAMETERS = {
    "tubing_pressure": ("atm", "fountain"),
    "casing_pressure": ("atm", "fountain"),
    "line_pressure": ("atm", "fountain"),
    "SPM": ("strokes/min", "sucker_rod_pump"),
    "pump_fillage": ("%", "sucker_rod_pump"),
    "min_rod_weight": ("kg", "sucker_rod_pump"),
    "max_rod_weight": ("kg", "sucker_rod_pump"),
    "dynamometer_area": ("unitless", "sucker_rod_pump"),
}


def active_pairs():
    """NK-76 casing pressure is structurally absent, not a missing sensor."""
    return [(well, parameter) for well, kind in WELL_TYPES.items()
            for parameter, (_, applicable) in PARAMETERS.items()
            if kind == applicable and (well, parameter) != ("NK-76", "casing_pressure")]


def ensure_directories():
    for path in (RAW, PROCESSED, OUTPUT, OUTPUT / "sql", OUTPUT / "figures"):
        path.mkdir(parents=True, exist_ok=True)
