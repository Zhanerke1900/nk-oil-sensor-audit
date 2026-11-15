"""Reproducible figures for the report and an offline interactive chart.

Every chart uses the observed values. No forward fill or invented readings are
drawn. Descriptive full-period plots are separate from train-only IQR fitting.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
COLORS = ["#126B77", "#E28B43", "#38558F", "#8D5A97", "#608953", "#BC4A57", "#7A756D"]


def save_figure(figure: plt.Figure, name: str) -> None:
    folder = ROOT / "outputs" / "figures"
    folder.mkdir(parents=True, exist_ok=True)
    figure.savefig(folder / f"{name}.png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def coverage_plot(frame: pd.DataFrame) -> None:
    """Only actual configured series enter the 6,552-hour denominator."""
    counts = frame.groupby(["well_id", "parameter"], observed=True).size().unstack()
    missing = (1 - counts / 6552) * 100
    missing = missing.reindex(sorted(missing.index, key=lambda x: int(str(x).split("-")[-1])))
    figure, axis = plt.subplots(figsize=(11.5, 6))
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad("#E8EBED")
    heat = axis.imshow(missing.to_numpy(), cmap=cmap, vmin=0, vmax=50, aspect="auto")
    axis.set_xticks(range(len(missing.columns)), [str(x).replace("_", "\n") for x in missing.columns], fontsize=9)
    axis.set_yticks(range(len(missing)), missing.index)
    axis.set_title("Missing hourly measurements by active sensor series", loc="left", pad=18)
    for row in range(len(missing)):
        for column in range(len(missing.columns)):
            value = missing.iloc[row, column]
            axis.text(column, row, "N/A" if pd.isna(value) else f"{value:.1f}%",
                      ha="center", va="center", fontsize=10,
                      color="white" if pd.notna(value) and value > 32 else "#172C40")
    figure.colorbar(heat, ax=axis, label="Missing expected hours (%)", shrink=.85)
    figure.text(.08, -.01, "Jan–Sep 2026. Each active series expects 6,552 hours. Grey cells are not applicable.", fontsize=9)
    save_figure(figure, "01_missing_measurements")


def flag_plot(frame: pd.DataFrame) -> None:
    flagged = frame.loc[frame["flag"].astype(str).ne(""), ["well_id", "flag"]].copy()
    flagged["flag"] = flagged["flag"].astype(str).str.split(";")
    counts = flagged.explode("flag").groupby(["well_id", "flag"], observed=True).size().unstack(fill_value=0)
    figure, axis = plt.subplots(figsize=(10, 4.8))
    counts.plot.bar(stacked=True, ax=axis, color=COLORS, width=.7, rot=0)
    axis.set(title="Source quality flags by well", xlabel="Well", ylabel="Flag occurrences")
    axis.legend(title="Source flag", frameon=False, bbox_to_anchor=(1.01, 1))
    axis.grid(axis="y", alpha=.2)
    figure.text(.1, -.01, "Compound flags count in both categories. A flag is an audit signal, not a verified equipment failure.", fontsize=9)
    save_figure(figure, "02_source_flags")


def area_plot(frame: pd.DataFrame) -> None:
    area = frame.loc[frame["parameter"].eq("dynamometer_area")].copy()
    area["date"] = area["timestamp"].dt.floor("D")
    daily = area.groupby(["date", "well_id"], observed=True)["value"].median().unstack()
    daily = daily.reindex(pd.date_range("2026-01-01", "2026-09-30", freq="D"))
    figure, axis = plt.subplots(figsize=(11, 5.1))
    for color, well in zip(COLORS, daily.columns):
        axis.plot(daily.index, daily[well], label=well, color=color, lw=1.3, alpha=.88)
    axis.axvline(pd.Timestamp("2026-05-01"), color="#60676F", ls="--", lw=1)
    axis.axvline(pd.Timestamp("2026-05-08"), color="#A6ABB0", ls=":", lw=1)
    axis.set_yscale("symlog", linthresh=10000)
    axis.set(title="Dynamometer area changes scale during May", ylabel="Daily median area (source unit, symmetric log scale)")
    axis.legend(ncol=4, frameon=False, loc="upper left")
    axis.grid(alpha=.15)
    figure.text(.1, -.01, "Dashed: May 1. Dotted: May 8 (NK-82). Values remain unchanged; the cause and correction factor are unverified.", fontsize=9)
    save_figure(figure, "03_area_scale")


def regime_plot(frame: pd.DataFrame) -> None:
    data = frame.loc[frame["well_id"].eq("NK-7") & frame["parameter"].eq("SPM")].copy()
    data["date"] = data["timestamp"].dt.floor("D")
    data["zero"] = data["value"].eq(0)
    days = pd.date_range("2026-01-01", "2026-09-30", freq="D")
    daily = data.groupby("date").agg(median_spm=("value", "median"), zero_pct=("zero", lambda x: x.mean()*100)).reindex(days)
    figure, axes = plt.subplots(2, 1, figsize=(10.5, 5.5), sharex=True)
    axes[0].plot(daily.index, daily.median_spm, color=COLORS[0], lw=1.5)
    axes[0].set(title="NK-7 shows a different operating or sensor regime from June", ylabel="Daily median SPM\n(strokes/min)")
    axes[1].plot(daily.index, daily.zero_pct, color=COLORS[1], lw=1.5)
    axes[1].set(ylabel="Zero SPM among\nobserved hours (%)", ylim=(-2, 102))
    for axis in axes:
        axis.axvline(pd.Timestamp("2026-06-01"), color="#60676F", ls="--", lw=1)
        axis.grid(alpha=.2)
    figure.text(.1, -.01, "Zero readings are retained. Missing hours do not enter the zero-rate denominator.", fontsize=9)
    save_figure(figure, "04_nk7_regime")


def correlation_plot(frame: pd.DataFrame) -> None:
    """Within-well centering reduces between-well mean confounding."""
    filtered = frame.loc[frame["flag"].astype(str).eq("")].copy()
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 5))
    settings = [
        ("fountain", ["tubing_pressure", "casing_pressure", "line_pressure"], "Fountain wells"),
        ("sucker_rod_pump", ["SPM", "pump_fillage", "min_rod_weight", "max_rod_weight"], "Sucker-rod pump wells"),
    ]
    for axis, (well_type, parameters, title) in zip(axes, settings):
        data = filtered.loc[filtered.well_type.eq(well_type) & filtered.parameter.isin(parameters)]
        wide = data.pivot(index=["well_id", "timestamp"], columns="parameter", values="value").reindex(columns=parameters)
        centered = wide - wide.groupby(level="well_id", observed=True).transform("mean")
        correlation = centered.corr(min_periods=100)
        image = axis.imshow(correlation, cmap="RdBu_r", vmin=-1, vmax=1)
        labels = [p.replace("_", "\n") for p in parameters]
        axis.set_xticks(range(len(labels)), labels, fontsize=9)
        axis.set_yticks(range(len(labels)), labels, fontsize=9)
        axis.set_title(title, pad=12)
        for row in range(len(parameters)):
            for col in range(len(parameters)):
                value = correlation.iloc[row, col]
                axis.text(col, row, f"{value:.2f}", ha="center", va="center", color="white" if abs(value)>.65 else "#142C40")
    figure.subplots_adjust(wspace=.65, bottom=.21, top=.88)
    figure.text(.08, .05, "Pearson correlations after within-well centering, unflagged observed values, pairwise complete hours.\nDynamometer area is excluded because its scale changes. Correlation does not establish causation.", fontsize=9)
    save_figure(figure, "05_correlations")


def diurnal_plot(frame: pd.DataFrame) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for axis, parameter, title, unit, color in zip(
        axes, ["SPM", "tubing_pressure"], ["Sucker-rod pumps", "Fountain wells"], ["strokes/min", "atm"], COLORS
    ):
        data = frame.loc[frame.parameter.eq(parameter)].copy()
        data["hour"] = data.timestamp.dt.hour
        stats = data.groupby("hour")["value"].agg(median="median", q25=lambda x: x.quantile(.25), q75=lambda x: x.quantile(.75))
        axis.plot(stats.index, stats["median"], color=color, lw=2)
        axis.fill_between(stats.index, stats.q25, stats.q75, color=color, alpha=.18)
        axis.set(title=title, xlabel="Hour of recorded timestamp", ylabel=f"{parameter} ({unit})", xticks=[0, 6, 12, 18, 23])
        axis.grid(alpha=.15)
    figure.suptitle("Hour-of-day profiles", x=.1, ha="left", y=1.03)
    figure.text(.1, -.05, "Line: pooled median. Band: 25th–75th percentile. Well mix and unequal coverage can affect these descriptive profiles.", fontsize=9)
    save_figure(figure, "06_hourly_profiles")


def interactive_plot(frame: pd.DataFrame) -> None:
    figure = go.Figure()
    selected = frame.loc[frame.parameter.eq("SPM")]
    hours = pd.date_range("2026-01-01", "2026-09-30 23:00", freq="h")
    wells = sorted(selected.well_id.unique(), key=lambda x: int(str(x).split("-")[-1]))
    for index, well in enumerate(wells):
        data = selected.loc[selected.well_id.eq(well)].set_index("timestamp").reindex(hours)
        figure.add_trace(go.Scatter(x=data.index, y=data.value, mode="lines", name=str(well),
                                   connectgaps=False, visible=index == 0, line={"color": COLORS[index % len(COLORS)], "width": 1}))
    buttons = [dict(label=str(well), method="update", args=[{"visible": [j == i for j in range(len(wells))]}, {"title": f"Hourly SPM — {well}"}]) for i, well in enumerate(wells)]
    figure.update_layout(title=f"Hourly SPM — {wells[0]}", template="plotly_white", height=600,
                         yaxis_title="SPM (strokes/min)", xaxis_title="Timestamp (source has no timezone)",
                         updatemenus=[dict(buttons=buttons, x=1, xanchor="right", y=1.13)],
                         xaxis={"rangeslider": {"visible": True}}, margin={"t": 100})
    figure.add_shape(type="line", x0="2026-08-08 23:00", x1="2026-08-08 23:00", y0=0, y1=1, yref="paper", line={"color": "#BD5C3A", "dash": "dash"})
    figure.add_annotation(x="2026-08-08 23:00", y=1, yref="paper", text="Official test begins", showarrow=False, yshift=18)
    figure.write_html(ROOT / "outputs" / "interactive_spm.html", include_plotlyjs=True, full_html=True)


def build_figures(frame: pd.DataFrame, summary: dict | None = None) -> None:
    """Called by main.py after the ETL succeeds."""
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["flag"] = frame["flag"].fillna("").astype(str)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 14,
                         "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#283A4A", "text.color": "#172C40"})
    for function in [coverage_plot, flag_plot, area_plot, regime_plot, correlation_plot, diurnal_plot]:
        function(frame)
    interactive_plot(frame)


if __name__ == "__main__":
    build_figures(pd.read_parquet(ROOT / "data" / "processed" / "observations.parquet"))
