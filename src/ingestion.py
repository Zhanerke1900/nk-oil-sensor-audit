"""Read the official splits; validate before any transformation."""
import time
import numpy as np
import pandas as pd
from .config import RAW, KEY, WELL_TYPES, PARAMETERS, START, END, TRAIN_END, TEST_START, active_pairs


def read_chunks(path, chunksize=50000):
    """Bound CSV parsing buffers, then assemble this modest-size educational set.

    This is chunked ingestion, not a claim that the complete pipeline is out of
    core. The final 258K-row table is deliberately materialized for analysis.
    """
    if isinstance(chunksize, bool) or not isinstance(chunksize, int) or chunksize < 1:
        raise ValueError("chunksize must be a positive integer")
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name}. Run python download.py first.")
    chunks = []
    largest_chunk_bytes = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, keep_default_na=True):
        largest_chunk_bytes = max(largest_chunk_bytes, int(chunk.memory_usage(deep=True).sum()))
        chunks.append(chunk)
    if not chunks:
        raise ValueError(f"Empty input file: {path}")
    return pd.concat(chunks, ignore_index=True), largest_chunk_bytes


def validate_frame(frame, version="v2"):
    """Reject malformed records; only exact duplicate observations may be removed."""
    required = {"well_id", "well_type", "timestamp", "parameter", "value", "unit"}
    if version == "v2":
        required |= {"n_obs", "flag"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("No sensor observations to validate")
    result = frame.copy()
    null_counts = {col: int(result[col].isna().sum()) for col in sorted(required)}
    # An empty flag means no source flag. It is not an unknown sensor reading.
    if "flag" in result:
        result["flag"] = result["flag"].fillna("").astype(str)
    essential = sorted(required - {"flag"})
    if result[essential].isna().any().any():
        raise ValueError("Null in a required measurement or key field; inspect input, do not silently impute.")
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="raise")
    result["value"] = pd.to_numeric(result["value"], errors="raise").astype("float64")
    if not np.isfinite(result["value"]).all():
        raise ValueError("Non-finite sensor values found.")
    if not result["timestamp"].eq(result["timestamp"].dt.floor("h")).all():
        raise ValueError("Timestamps must be aligned to the start of an hour.")
    if not result["timestamp"].between(pd.Timestamp(START), pd.Timestamp(END)).all():
        raise ValueError("Timestamp outside the documented January–September 2026 horizon.")
    allowed = set(active_pairs())
    observed = set(zip(result["well_id"], result["parameter"]))
    if not observed <= allowed:
        raise ValueError(f"Unknown or structurally inapplicable series: {observed - allowed}")
    if not result["well_type"].eq(result["well_id"].map(WELL_TYPES)).all():
        raise ValueError("Inconsistent well type.")
    expected_units = result["parameter"].map({p: v[0] for p, v in PARAMETERS.items()})
    if not result["unit"].eq(expected_units).all():
        raise ValueError("Inconsistent units: a calibration review is required.")
    if version == "v2":
        n_obs = pd.to_numeric(result["n_obs"], errors="raise")
        if not np.isfinite(n_obs).all() or (n_obs < 1).any() or (n_obs % 1 != 0).any():
            raise ValueError("n_obs must be a positive integer.")
        result["n_obs"] = n_obs.astype("int64")
    exact_duplicates = int(result.duplicated().sum())
    result = result.drop_duplicates().reset_index(drop=True)
    conflicting_keys = int(result.duplicated(KEY, keep=False).sum())
    if conflicting_keys:
        raise ValueError(f"{conflicting_keys} records have conflicting duplicate keys; no arbitrary averaging performed.")
    return result, {"raw_null_counts": null_counts, "exact_duplicates_removed": exact_duplicates,
                    "conflicting_duplicate_records": conflicting_keys, "invalid_records": 0}


def optimize_types(frame):
    result = frame.copy()
    for column in ("well_id", "well_type", "parameter", "unit", "flag", "split"):
        if column in result:
            result[column] = result[column].astype("category")
    if "n_obs" in result:
        result["n_obs"] = pd.to_numeric(result["n_obs"], downcast="unsigned")
    return result


def validate_splits(train, test):
    if train.empty or test.empty:
        raise ValueError("Both official splits must be nonempty.")
    if train["timestamp"].max() >= test["timestamp"].min():
        raise ValueError("Official train/test time ranges overlap.")
    if train["timestamp"].max() > pd.Timestamp(TRAIN_END) or test["timestamp"].min() < pd.Timestamp(TEST_START):
        raise ValueError("The supplied split does not follow the published cutoff.")
    if pd.MultiIndex.from_frame(train[KEY]).intersection(pd.MultiIndex.from_frame(test[KEY])).size:
        raise ValueError("The same observation appears in both train and test.")


def load_v2():
    started = time.perf_counter()
    frames, audits, chunk_memory = [], {}, []
    raw_memory = 0
    for split in ("train", "test"):
        raw, peak = read_chunks(RAW / f"v2_{split}.csv")
        raw_memory += int(raw.memory_usage(deep=True).sum())
        clean, audit = validate_frame(raw, "v2")
        clean["split"] = split
        frames.append(clean)
        audits[split] = audit
        chunk_memory.append(peak)
    validate_splits(*frames)
    combined = pd.concat(frames, ignore_index=True)
    before = int(combined.memory_usage(deep=True).sum())
    combined = optimize_types(combined)
    after = int(combined.memory_usage(deep=True).sum())
    combined = combined.sort_values(KEY).reset_index(drop=True)
    combined["observation_id"] = np.arange(1, len(combined) + 1, dtype="int64")
    combined["regime"] = np.where(
        (combined["well_id"] == "NK-7") & (combined["timestamp"] >= "2026-06-01"),
        "NK7_from_June", "original")
    change_date = pd.Series(pd.Timestamp("2026-05-01"), index=combined.index)
    change_date.loc[combined["well_id"] == "NK-82"] = pd.Timestamp("2026-05-08")
    area = combined["parameter"] == "dynamometer_area"
    combined["scale_period"] = np.where(~area, "not_applicable",
                                         np.where(combined["timestamp"] < change_date, "before_shift", "after_shift"))
    # Review marker is metadata, not a claim that each marked reading is wrong.
    combined["scale_review"] = area.astype("int8")
    combined["regime"] = combined["regime"].astype("category")
    combined["scale_period"] = combined["scale_period"].astype("category")
    return combined, {
        "splits": audits, "raw_csv_frame_bytes": raw_memory,
        "memory_before_optimization_bytes": before, "memory_after_optimization_bytes": after,
        "memory_reduction_percent": 100 * (1 - after / before),
        "largest_parsed_chunk_bytes": max(chunk_memory), "chunksize": 50000,
        "memory_measurement": "DataFrame.memory_usage(deep=True); same validated columns before/after dtype optimization; derived audit fields excluded",
        "loading_seconds": time.perf_counter() - started,
    }
