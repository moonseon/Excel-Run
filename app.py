import streamlit as st

st.set_page_config(
    page_title="엑셀 서식 기반 계산기",
    page_icon="🧮",
    layout="centered",
)

DEFAULT_VALUES = {
    "add_a": 1.0,
    "add_b": 1.0,
    "sub_a": 1.0,
    "sub_b": 1.0,
    "mul_a": 1.0,
    "mul_b": 1.0,
    "div_a": 1.0,
    "div_b": 1.0,
}

ROWS = [
    ("add", "덧셈", "+"),
    ("sub", "뺄셈", "-"),
    ("mul", "곱셈", "×"),
    ("div", "나눗셈", "/"),
]


def init_state():
    """Streamlit Cloud 재실행/기존 세션에서도 필요한 키를 모두 안전하게 생성합니다."""
    for key, value in DEFAULT_VALUES.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_values():
    for key, value in DEFAULT_VALUES.items():
        st.session_state[key] = value


def calculate(a: float, op: str, b: float):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "×":
        return a * b
    if op == "/":
        if b == 0:
            return "0으로 나눌 수 없음"
        return a / b
    return ""


def format_result(value):
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return str(int(value))
    return f"{value:,.6f}".rstrip("0").rstrip(".")


st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .sub-text {
        color: #64748b;
        margin-bottom: 24px;
    }
    .header-cell {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        font-weight: 800;
    }
    .label-cell {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 13px 10px;
        font-weight: 800;
        text-align: center;
    }
    .op-cell {
        padding-top: 8px;
        text-align: center;
        font-size: 26px;
        font-weight: 900;
    }
    .result-box {
        background: #fef08a;
        border: 1px solid #facc15;
        padding: 10px 12px;
        border-radius: 10px;
        min-height: 44px;
        font-size: 20px;
        font-weight: 900;
        text-align: right;
    }
    div[data-testid="stNumberInput"] input {
        background-color: #fef9c3;
        border: 1px solid #facc15;
        font-weight: 800;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

st.markdown('<div class="main-title">엑셀 서식 기반 사칙연산 계산기</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-text">엑셀 파일의 A / B / C 구조와 노란 입력 셀 스타일을 Python Streamlit 웹앱으로 변환했습니다.</div>',
    unsafe_allow_html=True,
)

st.button("초기화", on_click=reset_values, use_container_width=True)

st.markdown("### 계산 입력")

header_cols = st.columns([1.1, 1.3, 0.7, 1.3, 0.5, 1.4])
for col, text in zip(header_cols, ["구분", "A", "연산", "B", "=", "C"]):
    col.markdown(f'<div class="header-cell">{text}</div>', unsafe_allow_html=True)

for row_id, label, op in ROWS:
    cols = st.columns([1.1, 1.3, 0.7, 1.3, 0.5, 1.4])
    cols[0].markdown(f'<div class="label-cell">{label}</div>', unsafe_allow_html=True)

    a = cols[1].number_input(
        f"{label} A",
        key=f"{row_id}_a",
        label_visibility="collapsed",
        step=1.0,
    )

    cols[2].markdown(f'<div class="op-cell">{op}</div>', unsafe_allow_html=True)

    b = cols[3].number_input(
        f"{label} B",
        key=f"{row_id}_b",
        label_visibility="collapsed",
        step=1.0,
    )

    cols[4].markdown('<div class="op-cell">=</div>', unsafe_allow_html=True)

    result = calculate(a, op, b)
    cols[5].markdown(f'<div class="result-box">{format_result(result)}</div>', unsafe_allow_html=True)

st.divider()

st.markdown("### 엑셀 수식 대응")
st.info(
    "엑셀의 `=B2+D2`, `=B4-D4`, `=B6*D6`, `=B8/D8` 구조를 Python 계산 로직으로 변환했습니다."
)

st.markdown("### 실행 방법")
st.code("pip install -r requirements.txt\nstreamlit run app.py", language="bash")
