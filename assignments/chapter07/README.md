# Chapter 07 — 그래프로 데이터의 이야기를 보여주기

이 폴더는 Chapter 07 제출용 작업 공간입니다.

## 폴더 구조

```text
assignments/chapter07/
├─ chapter07.ipynb
├─ README.md
├─ images/
│  ├─ graph01.png                 # 카테고리별 completed 금액 (대표 그래프 1)
│  ├─ graph02.png                 # 월별 completed 금액 추이 (대표 그래프 2)
│  ├─ graph03.png                 # 상품 가격 분포 (bins 비교)
│  ├─ graph04.png                 # 가격-completed 판매 수량 산점도 (대표 그래프 3)
│  ├─ graph05_top_customers.png   # 상위 고객(익명)
│  └─ graph06_order_status.png    # 주문 상태별 주문 수
└─ reference/
   ├─ chapter07_practice_guide.md
   ├─ chapter07_assignment.md
   ├─ SUBMISSION_GUIDE.md
   └─ CHAPTER_SUBMISSION_MATRIX.md
```

## 이번 장에서 확인한 핵심

1. 그래프보다 시각화 질문을 먼저 정의 (최소 3개 질문 + 그래프 선택 이유)
2. 그래프를 그리기 전에 집계표와 총합 검증을 먼저 확인
3. 금액성 그래프는 `order_status == "completed"` 범위로 고정
4. 막대·선·히스토그램·산점도·가로막대 그래프 작성과 해석
5. 대표 그래프 3개에 대해 원본 집계값·관찰·해석·업무 의미·한계를 구분해서 작성
6. 대표 그래프의 값과 원본 집계표 값을 교차 검증
7. 축·단위·정렬·범례 등 오해를 줄이는 체크리스트 점검
8. 상위 고객 그래프에서 개인정보(이름/이메일/전화번호/주소) 미노출 확인
9. LLM에게 그래프 선택·축 설정·해석 시 주의점을 검토받고, 실제 반영 여부와 판단 이유를 기록
10. `scripts/run_visualization.py`를 재실행해 Notebook과 같은 집계 검증(PASS)이 나오는지 확인

## 데이터 준비에 대한 메모

이 저장소에는 공식 Chapter 05 전용 실습 Raw(`practice/chapter05/data/raw`, 의도적으로 결측·중복·PK/FK 오류가 섞인 데이터셋)가 포함되어 있지 않습니다. 대신 이미 저장소에 있는 프로젝트 공통 `data/raw`(Chapter 08 실습에서도 사용한 파일)를 입력으로, 공식 전처리 함수(`src/preprocessing.py`)를 그대로 실행해 `data/processed/*_clean.csv`를 다시 만들었습니다 (`scripts/rebuild_processed_data.py`). 이어서 공식 Chapter 07 통합 스크립트(`scripts/prepare_ch07_visualization_csv.py`)로 `data/processed/visualization.csv`도 함께 다시 만들어, 두 파일의 행 수와 병합 결과가 서로 어긋나지 않도록 맞췄습니다.

이번에 사용한 `data/raw` 스냅샷에는 주문/상품/고객 간 FK 불일치가 없었습니다(`order_match`/`product_match`/`customer_match` 실패 0건). 공식 Chapter 05 전용 Raw를 쓰면 이 값이 달라질 수 있다는 점은 Notebook에 별도로 적어 두었습니다.

## 공식 자료 보관 위치

강사 Public 저장소(`GilbertMoon/llm-data-analysis-course`)에서 Chapter 07 안내에 명시된 자료는 `assignments/chapter07/reference/`에 별도 보관했습니다.

```text
chapter07_practice_guide.md   # 단계별 실습 가이드 (practice/chapter07/chapter07.md)
chapter07_assignment.md       # Notebook에 옮겨 작성할 답안 템플릿
SUBMISSION_GUIDE.md           # 공통 제출 가이드
CHAPTER_SUBMISSION_MATRIX.md  # Chapter별 제출/Evidence 기준
```

`chapter07.ipynb`는 공식 `notebooks/ch07_visualization.ipynb`의 실행 흐름을 유지하면서, 제출용 위치인 `assignments/chapter07/chapter07.ipynb`에서 직접 작성했습니다.

## 작업 순서

`chapter07.ipynb`를 위에서부터 실행하면서 실제 결과를 확인하고, 각 결과 아래 Markdown 셀에 원본 집계값·결과 관찰·나의 해석과 판단·업무·분석적 의미·한계를 작성했습니다.

마지막에는 Notebook 안에서 프로젝트 루트 기준으로 아래 명령을 다시 실행해 결과를 비교했습니다.

```bash
python scripts/run_visualization.py
```

그리고 Notebook의 집계 검증(총합 일치 여부)과 스크립트 결과가 일치하는지 확인했습니다.

## 제출 파일

```text
assignments/chapter07/chapter07.ipynb
```

별도의 Markdown 답안 파일을 제출하는 방식이 아니라, 답안 내용은 Notebook의 Markdown 셀에 작성했습니다.
