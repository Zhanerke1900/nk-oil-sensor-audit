---
license: apache-2.0
task_categories:
  - time-series-forecasting
tags:
  - oil-and-gas
  - well-monitoring
  - sensor-data
  - time-series
  - industrial
  - predictive-maintenance
pretty_name: "Oil Well Sensor Monitoring Dataset - NK Field"
size_categories:
  - 100K<n<1M
---

# Oil Well Sensor Monitoring Dataset - NK Field

## Dataset Description

This dataset contains hourly sensor readings from 10 oil wells at the NK field.

The monitoring period covers approximately seven months, from January 1, 2026, to July 20, 2026.

The data were provided by **Galaz and Company LLP**
(**ТОО «Галаз и Компания»**) within the research project:

**“Development and Implementation of Control Algorithms for Low-Production-Rate Wells in Mechanized Oil Production Systems, Including Plunger Lift and Sucker-Rod Pump Systems, Using Artificial Intelligence Methods.”**

The dataset was prepared for research on artificial intelligence methods for monitoring, forecasting, anomaly detection, predictive maintenance, and control of low-production-rate oil wells.

## Dataset Summary

* Number of wells: 10
* Monitoring period: January 1, 2026 - July 20, 2026
* Sampling frequency: hourly
* Total number of rows: 186,251
* Fountain wells: 3
* Sucker-rod pump wells: 7
* Data format: long tabular format
* Train and test split: chronological

## Wells Included

| Well ID | Well type       | Recorded parameters                                                         |
| ------- | --------------- | --------------------------------------------------------------------------- |
| NK-75   | fountain        | tubing pressure, casing pressure, line pressure                             |
| NK-76   | fountain        | tubing pressure, line pressure                                              |
| NK-83   | fountain        | tubing pressure, casing pressure, line pressure                             |
| NK-7    | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-68   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-77   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-82   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-86   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-91   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |
| NK-93   | sucker-rod pump | SPM, pump fillage, minimum rod weight, maximum rod weight, dynamometer area |

NK-76 does not contain casing-pressure measurements because this parameter was not recorded in the original source files.

## Dataset Structure

The dataset is provided in long, tidy format.

Each row represents one parameter observation for one well at one timestamp.

| Field       | Type     | Description                    |
| ----------- | -------- | ------------------------------ |
| `well_id`   | string   | Unique well identifier         |
| `well_type` | string   | Well operating type            |
| `timestamp` | datetime | Hourly observation timestamp   |
| `parameter` | string   | Name of the measured parameter |
| `value`     | float    | Recorded sensor value          |
| `unit`      | string   | Unit of measurement            |

## Parameters

| Parameter          | Unit        | Applicable well type |
| ------------------ | ----------- | -------------------- |
| `tubing_pressure`  | atm         | fountain             |
| `casing_pressure`  | atm         | fountain             |
| `line_pressure`    | atm         | fountain             |
| `SPM`              | strokes/min | sucker-rod pump      |
| `pump_fillage`     | %           | sucker-rod pump      |
| `min_rod_weight`   | kg          | sucker-rod pump      |
| `max_rod_weight`   | kg          | sucker-rod pump      |
| `dynamometer_area` | unitless    | sucker-rod pump      |

## Dataset Files

The repository contains the following files:

| File                | Description                        |
| ------------------- | ---------------------------------- |
| `wells_dataset.csv` | Complete dataset without splitting |
| `train.csv`         | Chronological training split       |
| `test.csv`          | Chronological testing split        |

## Data Splits

The dataset was divided chronologically without random shuffling.

This split strategy prevents future observations from leaking into the training data and reflects a realistic forecasting scenario.

| Split |    Rows | Date range                           | Approximate share |
| ----- | ------: | ------------------------------------ | ----------------: |
| Train | 148,308 | 2026-01-01 00:00 to 2026-06-09 23:00 |               80% |
| Test  |  37,943 | 2026-06-10 00:00 to 2026-07-20 00:00 |               20% |

