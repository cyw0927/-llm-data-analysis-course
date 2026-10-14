# Chapter 13 — 외부 데이터로 분석을 확장하기

## 제출물
- [chapter13.ipynb](chapter13.ipynb) — 실행 완료 제출용 노트북
- `images/step02_source_terms.png` — 공식 출처·이용조건 **요약 이미지** (실제 웹 캡처 아님)
- `images/step04_snapshot_metadata.png` — Raw / Processed / Metadata **미수집 상태**
- `images/step05_quality.png` — 실제 NO_DATA / 합성 데모 품질 구분
- `images/step07_merge.png` — **합성 데모 전용** 병합 검증

## 공식 자료
- [공식 실습 Notebook](https://github.com/GilbertMoon/llm-data-analysis-course/blob/main/notebooks/ch13_external_data_collection.ipynb)
- [공식 실습 가이드](https://github.com/GilbertMoon/llm-data-analysis-course/blob/main/practice/chapter13/chapter13.md)
- [답안 템플릿](https://github.com/GilbertMoon/llm-data-analysis-course/blob/main/practice/chapter13/templates/chapter13_assignment.md)
- [한국천문연구원 특일 정보 공식 공공데이터포털 페이지](https://www.data.go.kr/data/15012690/openapi.do)

## 실행
```powershell
cd C:\dev\llm-data-analysis-course
python -m pip install -r requirements.txt
python scripts/run_external_data_collection.py
jupyter nbconvert --to notebook --execute assignments/chapter13/chapter13.ipynb --inplace
```

## 중요 상태
- 실제 외부 네트워크 수집 **SKIPPED**, Gate **OFF**
- 외부 품질 검사 **NO_DATA**, 실제 Raw/Metadata/Hash 없음
- 내부 월별 completed 매출 계산 **EXECUTED**
- 외부 월별 데이터 병합 예시는 **SYNTHETIC_DEMO_ONLY**
- 합성 공휴일 수를 실제 데이터/관찰/인과 주장으로 사용하지 않음

외부 API 실행은 공식 문서/조건·비밀키 보관·최소 범위·사람 승인이 끝난 뒤 별도 작업으로 진행합니다.
