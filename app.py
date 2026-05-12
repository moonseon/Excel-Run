
import io
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px


st.set_page_config(
    page_title="Data Converter WebApp",
    page_icon="📊",
    layout="wide",
)


DEFAULT_SAMPLE_WINDOW = 5


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove fully empty rows/columns and normalize headers."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() if str(c).strip() else f"Column_{i+1}" for i, c in enumerate(df.columns)]
    return df


def read_uploaded_data(uploaded_file, sheet_name=None) -> pd.DataFrame:
    """Read CSV/XLSX/XLSB data uploaded as the Data input."""
    suffix = Path(uploaded_file.name).suffix.lower()

    if suffix == ".csv":
        try:
            return clean_dataframe(pd.read_csv(uploaded_file))
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return clean_dataframe(pd.read_csv(uploaded_file, encoding="cp949"))

    if suffix in [".xlsx", ".xls"]:
        return clean_dataframe(pd.read_excel(uploaded_file, sheet_name=sheet_name or 0))

    if suffix == ".xlsb":
        return clean_dataframe(pd.read_excel(uploaded_file, sheet_name=sheet_name or 0, engine="pyxlsb"))

    raise ValueError("지원하지 않는 파일 형식입니다. CSV, XLSX, XLSB 파일을 업로드하세요.")


