"""Compare equivalent interior-gap algorithms, not fault-prediction models."""
import gc
import sqlite3
import time
import tracemalloc
import statistics
from contextlib import closing
import numpy as np
import pandas as pd
from .database import DB_PATH, GAP_SQL
from .config import OUTPUT


def python_gaps(records):
    """Baseline loop over prepared records sorted by well, parameter, time."""
    result = []
    previous_key, previous_hour = None, None
    for well, parameter, hour in records:
        key = (well, parameter)
        if key == previous_key and hour - previous_hour > 1:
            result.append((well, parameter, previous_hour, hour, hour - previous_hour - 1))
        previous_key, previous_hour = key, hour
    return result


def pandas_gaps(prepared):
    """Vectorized groupby+shift and subtraction on the same chronological input."""
    previous = prepared.groupby(["well_id", "parameter"], observed=True)["hour"].shift()
    mask = (prepared["hour"] - previous) > 1
    rows = prepared.loc[mask, ["well_id", "parameter", "hour"]].copy()
    rows["previous_hour"] = previous.loc[mask].astype("int64")
    rows["missing_hours"] = rows["hour"] - rows["previous_hour"] - 1
    return list(rows[["well_id", "parameter", "previous_hour", "hour", "missing_hours"]].itertuples(index=False, name=None))


def sqlite_gaps(connection):
    """LAG uses the same key order through SQLite's unique-key index."""
    records = connection.execute(GAP_SQL).fetchall()
    result = []
    for well, parameter, previous, current, missing in records:
        result.append((well, parameter, pd.Timestamp(previous).value // 3600000000000,
                       pd.Timestamp(current).value // 3600000000000, int(missing)))
    return result


def benchmark_gaps(frame, repeats=3):
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("Benchmark repeats must be a positive integer")
    started = time.perf_counter()
    # Prepared representations and database creation are deliberately not timed.
    # They have different purposes and are reported separately by the pipeline.
    prepared = frame[["well_id", "parameter", "timestamp"]].sort_values(["well_id", "parameter", "timestamp"]).copy()
    prepared["hour"] = prepared["timestamp"].astype("int64") // 3600000000000
    prepared = prepared.drop(columns="timestamp")
    records = list(prepared.itertuples(index=False, name=None))
    setup_seconds = time.perf_counter() - started
    rows = []
    with closing(sqlite3.connect(DB_PATH)) as connection:
        methods = {"Python loop baseline": lambda: python_gaps(records),
                   "Pandas groupby shift": lambda: pandas_gaps(prepared),
                   "SQLite LAG": lambda: sqlite_gaps(connection)}
        reference = sorted(python_gaps(records))
        for name, function in methods.items():
            result = function()  # Warm-up and correctness check.
            if sorted(result) != reference:
                raise AssertionError(f"Gap outputs differ for {name}.")
            durations = []
            for _ in range(repeats):
                gc.collect()
                start = time.perf_counter()
                function()
                durations.append(time.perf_counter() - start)
            # Memory is measured in a separate invocation: tracing would strongly
            # penalize Python loops if enabled during the timing comparison.
            gc.collect()
            tracemalloc.start()
            function()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append({"method": name, "median_seconds": statistics.median(durations),
                         "minimum_seconds": min(durations), "maximum_seconds": max(durations),
                         "python_traced_peak_bytes": int(peak), "gap_intervals": len(result),
                         "missing_hours": sum(row[-1] for row in result),
                         "exact_output_match": True, "repeats": repeats})
    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT / "benchmark.csv", index=False)
    return table, {
        "prepared_input_setup_seconds": setup_seconds,
        "timing_scope": "Warm computational query on prepared inputs; initial CSV parsing, common sort, record conversion, database construction/index creation are excluded. Output tuple conversion is included.",
        "memory_scope": "tracemalloc peak Python-traced incremental allocations from a separate run; prepared inputs excluded. SQLite native allocations are not fully captured. This is not total process RSS and does not establish total-memory superiority.",
        "ground_truth": "Exact algorithm-output equivalence on identical records, not precision/recall against verified fault labels.",
        "repeats": repeats,
        "caution": "Hardware, Python and library versions, cache state, and input representation influence timings; this is not an end-to-end ETL benchmark.",
    }
