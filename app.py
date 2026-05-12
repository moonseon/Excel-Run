import io
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from pyxlsb import open_workbook

st.set_page_config(page_title="XLSB Data Converter", page_icon="📊", layout="wide")

DEFAULT_FILE = Path(__file__).parent / "20251220-1 Data Converter_R1.0.xlsb"

SHEET_HINTS = {
    "raw": "Data",
    "ui": "UI",
    "converted": "DataConverted",
    "graph1": "Graph1",
    "graph2": "Graph2",
    "dashboard": "Dashboard",
    "converter": "Converter",
}


def save_uploaded_file(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".xlsb"
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(uploaded_file.getbuffer())
    temp.close()
    return Path(temp.name)


@st.cache_data(show_spinner=False)
def list_sheets(file_path: str):
    with open_workbook(file_path) as wb:
        return list(wb.sheets)


@st.cache_data(show_spinner=False)
def read_xlsb_sheet(file_path: str, sheet_name: str, max_rows: int | None = None) -> pd.DataFrame:
    rows = []
    with open_workbook(file_path) as wb:
        with wb.get_sheet(sheet_name) as sheet:
            for idx, row in enumerate(sheet.rows()):
                rows.append([cell.v for cell in row])
                if max_rows is not None and idx + 1 >= max_rows:
                    break
    if not rows:
        return pd.DataFrame()
    width = max(len(r) for r in rows)
    normalized = [r + [None] * (width - len(r)) for r in rows]
    return pd.DataFrame(normalized)


def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out = out.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return out.reset_index(drop=True)


def sheet_to_header_df(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_table(df)
    if df.empty:
        return df
    header = [str(x).strip() if x is not None and str(x) != "nan" else f"Column_{i+1}" for i, x in enumerate(df.iloc[0].tolist())]
    # 중복 컬럼명 처리
    seen = {}
    fixed = []
    for h in header:
        if h in seen:
            seen[h] += 1
            fixed.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 1
            fixed.append(h)
    body = df.iloc[1:].reset_index(drop=True)
    body.columns = fixed
    return body


def detect_time_column(df: pd.DataFrame):
    for col in df.columns:
        name = str(col).lower()
        if "time" in name or "ti00" in name:
            return col
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]
    return numeric_cols[0] if numeric_cols else None


def to_numeric_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def moving_average_filter(series: pd.Series, window: int) -> pd.Series:
    window = max(1, int(window))
    if window <= 1:
        return series
    return series.rolling(window=window, min_periods=1, center=False).mean()


def python_convert(raw_df: pd.DataFrame, selected_cols, bias_points: int, filter_window: int, remove_bias: bool) -> pd.DataFrame:
    table = sheet_to_header_df(raw_df)
    if table.empty:
        return pd.DataFrame()
    numeric = to_numeric_df(table)
    time_col = detect_time_column(table)
    result = pd.DataFrame()
    if time_col is not None:
        result["Time"] = pd.to_numeric(table[time_col], errors="coerce")
    for col in selected_cols:
        if col == time_col:
            continue
        values = pd.to_numeric(table[col], errors="coerce")
        result[f"{col}_Raw"] = values
        converted = values.copy()
        if remove_bias:
            base = converted.head(max(1, bias_points)).mean(skipna=True)
            converted = converted - base
            converted_name = f"{col}_BiasRemoved({bias_points})"
        else:
            converted_name = f"{col}_NoBiasRemove"
        if filter_window > 1:
            converted = moving_average_filter(converted, filter_window)
            converted_name += f"_MA{filter_window}"
        else:
            converted_name += "_NoFilter"
        result[converted_name] = converted
    return result


def summary_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        values = pd.to_numeric(df[col], errors="coerce")
        if values.notna().sum() == 0:
            continue
        rows.append({
            "Channel": col,
            "Count": int(values.notna().sum()),
            "Min": values.min(),
            "Max": values.max(),
            "Mean": values.mean(),
            "Std": values.std(),
        })
    return pd.DataFrame(rows)


def download_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, df in tables.items():
            safe_name = name[:31]
            df.to_excel(writer, index=False, sheet_name=safe_name)
    return buffer.getvalue()


st.title("📊 XLSB Data Converter Web App")
st.caption("업로드한 .xlsb 업무 엑셀을 기준으로 Data → Converter → DataConverted/Graph 흐름을 웹앱화한 Python Streamlit 버전입니다.")

with st.sidebar:
    st.header("1) 파일 선택")
    uploaded = st.file_uploader("XLSB 파일 업로드", type=["xlsb"])
    use_sample = st.checkbox("현재 업로드된 샘플 파일 사용", value=DEFAULT_FILE.exists())

    if uploaded is not None:
        file_path = save_uploaded_file(uploaded)
        st.success(f"업로드 완료: {uploaded.name}")
    elif use_sample and DEFAULT_FILE.exists():
        file_path = DEFAULT_FILE
        st.info(DEFAULT_FILE.name)
    else:
        st.warning(".xlsb 파일을 업로드하세요.")
        st.stop()

try:
    sheets = list_sheets(str(file_path))
except Exception as e:
    st.error(f"파일을 읽을 수 없습니다: {e}")
    st.stop()

with st.sidebar:
    st.header("2) 시트 매핑")
    raw_sheet = st.selectbox("원본 Data 시트", sheets, index=sheets.index(SHEET_HINTS["raw"]) if SHEET_HINTS["raw"] in sheets else 0)
    converted_sheet = st.selectbox("기존 결과 시트", sheets, index=sheets.index(SHEET_HINTS["converted"]) if SHEET_HINTS["converted"] in sheets else 0)
    graph_sheet = st.selectbox("그래프용 시트", sheets, index=sheets.index(SHEET_HINTS["graph2"]) if SHEET_HINTS["graph2"] in sheets else 0)
    preview_rows = st.slider("읽을 최대 행 수", 100, 50000, 10000, 100)

raw_df = read_xlsb_sheet(str(file_path), raw_sheet, preview_rows)
converted_raw = read_xlsb_sheet(str(file_path), converted_sheet, preview_rows)
graph_raw = read_xlsb_sheet(str(file_path), graph_sheet, preview_rows)

raw_table = sheet_to_header_df(raw_df)
converted_table = sheet_to_header_df(converted_raw)
graph_table = sheet_to_header_df(graph_raw)

st.subheader("업무 흐름")
flow_cols = st.columns(5)
flow_cols[0].metric("입력", raw_sheet)
flow_cols[1].metric("행 수", f"{max(len(raw_table), 0):,}")
flow_cols[2].metric("컬럼 수", f"{len(raw_table.columns):,}")
flow_cols[3].metric("기존 출력", converted_sheet)
flow_cols[4].metric("그래프", graph_sheet)

main_tab, convert_tab, graph_tab, export_tab = st.tabs(["원본/설정 확인", "Python 변환", "그래프/대시보드", "내보내기"])

with main_tab:
    st.markdown("### 원본 Data 미리보기")
    st.dataframe(raw_table.head(300), use_container_width=True, height=360)

    st.markdown("### 기존 DataConverted 미리보기")
    st.dataframe(converted_table.head(300), use_container_width=True, height=360)

with convert_tab:
    st.markdown("### 변환 옵션")
    available_cols = list(raw_table.columns)
    time_col = detect_time_column(raw_table)
    default_cols = [c for c in available_cols if c != time_col][: min(3, max(0, len(available_cols) - 1))]

    c1, c2, c3 = st.columns(3)
    with c1:
        selected_cols = st.multiselect("변환 대상 채널", available_cols, default=default_cols)
    with c2:
        remove_bias = st.checkbox("Bias 제거", value=True)
        bias_points = st.number_input("Bias 기준 포인트 수", min_value=1, max_value=10000, value=128, step=1)
    with c3:
        filter_window = st.number_input("이동평균 필터 Window", min_value=1, max_value=1000, value=1, step=1)
        st.caption("CFC 필터는 프로젝트 요구식 확정 후 동일 위치에 교체 가능합니다.")

    converted_py = python_convert(raw_df, selected_cols, int(bias_points), int(filter_window), remove_bias)
    st.markdown("### Python 변환 결과")
    st.dataframe(converted_py.head(500), use_container_width=True, height=420)

    metrics = summary_metrics(converted_py.drop(columns=["Time"], errors="ignore"))
    st.markdown("### 요약 통계")
    st.dataframe(metrics, use_container_width=True, height=260)

with graph_tab:
    st.markdown("### 그래프")
    graph_source = st.radio("그래프 데이터", ["Python 변환 결과", "엑셀 Graph 시트"], horizontal=True)
    plot_df = converted_py if graph_source == "Python 변환 결과" else graph_table
    if plot_df.empty:
        st.warning("그래프를 그릴 데이터가 없습니다.")
    else:
        plot_cols = list(plot_df.columns)
        x_default = detect_time_column(plot_df) or plot_cols[0]
        x_col = st.selectbox("X축", plot_cols, index=plot_cols.index(x_default) if x_default in plot_cols else 0)
        y_options = [c for c in plot_cols if c != x_col]
        y_default = y_options[: min(4, len(y_options))]
        y_cols = st.multiselect("Y축", y_options, default=y_default)
        chart_df = plot_df[[x_col] + y_cols].copy() if y_cols else pd.DataFrame()
        for col in chart_df.columns:
            chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce")
        chart_df = chart_df.dropna(subset=[x_col])
        if y_cols and not chart_df.empty:
            long_df = chart_df.melt(id_vars=[x_col], value_vars=y_cols, var_name="Channel", value_name="Value").dropna()
            fig = px.line(long_df, x=x_col, y="Value", color="Channel", title="Converted Data Graph")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Y축 채널을 선택하세요.")

with export_tab:
    st.markdown("### 결과 다운로드")
    export_bytes = download_excel_bytes({
        "RawDataPreview": raw_table.head(preview_rows),
        "ExistingConverted": converted_table.head(preview_rows),
        "PythonConverted": converted_py,
        "Summary": summary_metrics(converted_py.drop(columns=["Time"], errors="ignore")) if 'converted_py' in locals() else pd.DataFrame(),
    })
    st.download_button(
        "변환 결과 Excel 다운로드",
        data=export_bytes,
        file_name="converted_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("### 앱 설명")
    st.info(
        "현재 버전은 원본 Data 시트를 읽고 선택 채널에 대해 Bias 제거/이동평균 필터를 수행합니다. "
        "엑셀의 CFC필터, 꼬리만들기, 꼬리연결 로직은 다음 단계에서 Python 함수로 1:1 이식할 수 있도록 구조를 분리해 두었습니다."
    )