def list_sheets(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return []

    uploaded_file.seek(0)
    if suffix == ".xlsb":
        excel = pd.ExcelFile(uploaded_file, engine="pyxlsb")
    else:
        excel = pd.ExcelFile(uploaded_file)
    sheets = excel.sheet_names
    uploaded_file.seek(0)
    return sheets


def detect_time_column(df: pd.DataFrame):
    candidates = ["time", "Time", "TIME", "t", "T", "시간"]
    for c in candidates:
        if c in df.columns:
            return c
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return numeric_cols[0] if numeric_cols else None


def convert_data(
    data_df: pd.DataFrame,
    time_col: str | None,
    selected_cols: list[str],
    remove_bias: bool,
    filter_window: int,
) -> pd.DataFrame:
    """Business-logic style converter for uploaded Data sheet content."""
    if data_df.empty:
        return pd.DataFrame()

    result = pd.DataFrame()

    if time_col and time_col in data_df.columns:
        result[time_col] = data_df[time_col]

    for col in selected_cols:
        series = pd.to_numeric(data_df[col], errors="coerce")

        if remove_bias:
            bias_base = series.dropna().iloc[: min(20, series.dropna().shape[0])]
            bias = bias_base.mean() if not bias_base.empty else 0
            series = series - bias

        if filter_window and filter_window > 1:
            series = series.rolling(window=filter_window, min_periods=1, center=True).mean()

        result[col] = series

    return result


def make_excel_download(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="DataConverted")
    output.seek(0)
    return output.getvalue()


st.title("📊 Data Converter WebApp")
st.caption("엑셀 원본 구조를 웹앱으로 분리했습니다. Data 시트 데이터는 별도로 업로드하고, 웹에서 변환/그래프/다운로드를 수행합니다.")

with st.sidebar:
    st.header("1. 기준 엑셀 파일")
    template_file = st.file_uploader(
        "기준 파일 업로드 선택사항",
        type=["xlsb", "xlsx", "xls"],
        help="기존 Data Converter 파일입니다. 시트 구조 확인/참고용이며, Data 원본은 아래에서 별도 업로드합니다.",
        key="template_file",
    )

    if template_file:
        try:
            sheets = list_sheets(template_file)
            st.success(f"기준 파일 인식 완료: {len(sheets)}개 시트")
            with st.expander("시트 목록"):
                st.write(sheets)
        except Exception as e:
            st.warning(f"기준 파일 시트 확인 실패: {e}")

    st.divider()

    st.header("2. Data 원본 업로드")
    data_file = st.file_uploader(
        "Data 시트에 들어갈 원본 데이터 업로드",
        type=["csv", "xlsx", "xlsb", "xls"],
        help="측정 데이터, 센서 데이터, CSV 변환 데이터 등을 업로드하세요.",
        key="data_file",
    )


if not data_file:
    st.info("왼쪽 사이드바에서 Data 원본 파일을 업로드하세요. CSV, XLSX, XLSB 형식을 지원합니다.")
    st.stop()


try:
    data_sheets = list_sheets(data_file)
    selected_sheet = None
    if data_sheets:
        preferred_index = data_sheets.index("Data") if "Data" in data_sheets else 0
        selected_sheet = st.sidebar.selectbox(
            "Data 파일에서 읽을 시트",
            data_sheets,
            index=preferred_index,
        )
    data_file.seek(0)
    data_df = read_uploaded_data(data_file, selected_sheet)
except Exception as e:
    st.error(f"Data 파일을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()


if data_df.empty:
    st.warning("업로드한 Data 파일에서 유효한 데이터를 찾지 못했습니다.")
    st.stop()


st.subheader("① 업로드된 Data 미리보기")
c1, c2, c3 = st.columns(3)
c1.metric("행 수", f"{len(data_df):,}")
c2.metric("열 수", f"{len(data_df.columns):,}")
c3.metric("파일명", data_file.name)

st.dataframe(data_df.head(100), use_container_width=True)


numeric_cols = data_df.select_dtypes(include=[np.number]).columns.tolist()
if not numeric_cols:
    # Try converting object columns that look numeric
    converted_candidates = []
    for col in data_df.columns:
        parsed = pd.to_numeric(data_df[col], errors="coerce")
        if parsed.notna().sum() > 0:
            converted_candidates.append(col)
    numeric_cols = converted_candidates

if not numeric_cols:
    st.error("숫자형으로 변환 가능한 컬럼이 없습니다. Data 파일의 컬럼 구조를 확인하세요.")
    st.stop()


st.subheader("② 변환 설정")
time_default = detect_time_column(data_df)
time_options = ["없음"] + list(data_df.columns)
time_index = time_options.index(time_default) if time_default in time_options else 0

col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    time_col_choice = st.selectbox("시간축 컬럼", time_options, index=time_index)
    time_col = None if time_col_choice == "없음" else time_col_choice

with col2:
    remove_bias = st.checkbox("Bias 제거", value=True)

with col3:
    filter_window = st.number_input(
        "이동평균 필터 Window",
        min_value=1,
        max_value=999,
        value=DEFAULT_SAMPLE_WINDOW,
        step=1,
    )

default_signal_cols = [c for c in numeric_cols if c != time_col][:10]
selected_cols = st.multiselect(
    "변환할 데이터 컬럼",
    options=[c for c in data_df.columns if c != time_col],
    default=default_signal_cols,
)

if not selected_cols:
    st.warning("변환할 데이터 컬럼을 하나 이상 선택하세요.")
    st.stop()


converted_df = convert_data(
    data_df=data_df,
    time_col=time_col,
    selected_cols=selected_cols,
    remove_bias=remove_bias,
    filter_window=int(filter_window),
)


st.subheader("③ 변환 결과 DataConverted")
st.dataframe(converted_df.head(300), use_container_width=True)


st.subheader("④ 그래프")
graph_cols = st.multiselect(
    "그래프에 표시할 컬럼",
    options=selected_cols,
    default=selected_cols[: min(3, len(selected_cols))],
)

if graph_cols:
    plot_df = converted_df[[c for c in ([time_col] if time_col else []) + graph_cols if c in converted_df.columns]].copy()
    if time_col:
        fig = px.line(plot_df, x=time_col, y=graph_cols, title="Converted Data Graph")
    else:
        fig = px.line(plot_df[graph_cols], title="Converted Data Graph")
    st.plotly_chart(fig, use_container_width=True)


st.subheader("⑤ 결과 다운로드")
excel_bytes = make_excel_download(converted_df)
st.download_button(
    label="DataConverted.xlsx 다운로드",
    data=excel_bytes,
    file_name="DataConverted.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

with st.expander("현재 앱 구조"):
    st.markdown(
        """
        - 기준 엑셀 파일: 기존 `.xlsb` 구조 확인/참고용
        - Data 원본 업로드: 실제 입력 데이터
        - Python 변환 엔진: Bias 제거, 이동평균 필터, 컬럼 선택
        - DataConverted: 변환 결과
        - Graph: 웹 그래프
        - Download: 결과 엑셀 저장
        """
    )