## Research Context

The dataset was prepared within the research project:

**“Development and Implementation of Control Algorithms for Low-Production-Rate Wells in Mechanized Oil Production Systems, Including Plunger Lift and Sucker-Rod Pump Systems, Using Artificial Intelligence Methods.”**

The research focuses on the development of intelligent methods for monitoring and controlling low-production-rate wells.

The main research directions include:

* monitoring of low-production-rate wells;
* analysis of fountain wells;
* analysis of sucker-rod pump wells;
* analysis of mechanized oil production systems;
* detection of abnormal operating conditions;
* prediction of pressure and equipment parameters;
* predictive maintenance;
* artificial intelligence-based well control;
* decision support for oil production systems;
* optimization of low-production-rate well operation.

## Data Provider

**Organization:** Galaz and Company LLP

**Russian name:** ТОО «Галаз и Компания»

**Industry:** Oil and gas

**Data type:** Industrial well-monitoring, SCADA, telemetry, and dynamometer data

**Research purpose:** Development and evaluation of artificial intelligence algorithms for monitoring and controlling low-production-rate wells

## Data Processing

The original data were provided as separate Microsoft Excel files for individual wells and monitoring periods.

The following preprocessing steps were performed:

* consolidation of multiple source files;
* standardization of well identifiers;
* standardization of parameter names;
* conversion into a unified long-format table;
* chronological ordering of observations;
* removal of overlapping duplicate timestamps;
* assignment of well types;
* creation of chronological training and testing subsets.

No automatic missing-value imputation was applied.

No systematic outlier removal or correction was applied.

## Potential Tasks

The dataset can be used for:

* time-series forecasting;
* multivariate sensor forecasting;
* pressure trend prediction;
* anomaly detection;
* outlier detection;
* missing-data analysis;
* well shut-in detection;
* operating-mode classification;
* equipment condition monitoring;
* sucker-rod pump monitoring;
* predictive maintenance;
* low-production-rate well optimization;
* industrial artificial intelligence research;
* benchmarking of machine learning models;
* decision-support system development.

## Data Quality Notes

Users should consider the following data-quality limitations:

* The timestamps in the original source files did not contain an explicit year.
* The year 2026 was assigned based on the sequential order of monthly source files.
* The assigned year should be verified against the original SCADA or telemetry system before time-sensitive operational use.
* Missing readings are represented by absent rows rather than explicit null values.
* NK-76 has no casing-pressure measurements.
* NK-86 has a multi-day gap in source records from April 29 to May 12, 2026.
* NK-91 has a multi-day gap in source records from January 29 to February 4, 2026.
* The `dynamometer_area` parameter for NK-7 contains extreme values, including negative readings.
* Some extreme values may represent sensor, telemetry, or export artifacts.
* Overlapping timestamps at monthly file boundaries were deduplicated by keeping the first occurrence.
* The dataset has not undergone automatic outlier correction.
* The dataset has not undergone automatic missing-value imputation.

## Intended Use

The dataset is intended for scientific, educational, and experimental research in:

* artificial intelligence;
* machine learning;
* time-series analysis;
* oil and gas engineering;
* industrial monitoring;
* predictive maintenance;
* mechanized oil production;
* low-production-rate well control;
* sucker-rod pump analysis;
* intelligent decision-support systems.

The dataset should not be used as the sole source for real-time production, operational, or safety-critical decisions.

All analytical results, predictions, and control recommendations should be verified by qualified oil and gas specialists and compared with the original company monitoring systems.

## Limitations

The dataset does not contain all variables that may influence oil-well performance.

For example, it may not include:

* production rate;
* fluid composition;
* water cut;
* bottom-hole pressure;
* reservoir pressure;
* equipment maintenance history;
* intervention history;
* weather conditions;
* operator actions;
* detailed geological information.

