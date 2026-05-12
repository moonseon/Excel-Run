# 엑셀 서식 기반 사칙연산 계산기

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 수정 내용

- `st.session_state.values[...]` 접근 오류 수정
- 각 입력값을 Streamlit 세션 키로 직접 관리
- 초기화 버튼 안정화
