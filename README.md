# Sensor Data Quality Audit and ETL Pipeline

[![Python tests](https://github.com/Zhanerke1900/nk-oil-sensor-audit/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Zhanerke1900/nk-oil-sensor-audit/actions/workflows/tests.yml)

**Final Project 19 · Programming for Data Analysis and Database**  
**Team:** Amina Tuzelova, Alua Nurlybekova, Zhanerke Pernesh  
**Group:** AAI-2606M

This Python project audits the NK Oil Well Sensor Monitoring v2 dataset, compares
it with v1, and loads validated observations into a normalized SQLite database.
It includes a Streamlit dashboard, an offline interactive Plotly chart, a written
report, and a presentation.

## Main findings

- **258,387 recorded measurements** across 10 wells and 43 applicable sensor series.
- **23,349 missing hourly measurements** out of 281,736 expected (**8.29%**).
- **7,041 source-flagged rows** (**2.72%** of recorded measurements).
- Interior gaps account for 21,014 missing hours; boundary gaps account for 2,335.
- All 186,251 v1 observation keys remain in v2. Within the v1 time horizon, v2
  adds 963 keys and changes 160,674 matched values beyond an absolute tolerance
  of 0.000051. This measures agreement between dataset releases, not sensor accuracy.
- Python, Pandas, and SQLite identify the same **1,677 interior gap intervals**.

These results were calculated from the dataset revisions listed in
[`DATA_SOURCES.md`](DATA_SOURCES.md). Execution times in
`outputs/benchmark.csv` depend on the machine and runtime environment.

## Quick start on Windows PowerShell

Install **Python 3.12** and open a terminal in the project directory (the folder
containing `main.py`):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download.py
.\.venv\Scripts\python.exe main.py --run
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`download.py` verifies existing source CSVs when present, or downloads the public
sources at pinned revisions and checks their SHA-256 hashes. The Streamlit
command prints the dashboard URL (normally `http://localhost:8501`). Keep the
terminal open while using the dashboard; press `Ctrl+C` to stop it. Activation
of the virtual environment is optional because the commands use its Python
executable directly.

## Linux or macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python download.py
.venv/bin/python main.py --run
.venv/bin/python -m streamlit run app.py
```

Library versions are pinned in `requirements.txt`. The pipeline was executed
using Python 3.12.14, pandas 2.2.3, and SQLite provided by the Python runtime.
No separate database server, password, or API key is required.

## Other ways to use the project

From the project directory, with the virtual environment activated (or replace
`python` with the virtual environment's Python executable):

```bash
python main.py --menu     # Interactive console operations
python main.py --sql      # Re-export results of the 12 SQL queries
python main.py --summary  # Inspect saved results without rerunning ETL
python -m unittest discover -s tests -v
```

`--summary` reads `outputs/summary.json` without rerunning the pipeline or updating
benchmark times. It does not generate the data files required by the dashboard;
use `python main.py --run` to build those files first.

For setup and launch errors, see the [troubleshooting guide in Russian](docs/TROUBLESHOOTING_RU.md).

`walkthrough.ipynb` describes the processing workflow and runs in Jupyter or
Google Colab using the same Python modules as the command-line program.
Open `outputs/interactive_spm.html` in a browser to view the saved Plotly chart
offline, without running Streamlit.

## Dashboard features

- Filter measurements by well, parameter, date range, and train/test split.
- View expected, observed, and missing hours, flagged rows, and data completeness.
- Completeness is calculated as observed hours / expected hours × 100% for the
  selected well, parameter, period, and split, and is unaffected by the flag filter.
- Read parameter descriptions and measurement units in the sidebar.
- Explore time series, missing data, quality flags, saved SQL results, and method comparisons.

## Project files

| Path | Purpose |
|---|---|
| `download.py` | Pinned source downloads and SHA-256 verification |
| `main.py` | Command-line entry point and interactive console menu |
| `src/ingestion.py` | Chunked reading, schema validation, split checks, data-type optimization |
| `src/quality.py` | Hourly completeness, source flags, train-only IQR, descriptive summaries |
| `src/database.py` | Normalized schema and 12 SQL queries |
| `src/benchmarks.py` | Three equivalent gap-detection methods and runtime/memory measurements |
| `src/pipeline.py` | Processing pipeline and export of results |
| `src/visualization.py` | Six static figures and an interactive Plotly chart |
| `app.py` | Dashboard filters, charts, and SQL result viewer |
| `data/raw/` | Source CSVs, source descriptions, and checksums (downloaded locally) |
| `data/processed/observations.parquet` | Validated long-format data with audit annotations (generated) |
| `data/processed/wide.parquet` | Hourly wide-format data (generated) |
| `data/processed/wells.db` | SQLite database (generated) |
| `sql/` | Database schema and analytical SQL queries |
| `outputs/` | Audit tables, benchmark data, figures, and processing summary |
| `walkthrough.ipynb` | Notebook with exploration of data and results |
| `docs/er_diagram.png`, `docs/er_diagram.mmd` | Database ER diagram |
| [docs/DASHBOARD_GUIDE_RU.md](docs/DASHBOARD_GUIDE_RU.md) | Dashboard demonstration guide in Russian |
| `docs/report.docx` | Written report |
| `docs/presentation.pptx` | Editable presentation |
| `DATA_SOURCES.md` | Data source links, attribution, and revision information |

Generated CSV, Parquet, and SQLite files can be recreated by `download.py` and
`main.py --run` and do not need to be committed to the repository.

## Audit rules

The unique observation key is `(well_id, parameter, timestamp)`. The pipeline
checks the input schema, measurement units, hourly timestamps, and duplicate
keys. It rejects conflicting records and removes exact duplicates if any are
found. The source snapshots contain no duplicate keys or missing numeric values
in existing measurement rows.

Missingness is evaluated against the documented hourly period from **January 1
to September 30, 2026**, considering only the well–sensor pairs for which a
measurement is applicable. For example, NK-76 does not record casing pressure.
Nulls for structurally inapplicable sensors in the wide table do not represent
missing measurements. SQL `LAG()` detects gaps between recorded observations;
leading and trailing gaps are counted separately.

Source quality flags are computed before hourly aggregation. A flagged hourly
observation may have a mean value that does not itself exceed the threshold
that triggered a flag. The original flag string and normalized individual flags
are preserved. Compound flag categories may overlap. Zero readings are kept.
The pipeline does not automatically impute missing measurements, remove
outliers, or alter values to compensate for the known scale change.

The audit marks the reported **May 2026 change in `dynamometer_area` scale**
and the **June 2026 operating-regime change for NK-7** for separate review.
An IQR rule fitted only on the chronological training period supplies an
additional statistical screening indicator. These flags do not by themselves
confirm an equipment fault. The descriptive figures cover the full period;
no forecasting model is fitted.

## Baseline and two comparison methods

For gap detection, three implementations are evaluated on the **same interior-
gap task**:

1. **Python loop** — sequential baseline that checks the time difference
   between consecutive observations within each well–parameter series.
2. **Pandas** — `groupby().shift()` followed by timestamp subtraction.
3. **SQLite** — a window query using `LAG()`.

The original chronological train/test split is preserved. All three methods
produce identical sets of 1,677 interior gap intervals.

The timing benchmark uses prepared inputs, a warm-up run, and the median of
three uninstrumented runs. It excludes the initial CSV import, shared sorting,
Python record preparation, database construction, and indexing; output
conversion is included. Therefore, the benchmark compares the **gap-detection
step**, not complete ETL execution time.

Memory allocation is measured in a separate run with `tracemalloc`. The values
represent incremental Python-traced allocations, not total process RAM. In
particular, SQLite's native allocations are not fully represented. Method
agreement is verified by comparing output tuples. Because this task does not
predict sensor failures and has no verified failure labels, the comparison
uses execution time, measured allocations, and output agreement rather than
classification scores or forecasting errors.

## SQL and database relationships

The normalized SQLite database contains **six tables**: wells, parameters,
applicable well–parameter series, observations, flag types, and observation–flag
links. A foreign key on `(well_id, parameter)` prevents storing observations
for inapplicable sensor series. Observation keys have a uniqueness constraint.
The pipeline enables foreign-key enforcement and performs integrity checks.

See `docs/er_diagram.mmd`, `docs/er_diagram.png`, and `sql/schema.sql` for the
database structure. The **12 analytical SQL queries** use joins, aggregates,
`GROUP BY`/`HAVING`, subqueries, common table expressions (CTEs), and window
functions such as `LAG()`. Their results are loaded into Pandas and saved
under `outputs/sql/`, where they can also be viewed in the dashboard.

See the [SQL query guide in Russian](docs/SQL_GUIDE_RU.md) for questions and result interpretation.

## Data sources and limitations

The v2 dataset and earlier v1 release were published by Arailym Tleubayeva:

- [NK Oil Well Sensor Monitoring v2](https://huggingface.co/datasets/Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring-v2)
- [NK Oil Well Sensor Monitoring v1](https://huggingface.co/datasets/Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring)

Source attribution and pinned revisions are documented in
[`DATA_SOURCES.md`](DATA_SOURCES.md). The readings are attributed to **Galaz
and Company LLP**. The source assigns the year 2026 based on file ordering;
operational use would require verifying the timestamps against SCADA records.
The reason for the May scale change and many differences between v1 and v2
remains unverified. The full processed table fits in memory; chunked input
parsing does not make every downstream calculation out-of-core.

The course project specification lists **topic 19** among the exceptions to
the recommended dataset size of 500,000 rows or 200 MB. The original data is
analyzed without artificially duplicating measurements.
