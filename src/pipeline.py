"""Orchestrate the complete reproducible ETL and quality audit."""
import importlib.metadata
import json
import platform
import time
import pandas as pd
from .config import RAW, PROCESSED, OUTPUT, START, END, TRAIN_END, TEST_START, WELL_TYPES, active_pairs, ensure_directories
from .ingestion import load_v2
from .quality import coverage_table, source_flag_tables, descriptive_tables, train_iqr_audit, compare_versions, known_issue_tables
from .database import create_database, export_queries, DB_PATH
from .benchmarks import benchmark_gaps


def write_wide(frame):
    """Pivot values to hourly features and retain missing cells as NaN.

    Column interpretation must use well_parameters: e.g. NK-76 casing pressure
    and all pump features in fountain wells are inapplicable, not sensor gaps.
    """
    wide = frame.pivot(index=["well_id", "timestamp"], columns="parameter", values="value")
    expected_index = pd.MultiIndex.from_product(
        [list(WELL_TYPES), pd.date_range(START, END, freq="h")], names=["well_id", "timestamp"])
    wide = wide.reindex(expected_index).reset_index()
    wide.columns.name = None
    wide["well_type"] = wide["well_id"].map(WELL_TYPES)
    wide["split"] = wide["timestamp"].le(pd.Timestamp(TRAIN_END)).map({True: "train", False: "test"})
    wide.to_parquet(PROCESSED / "wide.parquet", index=False)
    return wide


def split_statistics(frame):
    records = []
    for split, start, end in (("train", START, TRAIN_END), ("test", TEST_START, END)):
        part = frame[frame["split"] == split]
        coverage, _ = coverage_table(part, start, end)
        records.append({"split": split, "rows": len(part), "start": str(part["timestamp"].min()),
                        "end": str(part["timestamp"].max()), "expected_hours_across_series": int(coverage["expected_hours"].sum()),
                        "missing_hours_across_series": int(coverage["missing_hours"].sum()),
                        "flagged_rows": int(part["flag"].astype(str).ne("").sum())})
        coverage.to_csv(OUTPUT / f"coverage_{split}.csv", index=False)
    pd.DataFrame(records).to_csv(OUTPUT / "split_summary.csv", index=False)
    return records


def run_pipeline():
    ensure_directories()
    started = time.perf_counter()
    print("1/7 Loading and validating the two official v2 splits...")
    frame, ingestion = load_v2()
    frame.to_parquet(PROCESSED / "observations.parquet", index=False)
    wide = write_wide(frame)
    print("2/7 Auditing coverage, flags, distributions, and known changes...")
    coverage, boundaries = coverage_table(frame)
    coverage.to_csv(OUTPUT / "coverage_by_series.csv", index=False)
    boundaries.to_csv(OUTPUT / "gaps_boundary.csv", index=False)
    exploded, flag_counts = source_flag_tables(frame)
    flag_counts.to_csv(OUTPUT / "flags_by_well.csv", index=False)
    for name, table in descriptive_tables(frame).items():
        table.to_csv(OUTPUT / f"{name}.csv", index=False)
    iqr = train_iqr_audit(frame)
    iqr.to_csv(OUTPUT / "iqr_audit.csv", index=False)
    scale, regime = known_issue_tables(frame)
    splits = split_statistics(frame)
    print("3/7 Rebuilding normalized SQLite tables and running 12 SQL queries...")
    database_started = time.perf_counter()
    create_database(frame, exploded)
    db_seconds = time.perf_counter() - database_started
    sql_outputs = export_queries()
    gaps = sql_outputs["04_interior_gaps_lag"]
    gaps.to_csv(OUTPUT / "gaps_interior.csv", index=False)
    missing_count = int(coverage["missing_hours"].sum())
    interior_count = int(gaps["missing_hours"].sum())
    boundary_count = int(boundaries["missing_hours"].sum())
    if missing_count != interior_count + boundary_count:
        raise AssertionError("Coverage and gap-interval audit disagree.")
    print("4/7 Comparing v1 and v2 on their common time horizon...")
    release_comparison = compare_versions(frame)
    print("5/7 Benchmarking Python, Pandas, and SQLite on the same gap task...")
    benchmark, benchmark_notes = benchmark_gaps(frame)
    source_versions = {}
    for version in ("v1", "v2"):
        metadata_file = RAW / f"{version}_metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            source_versions[version] = metadata.get("sha")
    versions = {name: importlib.metadata.version(name) for name in ("pandas", "numpy", "pyarrow")}
    summary = {
        "project": "Sensor Data Quality Audit and ETL Pipeline",
        "topic_number": 19,
        "rows": int(len(frame)), "wells": int(frame["well_id"].nunique()),
        "parameters": int(frame["parameter"].nunique()), "active_series": len(active_pairs()),
        "period_start": START, "period_end": END,
        "train_rows": int(frame["split"].eq("train").sum()),
        "test_rows": int(frame["split"].eq("test").sum()),
        "split_cutoff": TRAIN_END, "test_start": TEST_START,
        "expected_hourly_rows": int(coverage["expected_hours"].sum()),
        "missing_hourly_rows": missing_count,
        "missing_percent": float(100 * missing_count / coverage["expected_hours"].sum()),
        "interior_gap_intervals": int(len(gaps)), "interior_missing_hours": interior_count,
        "boundary_gap_intervals": int(len(boundaries)), "boundary_missing_hours": boundary_count,
        "flagged_rows": int(frame["flag"].astype(str).ne("").sum()),
        "flagged_percent": float(100 * frame["flag"].astype(str).ne("").mean()),
        "individual_flag_occurrences": int(len(exploded)),
        "zero_value_rows_retained": int(frame["value"].eq(0).sum()),
        "wide_rows": int(len(wide)), "wide_columns": int(len(wide.columns)),
        "source_flag_counts": {str(k): int(v) for k, v in frame["flag"].value_counts().items()},
        "individual_flag_counts": {str(k): int(v) for k, v in exploded["flag_name"].value_counts().items()},
        "ingestion": ingestion, "splits": splits,
        "database_build_seconds": db_seconds, "database_bytes": DB_PATH.stat().st_size,
        "parquet_bytes": (PROCESSED / "observations.parquet").stat().st_size,
        "sql_queries": len(sql_outputs), "v1_v2": release_comparison,
        "benchmark": benchmark.to_dict("records"), "benchmark_notes": benchmark_notes,
        "area_scale_review": scale.to_dict("records"), "nk7_regime_review": regime.to_dict("records"),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "library_versions": versions, "source_revisions": source_versions,
        "pipeline_seconds_before_figures": time.perf_counter() - started,
        "limitations": [
            "The provider assigned year 2026 from monthly source-file order; original SCADA timestamps should verify it.",
            "Source flags refer to raw records before hourly averaging; they are preserved rather than regenerated from hourly values.",
            "There are no verified equipment-failure labels; no fault-detection precision or recall is claimed.",
            "Area scale changes and the NK-7 regime shift require interpretation; no unverified calibration correction was applied.",
            "Tracemalloc excludes much native allocation; memory results are Python-traced allocations, not total RSS.",
            "The complete final table fits memory; chunked CSV reading does not make every analysis out of core.",
            "Missing cells in a wide table include structurally inapplicable parameters; coverage uses only the 43 active series.",
        ],
    }
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("6/7 Saving auditable results and processing metadata...")
    return frame, summary
