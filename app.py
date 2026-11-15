"""Interactive inspection of the reproducible oil-well data-quality audit.

Run from the project folder with ``streamlit run app.py`` after ``main.py --run``.
The flag filter changes the displayed measurements, never the coverage count.
"""
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "processed" / "observations.parquet"
REQUIRED = {
    "well_id", "well_type", "timestamp", "parameter", "value", "unit",
    "n_obs", "flag", "split",
}


@st.cache_data(show_spinner=False)
def load_observations(path: str, modified_ns: int) -> pd.DataFrame:
    """Cache by modification time, so a rerun of the pipeline refreshes the app."""
    del modified_ns
    frame = pd.read_parquet(path)
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError("Нет обязательных столбцов: " + ", ".join(sorted(missing)))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    if frame.empty or frame["timestamp"].isna().any():
        raise ValueError("Пустой набор данных или некорректная дата.")
    if frame.duplicated(["well_id", "parameter", "timestamp"]).any():
        raise ValueError("Найдены повторные ключи well_id / parameter / timestamp.")
    frame["flag"] = frame["flag"].astype("string").fillna("").str.strip()
    return frame.sort_values(["well_id", "parameter", "timestamp"])


def coverage_table(observed: pd.DataFrame, start, end) -> pd.DataFrame:
    """Reindex one valid sensor series; row presence defines availability."""
    expected = pd.date_range(start, end, freq="h", name="timestamp")
    grid = observed.set_index("timestamp").reindex(expected)
    grid["record_present"] = expected.isin(observed["timestamp"])
    return grid


def add_marker(figure, when, label, start, end, color="#667085"):
    """Use a shape and annotation to support Plotly datetime axes consistently."""
    when = pd.Timestamp(when)
    if start <= when <= end:
        figure.add_shape(
            type="line", x0=when, x1=when, y0=0, y1=1, yref="paper",
            line={"color": color, "width": 1.5, "dash": "dot"},
        )
        figure.add_annotation(
            x=when, y=1, yref="paper", text=label, showarrow=False,
            yanchor="bottom", font={"size": 10, "color": color},
        )


def show_sql_results():
    """Show saved query results produced by the pipeline, with their SQL text."""
    files = sorted((ROOT / "outputs" / "sql").glob("*.csv"))
    st.caption("Сохранённые SQL-результаты для полного датасета.")
    if not files:
        st.info("Выполни python main.py --run, чтобы получить результаты SQL.")
        return
    chosen = st.selectbox("SQL-запрос", files, format_func=lambda p: p.stem)
    try:
        result = pd.read_csv(chosen)
        st.dataframe(result, width="stretch", hide_index=True)
        st.download_button("Скачать результат CSV", chosen.read_bytes(),
                           file_name=chosen.name, mime="text/csv")
    except pd.errors.EmptyDataError:
        st.info("Этот запрос не вернул строк.")
    except (OSError, ValueError) as exc:
        st.error(f"Не удалось прочитать результат: {exc}")
    sql_file = ROOT / "sql" / (chosen.stem + ".sql")
    if sql_file.exists():
        with st.expander("Текст SQL"):
            st.code(sql_file.read_text(encoding="utf-8"), language="sql")


