# Sensor Data Quality Audit and ETL Pipeline

**Final project 19 · Programming for Data Analysis and Database**  
**Team:** Amina Tuzelova, Alua Nurlybekova, Zhanerke Pernesh  
**Group:** AAI-2606M

This Python project audits the NK Oil Well Sensor Monitoring v2 dataset, compares
it with v1, and loads the validated observations into a normalized SQLite
database. It includes a Streamlit dashboard, an offline Plotly chart, an English
report and a presentation. Russian start and defense notes are in `docs/`.

## Main findings

- 258,387 observed measurements across 10 wells and 43 applicable sensor series.
- 23,349 absent hourly measurements out of 281,736 expected, or **8.29%**.
- 7,041 source-flagged rows, or **2.72%** of observed rows.
- Interior gaps account for 21,014 missing hours. Boundary gaps account for 2,335.
- All 186,251 v1 observation keys remain in v2. Within the v1 time horizon, v2
  adds 963 keys and changes 160,674 matched values beyond an absolute tolerance
  of 0.000051. This is a release-consistency finding, not an accuracy score.
- Python, Pandas and SQLite detect exactly the same 1,677 interior gap intervals.

These are measured outputs from the included source snapshot. Runtime values in
`outputs/benchmark.csv` are specific to the recorded execution environment.

## Quick start on Windows PowerShell

Install **Python 3.12** first. Extract the ZIP and open a terminal in this folder
(the folder containing `main.py`). Run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download.py
.\.venv\Scripts\python.exe main.py --run
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The download step verifies existing raw CSV files in the complete ZIP. When they
are absent, it downloads the public sources at fixed revisions. The program
prints a local dashboard URL, normally `http://localhost:8501`. Keep the terminal
open and press `Ctrl+C` to stop the dashboard. Virtual-environment activation is
unnecessary, so no PowerShell execution-policy change is required.