The absence of these variables may limit the interpretation of anomalies and model predictions.

The dataset also does not contain verified labels for all equipment failures, well shutdowns, or abnormal operating modes.

## Ownership and Attribution

The original industrial data were provided by **Galaz and Company LLP (ТОО «Галаз и Компания»)** within the stated research project.

Users should acknowledge the data provider and the research context in publications, reports, presentations, and derivative research.

Publication of the dataset does not remove the obligation to comply with applicable confidentiality, data-ownership, industrial-data protection, and contractual requirements.

## Example Usage

### Load the Complete Dataset

```python
import pandas as pd

df = pd.read_csv(
    "wells_dataset.csv",
    parse_dates=["timestamp"]
)

print(df.head())
print(df.shape)
print(df.columns)
print(df["well_id"].unique())
```

### Load Train and Test Splits

```python
import pandas as pd

train = pd.read_csv(
    "train.csv",
    parse_dates=["timestamp"]
)

test = pd.read_csv(
    "test.csv",
    parse_dates=["timestamp"]
)

print("Train period:")
print(train["timestamp"].min())
print(train["timestamp"].max())

print("Test period:")
print(test["timestamp"].min())
print(test["timestamp"].max())
```

### Select Fountain Wells

```python
fountain_wells = df[
    df["well_type"] == "fountain"
]

print(fountain_wells.head())
print(fountain_wells["well_id"].unique())
```

### Select Sucker-Rod Pump Wells

```python
pump_wells = df[
    df["well_type"] == "sucker_rod_pump"
]

print(pump_wells.head())
print(pump_wells["well_id"].unique())
```

### Convert One Well to Wide Format

```python
nk75 = (
    df[df["well_id"] == "NK-75"]
    .pivot(
        index="timestamp",
        columns="parameter",
        values="value"
    )
    .sort_index()
)

print(nk75.head())
```

### Compare Tubing Pressure Across Fountain Wells

```python
fountain_pressure = df[
    (df["well_type"] == "fountain")
    & (df["parameter"] == "tubing_pressure")
]

pressure_table = fountain_pressure.pivot(
    index="timestamp",
    columns="well_id",
    values="value"
)

pressure_table.plot(
    title="Tubing Pressure of Fountain Wells"
)
```

### Analyze Missing Hourly Observations

```python
well_data = df[
    df["well_id"] == "NK-75"
].copy()

hourly_grid = pd.date_range(
    start=well_data["timestamp"].min(),
    end=well_data["timestamp"].max(),
    freq="h"
)

wide_data = well_data.pivot(
    index="timestamp",
    columns="parameter",
    values="value"
)

wide_data = wide_data.reindex(hourly_grid)

print(wide_data.isna().sum())
```

## License

The dataset is released under the **Apache License 2.0**.

Users must also comply with applicable data-ownership, confidentiality, industrial-data protection, and contractual requirements associated with the original data.

## Citation

Please cite the dataset as follows:

```bibtex
@dataset{tleubayeva_2026_nk_well_monitoring,
  author       = {Arailym Tleubayeva},
  title        = {Oil Well Sensor Monitoring Dataset: NK Field},
  year         = {2026},
  publisher    = {Hugging Face},
  organization = {Galaz and Company LLP},
  note         = {Dataset prepared within a research project on artificial intelligence-based control algorithms for low-production-rate wells},
  url          = {https://huggingface.co/datasets/Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring}
}
```

## Acknowledgements

The dataset author acknowledges **Galaz and Company LLP (ТОО «Галаз и Компания»)** for providing the industrial well-monitoring data used within the research project:

**“Development and Implementation of Control Algorithms for Low-Production-Rate Wells in Mechanized Oil Production Systems, Including Plunger Lift and Sucker-Rod Pump Systems, Using Artificial Intelligence Methods.”**

## Contact

For questions, corrections, or research collaboration, please use the Community section of the Hugging Face dataset repository.
