# Chapter 09 과제

회귀 분석으로 숫자 예측하기 과제 작업 폴더입니다.

## 주 제출물
- `chapter09.ipynb`

## 이미지
- `images/step02_leakage.png`
- `images/step04_split.png`
- `images/step06_final_metrics.png`

## 공식 기준
- 공식 Notebook: `notebooks/ch09_regression_analysis.ipynb`
- 답안 템플릿: `practice/chapter09/templates/chapter09_assignment.md`
- 입력 준비: `python scripts/prepare_ch09_data.py`
- 전체 재실행: `python scripts/run_regression_analysis.py`

## 진행 원칙
1. 예측 문제와 예측 시점을 먼저 정의합니다.
2. Target 계산 재료, 사후 정보, 식별자를 feature에서 제외합니다.
3. Train / Final Test는 시간 순서로 분리합니다.
4. 모델 선택은 Train TimeSeriesSplit에서 끝냅니다.
5. Final Test는 Baseline과 고정된 Selected Model의 마지막 평가에만 사용합니다.
6. 실행 결과는 실제 Notebook 출력과 Evidence를 확인한 뒤 작성합니다.