## Linux or macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python download.py
.venv/bin/python main.py --run
.venv/bin/python -m streamlit run app.py
```

Dependencies are listed with exact versions in `requirements.txt`. The pipeline
was executed on Python 3.12.14, pandas 2.2.3 and SQLite from the Python runtime.
No database server, password or API key is needed.

## Other ways to use the project

```bash
python main.py --menu    # Interactive console operations
python main.py --sql     # Re-export the 12 analytical SQL results
python -m unittest discover -s tests -v
```

`walkthrough.ipynb` explains the workflow and can run in Jupyter or Google Colab.
The notebook uses the same modules as the command-line program. Open
`outputs/interactive_spm.html` in a browser to inspect the saved interactive
chart offline, without Streamlit or a Python installation.

## Project files

| Path | Purpose |
|---|---|
| `download.py` | Pinned source downloads and SHA-256 validation |
| `main.py` | Command-line entry point and interactive console menu |
| `src/ingestion.py` | Chunked reading, schema checks, official split validation, dtype optimization |
| `src/quality.py` | Hourly completeness, flags, train-only IQR, daily and hourly descriptive summaries |
| `src/database.py` | Normalized schema and 12 SQL queries |
| `src/benchmarks.py` | Equivalent gap-detection methods and measured timing |
| `src/pipeline.py` | Reproducible orchestration and result export |
| `src/visualization.py` | Six static figures and the offline Plotly chart |
| `app.py` | Dashboard filters, charts and SQL result viewer |
| `data/raw/` | Unmodified source CSVs, source cards and checksum manifest |
| `data/processed/observations.parquet` | Validated long-format data with audit annotations |
| `data/processed/wide.parquet` | Hourly wide representation for analysis |
| `data/processed/wells.db` | SQLite database |
| `sql/` | Schema and executable analytical queries |
| `outputs/` | Audit tables, benchmark, figures and actual run summary |
| `docs/report.docx` | Written report |
| `docs/presentation.pptx` | Editable presentation |
| `docs/START_HERE_RU.md` | Short Russian run instructions |
| `docs/DEFENSE_RU.md` | Project explanation and likely defense questions |
| `docs/TEAM_CONTRIBUTIONS.md` | Proposed division of work to confirm |

## Audit rules

The observation key is `(well_id, parameter, timestamp)`. The pipeline rejects
invalid schemas, inconsistent units, non-hourly times and conflicting duplicate
keys. It removes exact duplicate records only if present. The supplied files
contain no duplicates or missing numeric values in existing rows.

Missingness is measured against the documented hourly horizon, January 1 through
September 30, 2026. Only applicable well–parameter pairs enter the denominator.
For example, NK-76 does not record casing pressure. Wide-table structural nulls
must not be counted as data loss. Ordinary SQL `LAG` finds only interior gaps,
so the pipeline separately checks leading and trailing gaps.

Source flags are computed before hourly aggregation and can describe an hourly
mean that does not exceed the corresponding raw threshold. The original flag
string and normalized individual flags are both retained. Compound categories
overlap. Zero readings remain in the dataset. The program performs no automatic
imputation, outlier deletion or guessed scale correction.

Scale-period and NK-7 regime fields annotate known concerns. An IQR rule fitted
on the official training interval provides separate statistical screening.
Those review flags do not establish equipment failure. Descriptive plots use the
full period and do not train a forecasting model.

## Baseline and two methods

The assignment permits processing-time comparisons for this cluster. The
experiment compares a Python loop baseline, Pandas `groupby().shift()` with subtraction and SQLite
`LAG()` for **the same interior-gap detection problem**. The official chronological
split is preserved. No unrelated classifier is required for this ETL topic.

The timing experiment uses prepared inputs, warm execution and a median of three
uninstrumented runs. Initial CSV reading, shared sorting, Python record conversion,
database construction and indexing are excluded. Output conversion is included.
This measures the detection step, not end-to-end ETL throughput.

A separate `tracemalloc` run records incremental Python-traced allocations.
Prepared inputs and much of SQLite's native memory are outside that measurement.
These memory values must not be described as total RAM or used to claim that SQL
has the smallest overall memory footprint. Actual equality of all output tuples
is checked. No precision, recall or MAE is invented because the dataset supplies
no verified equipment-failure labels and this project does not forecast values.

## SQL and relationships

Six tables represent wells, parameters, applicable series, observations, flag
names and observation–flag links. The `(well_id, parameter)` foreign key prevents
observations for inapplicable sensors. The observation key has a uniqueness
constraint. Foreign keys and SQLite integrity checks run during export.

See `docs/er_diagram.mmd`, `docs/er_diagram.png` and `sql/schema.sql`.
The 12 queries include joins, aggregation, `HAVING`, a subquery, CTEs and window
functions. The program reads results into Pandas and writes them to
`outputs/sql/`, where the dashboard can display them.

## Before submission

1. Run the project on the laptop that will be used for the defense.
2. Replace the proposed contribution allocation with each person's actual work
   in the report and presentation.
3. Review the Russian defense notes and rehearse the dashboard demonstration.
4. Create your own GitHub repository and upload the code. `.gitignore` omits
   generated large data and databases; `download.py` recreates the inputs.
5. Add the actual repository URL to the report/presentation if your teacher
   requires it. Do not invent a URL or commit history.
6. Upload the report and presentation to Moodle at least 2–3 days before the
   final exam, as required in the assignment. Confirm the exam date yourself.

The attached assignment explicitly lists topic 19 among the dataset-size
exceptions. Artificially duplicating rows to reach 500,000 would damage the
analysis and is unnecessary. Follow your university's rules for assistance and
be prepared to explain every module.

## Data source and limitations

Sources, attribution and pinned revisions are documented in `DATA_SOURCES.md`.
The provider is Galaz and Company LLP. The source assigns the year 2026 from file
order; timestamps should be checked against SCADA before operational use. The
cause of the May scale change and many cross-version discrepancies remains
unverified. The final table fits in memory; chunked parsing does not make all
subsequent analyses out of core.
