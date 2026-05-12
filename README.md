# XLSB Data Converter Streamlit App

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 기능

- `.xlsb` 파일 업로드
- `Data` 시트 원본 데이터 확인
- `DataConverted`, `Graph` 시트 미리보기
- 선택 채널 Python 변환
- Bias 제거
- 이동평균 필터
- 그래프 표시
- 변환 결과 Excel 다운로드

## 다음 확장 예정

- CFC 필터 Python 1:1 구현
- 꼬리만들기 / 꼬리연결 로직 이식
- Channel 시트 기반 자동 채널 매핑
- Dashboard 지표 자동 생성