def show_methods():
    st.markdown("### Python loop · Pandas diff · SQLite LAG")
    st.write(
        "Три метода ищут внутренние пропуски между соседними наблюдениями. "
        "Перед сравнением времени проверяется точное совпадение результатов. "
        "Отсутствующие часы в начале и конце периода учитываются отдельно."
    )
    st.caption(
        "Измеряется поиск на уже подготовленных данных после прогрева: "
        "медиана трёх запусков. Загрузка CSV, общая сортировка, подготовка "
        "представлений и создание базы SQLite вынесены за пределы этого замера."
    )
    benchmark = ROOT / "outputs" / "benchmark.csv"
    if benchmark.exists():
        st.dataframe(pd.read_csv(benchmark), width="stretch", hide_index=True)
    else:
        st.info("Таблица появится после запуска полного анализа.")
    st.caption(
        "Время зависит от компьютера и состояния кэша. Память, измеренная "
        "tracemalloc, отражает отслеживаемые Python-выделения; это не полная "
        "память процесса и не все внутренние буферы SQLite / Pandas."
    )
    summary = ROOT / "outputs" / "summary.json"
    if summary.exists():
        with st.expander("Полный отчёт анализа JSON"):
            try:
                st.json(json.loads(summary.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                st.warning(f"Не удалось прочитать отчёт: {exc}")


def main():
    st.set_page_config(page_title="NK Oil Wells | Data Quality", page_icon="📊", layout="wide")
    st.title("Sensor Data Quality Audit and ETL Pipeline")
    st.caption("Topic 19 · AAI-2606M · Amina Tuzelova · Alua Nurlybekova · Zhanerke Pernesh")
    if not DATA_FILE.exists():
        st.info("Сначала подготовь данные в терминале из папки проекта.")
        st.code("python download.py\npython main.py --run\nstreamlit run app.py", language="bash")
        st.stop()
    try:
        data = load_observations(str(DATA_FILE), DATA_FILE.stat().st_mtime_ns)
    except (OSError, ValueError, ImportError) as exc:
        st.error(f"Не удалось загрузить подготовленные данные: {exc}")
        st.code("python download.py\npython main.py --run", language="bash")
        st.stop()

    wells = sorted(data["well_id"].astype(str).unique())
    well = st.sidebar.selectbox("Скважина", wells, index=wells.index("NK-7") if "NK-7" in wells else 0)
    well_data = data.loc[data["well_id"] == well]
    parameters = sorted(well_data["parameter"].astype(str).unique())
    parameter = st.sidebar.selectbox("Параметр", parameters,
                                     index=parameters.index("SPM") if "SPM" in parameters else 0)
    first, last = data["timestamp"].min(), data["timestamp"].max()
    dates = st.sidebar.date_input("Период", value=(first.date(), last.date()),
                                  min_value=first.date(), max_value=last.date())
    if not isinstance(dates, (tuple, list)):
        dates = (dates, dates)
    if len(dates) != 2:
        st.info("Выбери начальную и конечную дату периода.")
        st.stop()
    split = st.sidebar.selectbox("Выборка", ["Все", "train", "test"])
    flag_filter = st.sidebar.selectbox("Флаги на графике", ["Все значения", "Без флагов", "Только с флагами"])
    start = max(pd.Timestamp(dates[0]), first)
    end = min(pd.Timestamp(dates[1]) + pd.Timedelta(hours=23), last)
    if split != "Все":
        split_times = data.loc[data["split"] == split, "timestamp"]
        if split_times.empty:
            st.info("В данных отсутствует выбранная выборка.")
            st.stop()
        start, end = max(start, split_times.min()), min(end, split_times.max())
    if start > end:
        st.info("Выбранный период не пересекается с выбранной выборкой.")
        st.stop()
    observed = well_data.loc[
        (well_data["parameter"] == parameter) & well_data["timestamp"].between(start, end)
    ].copy()
    if split != "Все":
        observed = observed.loc[observed["split"] == split]
    grid = coverage_table(observed, start, end)
    flagged = observed["flag"].ne("")
    shown = observed if flag_filter == "Все значения" else observed.loc[
        ~flagged if flag_filter == "Без флагов" else flagged
    ]
    metrics = st.columns(4)
    for column, label, value in zip(metrics,
        ["Ожидаемые часы", "Наблюдаемые часы", "Отсутствующие часы", "Строки с флагами"],
        [len(grid), int(grid["record_present"].sum()), int((~grid["record_present"]).sum()), int(flagged.sum())]):
        column.metric(label, f"{value:,}")
    st.caption("Полнота рассчитана до фильтрации по флагам, для одной выбранной пары скважина–параметр.")
    chart_tab, gap_tab, flag_tab, sql_tab, method_tab = st.tabs(
        ["Временной ряд", "Пропуски", "Флаги качества", "SQL", "Сравнение методов"])

    with chart_tab:
        unit = well_data.loc[well_data["parameter"] == parameter, "unit"].astype(str).iloc[0]
        values = shown.set_index("timestamp")["value"].reindex(grid.index)
        figure = go.Figure(go.Scatter(x=values.index, y=values, mode="lines",
                                      name=parameter, connectgaps=False, line={"color": "#176B87", "width": 1}))
        marked = shown.loc[shown["flag"].ne("")]
        figure.add_trace(go.Scatter(x=marked["timestamp"], y=marked["value"], mode="markers",
                                    name="Флаг источника", marker={"color": "#E76F51", "size": 5},
                                    text=marked["flag"], hovertemplate="%{x}<br>%{y}<br>%{text}<extra></extra>"))
        test_start = data.loc[data["split"] == "test", "timestamp"].min()
        if pd.notna(test_start):
            add_marker(figure, test_start, "Начало test", start, end)
        if parameter == "dynamometer_area":
            add_marker(figure, "2026-05-08" if well == "NK-82" else "2026-05-01",
                       "Изменение масштаба", start, end, "#B45309")
        if well == "NK-7":
            add_marker(figure, "2026-06-01", "Новый режим NK-7", start, end, "#7C3AED")
        figure.update_layout(height=440, title=f"{well} · {parameter}",
                             xaxis_title="Время (час)", yaxis_title=unit,
                             legend={"orientation": "h", "y": -0.2}, margin={"t": 85})
        st.plotly_chart(figure, width="stretch")
        st.caption("Разрывы линии отражают отсутствующие или исключённые фильтром точки. Нулевые значения сохранены.")
        st.dataframe(shown.tail(200), width="stretch", hide_index=True)
    with gap_tab:
        daily = (~grid["record_present"]).resample("D").sum().rename("missing_hours").reset_index()
        st.plotly_chart(px.bar(daily, x="timestamp", y="missing_hours",
                               labels={"timestamp": "Дата", "missing_hours": "Отсутствующие часы"},
                               title="Отсутствующие строки по дням"), width="stretch")
        st.caption("Начальные и конечные пропуски включены; неизвестная комбинация NK-76 / casing_pressure не создаётся.")
        hourly = grid.reset_index()
        st.dataframe(hourly, width="stretch", hide_index=True, height=300)
        st.download_button("Скачать почасовую таблицу", hourly.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{well}_{parameter}_hourly.csv", mime="text/csv")
    with flag_tab:
        tokens = observed.loc[flagged, "flag"].str.split(";").explode().str.strip()
        counts = tokens[tokens.ne("")].value_counts().rename_axis("flag").reset_index(name="rows")
        st.write("Флаги вычислены автором датасета на исходных записях до почасового усреднения.")
        st.caption("Одна строка может иметь несколько флагов. Учитывается весь выбранный период до фильтра графика.")
        if counts.empty:
            st.info("В выбранном периоде флагов источника нет.")
        else:
            st.plotly_chart(px.bar(counts, x="flag", y="rows", labels={"flag": "Флаг", "rows": "Строки"}), width="stretch")
        st.warning("Причина изменения масштаба dynamometer_area не подтверждена. Смена режима NK-7 и статистический выброс сами по себе не доказывают отказ оборудования.")
    with sql_tab:
        show_sql_results()
    with method_tab:
        show_methods()
    st.caption("Источник: NK Oil Well Sensor Monitoring v2 · Arailym Tleubayeva · Galaz and Company LLP · Apache 2.0")


if __name__ == "__main__":
    main()
