"""Normalized SQLite storage and analytical SQL examples."""
import sqlite3
from contextlib import closing
import pandas as pd
from .config import PROCESSED, SQL_DIR, OUTPUT, WELL_TYPES, PARAMETERS, active_pairs

DB_PATH = PROCESSED / "wells.db"
GAP_SQL = """
WITH ordered AS (
    SELECT well_id, parameter, timestamp,
           LAG(timestamp) OVER (
               PARTITION BY well_id, parameter ORDER BY timestamp
           ) AS previous_timestamp
    FROM observations
)
SELECT well_id, parameter, previous_timestamp, timestamp,
       (CAST(strftime('%s', timestamp) AS INTEGER) -
        CAST(strftime('%s', previous_timestamp) AS INTEGER)) / 3600 - 1 AS missing_hours
FROM ordered
WHERE (CAST(strftime('%s', timestamp) AS INTEGER) -
       CAST(strftime('%s', previous_timestamp) AS INTEGER)) > 3600
ORDER BY well_id, parameter, timestamp
"""

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE wells (
    well_id TEXT PRIMARY KEY,
    well_type TEXT NOT NULL CHECK(well_type IN ('fountain','sucker_rod_pump'))
);
CREATE TABLE parameters (
    parameter TEXT PRIMARY KEY,
    unit TEXT NOT NULL,
    applicable_well_type TEXT NOT NULL
);
CREATE TABLE well_parameters (
    well_id TEXT NOT NULL REFERENCES wells(well_id),
    parameter TEXT NOT NULL REFERENCES parameters(parameter),
    PRIMARY KEY (well_id, parameter)
);
CREATE TABLE observations (
    observation_id INTEGER PRIMARY KEY,
    well_id TEXT NOT NULL,
    parameter TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    value REAL NOT NULL,
    n_obs INTEGER NOT NULL CHECK(n_obs > 0),
    split TEXT NOT NULL CHECK(split IN ('train','test')),
    flag TEXT NOT NULL,
    regime TEXT NOT NULL,
    scale_period TEXT NOT NULL,
    scale_review INTEGER NOT NULL CHECK(scale_review IN (0,1)),
    FOREIGN KEY (well_id, parameter) REFERENCES well_parameters(well_id, parameter),
    UNIQUE (well_id, parameter, timestamp)
);
CREATE TABLE flags (
    flag_name TEXT PRIMARY KEY
);
CREATE TABLE observation_flags (
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
    flag_name TEXT NOT NULL REFERENCES flags(flag_name),
    PRIMARY KEY (observation_id, flag_name)
);
CREATE INDEX idx_observation_time ON observations(timestamp);
CREATE INDEX idx_observation_split ON observations(split);
"""


def create_database(frame, exploded_flags):
    """Rebuild derived storage atomically; raw source CSVs are never changed."""
    temporary = DB_PATH.with_suffix(".building.db")
    if temporary.exists():
        temporary.unlink()
    # A sqlite connection's own context manager commits but does not close it.
    # Explicit closing is required before atomic replacement on Windows.
    with closing(sqlite3.connect(temporary)) as conn, conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO wells VALUES (?, ?)", WELL_TYPES.items())
        conn.executemany("INSERT INTO parameters VALUES (?, ?, ?)",
                         [(p, unit, kind) for p, (unit, kind) in PARAMETERS.items()])
        conn.executemany("INSERT INTO well_parameters VALUES (?, ?)", active_pairs())
        columns = ["observation_id", "well_id", "parameter", "timestamp", "value", "n_obs",
                   "split", "flag", "regime", "scale_period", "scale_review"]
        stored = frame[columns].copy()
        stored["timestamp"] = stored["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        conn.executemany("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         stored.itertuples(index=False, name=None))
        names = sorted(exploded_flags["flag_name"].unique())
        conn.executemany("INSERT INTO flags VALUES (?)", [(name,) for name in names])
        conn.executemany("INSERT INTO observation_flags VALUES (?, ?)",
                         exploded_flags[["observation_id", "flag_name"]].itertuples(index=False, name=None))
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database foreign-key validation failed.")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed.")
    temporary.replace(DB_PATH)
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    (SQL_DIR / "schema.sql").write_text(SCHEMA.strip() + "\n", encoding="utf-8")


def query_definitions():
    """Each query answers an explicit audit or exploratory question."""
    return {
        "01_well_inventory": """
SELECT w.well_id, w.well_type, COUNT(o.observation_id) AS observations,
       COUNT(DISTINCT o.parameter) AS observed_parameters,
       MIN(o.timestamp) AS first_observation, MAX(o.timestamp) AS last_observation
FROM wells w LEFT JOIN observations o ON w.well_id = o.well_id
GROUP BY w.well_id, w.well_type ORDER BY w.well_id;
""",
        "02_parameter_statistics": """
SELECT p.parameter, p.unit, COUNT(*) AS observations, AVG(o.value) AS mean_value,
       MIN(o.value) AS minimum_value, MAX(o.value) AS maximum_value,
       AVG(o.n_obs) AS mean_raw_records_per_hour
