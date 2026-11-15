# Data sources and attribution

Arailym Tleubayeva. (2026). *Oil Well Sensor Monitoring Dataset: NK Field (v2)*. Hugging Face.
https://huggingface.co/datasets/Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring-v2

Arailym Tleubayeva. (2026). *Oil Well Sensor Monitoring Dataset: NK Field*. Hugging Face.
https://huggingface.co/datasets/Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring

The data provider is **Galaz and Company LLP (ТОО «Галаз и Компания»)**.
The source dataset cards declare **Apache License 2.0** and describe additional
original-data attribution, ownership and contractual obligations. Refer to the
preserved source cards in `data/raw/v1_README.md` and `data/raw/v2_README.md`.
The Apache license text is available at https://www.apache.org/licenses/LICENSE-2.0 .

`download.py` pins both repositories to verified revisions and checks SHA-256
checksums. `data/raw/download_manifest.json` records the revisions, source URLs,
filenames, sizes and checksums. Local raw CSV files remain unchanged.

The project produces educational analyses of these published data. It does not
contain verified equipment-failure labels or establish the cause of the reported
scale or operating-regime changes. The source assigns the year 2026 from the
monthly file sequence. The operator must verify that year for operational use.

Implementation references:

- Pandas documentation: https://pandas.pydata.org/docs/
- SQLite window functions: https://www.sqlite.org/windowfunctions.html
- Apache Arrow Parquet: https://arrow.apache.org/docs/python/parquet.html
- Streamlit documentation: https://docs.streamlit.io/
- Plotly Python documentation: https://plotly.com/python/
