# Chapter 10 과제

분류 분석으로 주문 취소 여부를 예측하는 과제 작업 폴더입니다.

## 주 제출물
- `chapter10.ipynb`

## 이미지
- `images/step02_class_ratio.png`
- `images/step03_baseline.png`
- `images/step05_threshold.png`
- `images/step06_confusion_matrix.png`

## 공식 기준
- 공식 Notebook: `notebooks/ch10_llm_code_generation.ipynb`
- 답안 템플릿: `practice/chapter10/templates/chapter10_assignment.md`
- 입력 준비: `python scripts/prepare_ch10_data.py`
- 전체 재실행: `python scripts/run_classification_analysis.py`

## 진행 원칙
1. completed=0, cancelled=1로 타깃 범위를 고정합니다.
2. 주문 생성 직후 예측을 가정하고 사후 정보와 식별자를 제외합니다.
3. line_total, 주문 단위 집계, 병합 관계를 먼저 검증합니다.
4. Train / Validation / Test를 분리합니다.
5. 모델과 Threshold는 Validation에서 선택합니다.
6. Final Test는 선택이 끝난 뒤 마지막 평가에만 사용합니다.
7. Public prediction에서 원본 식별자를 제거합니다.
8. 자동 Validation PASS와 운영 적합성을 구분합니다.