FROM observations o JOIN parameters p ON p.parameter = o.parameter
GROUP BY p.parameter, p.unit ORDER BY p.parameter;
""",
        "03_monthly_well_trends": """
SELECT w.well_id, w.well_type, o.parameter, p.unit,
       substr(o.timestamp,1,7) AS month, COUNT(*) AS observations,
       AVG(o.value) AS mean_value, SUM(o.flag <> '') AS flagged_hours
FROM observations o JOIN wells w ON w.well_id = o.well_id
JOIN parameters p ON p.parameter = o.parameter
GROUP BY w.well_id, w.well_type, o.parameter, p.unit, month
ORDER BY w.well_id, o.parameter, month;
""",
        "04_interior_gaps_lag": GAP_SQL + ";\n",
        "05_individual_flag_counts": """
SELECT f.flag_name, COUNT(*) AS occurrences, COUNT(DISTINCT o.well_id) AS wells
FROM flags f JOIN observation_flags ofl ON f.flag_name = ofl.flag_name
JOIN observations o ON o.observation_id = ofl.observation_id
GROUP BY f.flag_name ORDER BY occurrences DESC;
""",
        "06_wells_with_many_flagged_hours": """
SELECT w.well_id, w.well_type, COUNT(*) AS observations,
       SUM(o.flag <> '') AS flagged_observations,
       ROUND(100.0 * SUM(o.flag <> '') / COUNT(*), 3) AS flagged_percent
FROM observations o JOIN wells w ON o.well_id = w.well_id
GROUP BY w.well_id, w.well_type HAVING SUM(o.flag <> '') >= 100
ORDER BY flagged_percent DESC;
""",
        "07_missing_series_rank": """
WITH completeness AS (
    SELECT wp.well_id, wp.parameter, 6552 AS expected_hours,
           COUNT(o.observation_id) AS observed_hours,
           6552 - COUNT(o.observation_id) AS missing_hours
    FROM well_parameters wp LEFT JOIN observations o
      ON wp.well_id = o.well_id AND wp.parameter = o.parameter
    GROUP BY wp.well_id, wp.parameter
)
SELECT *, DENSE_RANK() OVER (ORDER BY missing_hours DESC) AS missing_rank
FROM completeness ORDER BY missing_rank, well_id, parameter;
""",
        "08_daily_collection_coverage": """
WITH RECURSIVE calendar(date) AS (
    SELECT '2026-01-01'
    UNION ALL
    SELECT date(date, '+1 day') FROM calendar WHERE date < '2026-09-30'
), daily AS (
    SELECT substr(timestamp,1,10) AS date, COUNT(*) AS observed_rows,
           COUNT(DISTINCT well_id) AS wells_reporting
    FROM observations GROUP BY date
)
SELECT c.date, COALESCE(d.observed_rows, 0) AS observed_rows, 43 * 24 AS expected_rows,
       43 * 24 - COALESCE(d.observed_rows, 0) AS missing_rows,
       COALESCE(d.wells_reporting, 0) AS wells_reporting
FROM calendar c LEFT JOIN daily d ON c.date = d.date
ORDER BY missing_rows DESC, c.date;
""",
        "09_subquery_flagged_well_parameter_review": """
SELECT well_id, parameter, COUNT(*) AS observations,
       SUM(flag <> '') AS flagged_hours, SUM(value = 0) AS zero_value_hours
FROM observations
WHERE well_id IN (
    SELECT well_id FROM observations GROUP BY well_id HAVING SUM(flag <> '') >= 100
)
GROUP BY well_id, parameter ORDER BY well_id, parameter;
""",
        "10_nk7_regime_comparison": """
SELECT regime, parameter, COUNT(*) AS observations,
       AVG(value) AS mean_value, SUM(value = 0) AS zero_hours,
       SUM(value < 0) AS negative_hours, SUM(flag <> '') AS flagged_hours
FROM observations WHERE well_id = 'NK-7'
GROUP BY regime, parameter ORDER BY parameter, regime;
""",
        "11_multi_flag_observations": """
SELECT o.observation_id, o.well_id, o.parameter, o.timestamp, o.value,
       COUNT(ofl.flag_name) AS flag_count,
       GROUP_CONCAT(ofl.flag_name, ';') AS individual_flags
FROM observations o JOIN observation_flags ofl ON o.observation_id = ofl.observation_id
GROUP BY o.observation_id HAVING COUNT(ofl.flag_name) > 1
ORDER BY o.timestamp;
""",
        "12_official_split_summary": """
SELECT split, COUNT(*) AS observations, MIN(timestamp) AS first_time,
       MAX(timestamp) AS last_time, SUM(flag <> '') AS flagged_observations,
       COUNT(DISTINCT well_id) AS wells
FROM observations GROUP BY split ORDER BY first_time;
""",
    }


def export_queries():
    outputs = {}
    with closing(sqlite3.connect(DB_PATH)) as conn:
        for name, sql in query_definitions().items():
            (SQL_DIR / f"{name}.sql").write_text(sql.strip() + "\n", encoding="utf-8")
            table = pd.read_sql_query(sql, conn)
            table.to_csv(OUTPUT / "sql" / f"{name}.csv", index=False)
            outputs[name] = table
    return outputs
