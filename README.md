# Data Converter WebApp v2

## 변경 사항
- 기존 전체 엑셀 파일 업로드는 선택 사항으로 변경
- `Data` 시트에 들어갈 원본 데이터는 별도 업로드 가능
- CSV / XLSX / XLSB 지원
- 업로드 데이터 기준으로 변환, 그래프, 결과 다운로드 수행

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 사용 순서
1. 선택 사항: 기존 Data Converter `.xlsb` 기준 파일 업로드
2. 필수: Data 원본 파일 업로드
3. 시간축 컬럼 선택
4. 변환할 데이터 컬럼 선택
5. Bias 제거 / 이동평균 필터 설정
6. DataConverted 결과 확인
7. 결과 Excel 다운로드
