"""Missingness, source flags, exploratory summaries, and release comparison."""
import json
import numpy as np
import pandas as pd
from .config import START, END, TRAIN_END, TEST_START, KEY, OUTPUT, RAW, active_pairs
from .ingestion import read_chunks, validate_frame


def coverage_table(frame, start=START, end=END, pairs=None):
    """Count absent hourly rows, including both ends of the declared horizon."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    pairs = active_pairs() if pairs is None else pairs
    expected_hours = int((end - start) / pd.Timedelta(hours=1)) + 1
    part = frame[frame["timestamp"].between(start, end)]
    groups = {key: g for key, g in part.groupby(["well_id", "parameter"], observed=True)}
    coverage, boundaries = [], []
    for well, parameter in pairs:
        group = groups.get((well, parameter))
        present = 0 if group is None else int(group["timestamp"].nunique())
        first = None if not present else group["timestamp"].min()
        last = None if not present else group["timestamp"].max()
        coverage.append({"well_id": well, "parameter": parameter, "expected_hours": expected_hours,
                         "observed_hours": present, "missing_hours": expected_hours - present,
                         "missing_percent": 100 * (expected_hours - present) / expected_hours,
                         "first_observed": first, "last_observed": last})
        if not present:
            boundaries.append({"well_id": well, "parameter": parameter, "kind": "entire_series",
                               "missing_start": start, "missing_end": end, "missing_hours": expected_hours})
        else:
            if first > start:
                boundaries.append({"well_id": well, "parameter": parameter, "kind": "leading",
                                   "missing_start": start, "missing_end": first - pd.Timedelta(hours=1),
                                   "missing_hours": int((first - start) / pd.Timedelta(hours=1))})
            if last < end:
                boundaries.append({"well_id": well, "parameter": parameter, "kind": "trailing",
                                   "missing_start": last + pd.Timedelta(hours=1), "missing_end": end,
                                   "missing_hours": int((end - last) / pd.Timedelta(hours=1))})
    boundary_columns = ["well_id", "parameter", "kind", "missing_start", "missing_end", "missing_hours"]
    return pd.DataFrame(coverage), pd.DataFrame(boundaries, columns=boundary_columns)


def source_flag_tables(frame):
    """Explode semicolon flags without treating an empty string as a defect."""
    flagged = frame.loc[frame["flag"].astype(str).ne(""),
                        ["observation_id", "well_id", "parameter", "timestamp", "split", "flag"]].copy()
    flagged["flag_name"] = flagged["flag"].astype(str).str.split(";")
    exploded = flagged.explode("flag_name").drop_duplicates(["observation_id", "flag_name"])
    counts = exploded.groupby(["well_id", "flag_name"], observed=True).size().rename("flag_occurrences").reset_index()
    return exploded, counts


def descriptive_tables(frame):
    stats = frame.groupby(["well_id", "well_type", "parameter"], observed=True)["value"].describe().reset_index()
    with_dates = frame.assign(month=frame["timestamp"].dt.strftime("%Y-%m"),
                              date=frame["timestamp"].dt.floor("D"),
                              hour=frame["timestamp"].dt.hour)
    monthly = with_dates.groupby(["well_id", "well_type", "parameter", "month"], observed=True)["value"].agg(
        count="count", mean="mean", median="median", minimum="min", maximum="max").reset_index()
    daily = with_dates.groupby(["well_id", "well_type", "parameter", "date"], observed=True)["value"].agg(
        count="count", mean="mean", median="median").reset_index()
    hourly = with_dates.groupby(["well_type", "parameter", "hour"], observed=True)["value"].agg(
        count="count", median="median", mean="mean").reset_index()
    return {"descriptive_statistics": stats, "monthly_statistics": monthly,
            "daily_statistics": daily, "hourly_patterns": hourly}


def train_iqr_audit(frame):
    """Descriptive flags using training-only quartiles within known regimes.

    These statistical flags are not verified equipment-failure labels. No values
    are deleted. Known calibration periods are kept separate to avoid using one
    global range across the documented area-scale change.
    """
    grouping = ["well_id", "parameter", "regime", "scale_period"]
    train = frame[frame["split"] == "train"]
    thresholds = train.groupby(grouping, observed=True)["value"].quantile([0.25, 0.75]).unstack()
    thresholds.columns = ["q1", "q3"]
    thresholds = thresholds.reset_index()
    thresholds["iqr"] = thresholds["q3"] - thresholds["q1"]
    thresholds["lower"] = thresholds["q1"] - 1.5 * thresholds["iqr"]
    thresholds["upper"] = thresholds["q3"] + 1.5 * thresholds["iqr"]
    scored = frame.merge(thresholds, on=grouping, how="left", validate="many_to_one")
    scored["iqr_outlier"] = (scored["value"] < scored["lower"]) | (scored["value"] > scored["upper"])
    scored["unseen_training_group"] = scored["lower"].isna()
    result = scored.groupby(grouping + ["split"], observed=True).agg(
        observations=("value", "size"), iqr_outliers=("iqr_outlier", "sum"),
        without_training_threshold=("unseen_training_group", "sum")).reset_index()
    result["outlier_percent"] = 100 * result["iqr_outliers"] / result["observations"]
    thresholds.to_csv(OUTPUT / "iqr_thresholds_train.csv", index=False)
    return result


def compare_versions(frame):
    raw, _ = read_chunks(RAW / "v1_full.csv")
    old, old_audit = validate_frame(raw, "v1")
    start, end = old["timestamp"].min(), old["timestamp"].max()
    current = frame[frame["timestamp"].between(start, end)].copy()
    old["well_id"] = old["well_id"].astype(str)
    old["parameter"] = old["parameter"].astype(str)
    joined = old[KEY + ["value", "well_type", "unit"]].merge(
        current[KEY + ["value", "well_type", "unit"]], on=KEY, how="outer",
        suffixes=("_v1", "_v2"), indicator=True, validate="one_to_one")
    matched = joined["_merge"].eq("both")
    joined["absolute_change"] = (joined["value_v2"] - joined["value_v1"]).abs()
    # v1 was rounded to four decimals. Half a rounding unit avoids counting
    # representation-only differences as substantive release differences.
    tolerance = 5.1e-5
    changed = matched & ~np.isclose(joined["value_v1"], joined["value_v2"], rtol=0, atol=tolerance)
    strict_changed = matched & ~np.isclose(joined["value_v1"], joined["value_v2"], rtol=0, atol=1e-6)
    metadata_changed = matched & ((joined["unit_v1"] != joined["unit_v2"]) |
                                 (joined["well_type_v1"] != joined["well_type_v2"]))
    examples = joined.loc[changed].sort_values("absolute_change", ascending=False).head(100)
    examples.to_csv(OUTPUT / "v1_v2_changed_examples.csv", index=False)
    joined.loc[~matched].head(100).to_csv(OUTPUT / "v1_v2_unmatched_examples.csv", index=False)
    summary = {
        "v1_rows": int(len(old)), "v2_rows_in_v1_horizon": int(len(current)),
        "overlap_start": str(start), "overlap_end": str(end),
        "matched_keys": int(matched.sum()), "only_v1_keys": int(joined["_merge"].eq("left_only").sum()),
        "only_v2_keys": int(joined["_merge"].eq("right_only").sum()),
        "changed_values": int(changed.sum()), "unchanged_values": int((matched & ~changed).sum()),
        "metadata_changes": int(metadata_changed.sum()), "absolute_tolerance": tolerance,
        "changed_values_at_strict_tolerance_1e_6": int(strict_changed.sum()),
        "v2_rows_outside_v1_horizon": int(len(frame) - len(current)),
        "maximum_absolute_change": float(joined.loc[matched, "absolute_change"].max()),
        "v1_validation": old_audit,
        "interpretation": "A release consistency audit, not a ground-truth accuracy test. The releases may differ in aggregation or preparation. No automatic replacement is made.",
    }
    (OUTPUT / "v1_v2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def known_issue_tables(frame):
    """Describe known changes without inventing a physical calibration factor."""
    area = frame[frame["parameter"] == "dynamometer_area"].copy()
    # April and 9–31 May avoid the later NK-7 June regime change. NK-82's
    # documented shift occurs May 8, later than the other wells.
    before = area[area["timestamp"].between("2026-04-01", "2026-04-30 23:00")]
    after = area[area["timestamp"].between("2026-05-09", "2026-05-31 23:00")]
    a = before.groupby("well_id", observed=True)["value"].median().rename("april_median")
    b = after.groupby("well_id", observed=True)["value"].median().rename("may_9_31_median")
    scale = pd.concat([a, b], axis=1).reset_index()
    scale["median_ratio"] = scale["may_9_31_median"] / scale["april_median"].replace(0, np.nan)
    scale.to_csv(OUTPUT / "area_scale_review.csv", index=False)
    nk7 = frame[(frame["well_id"] == "NK-7") & (frame["parameter"] == "SPM")].copy()
    nk7["zero"] = nk7["value"].eq(0)
    regime = nk7.groupby("regime", observed=True).agg(
        observations=("value", "size"), median_spm=("value", "median"), zero_hours=("zero", "sum")).reset_index()
    regime["zero_percent"] = 100 * regime["zero_hours"] / regime["observations"]
    regime.to_csv(OUTPUT / "nk7_regime_review.csv", index=False)
    return scale, regime
