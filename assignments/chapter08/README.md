# Chapter 08 — 작은 데이터 분석 프로젝트 완성하기

이 폴더는 Chapter 08 제출용 작업 공간입니다.

## 폴더 구조

```text
assignments/chapter08/
├─ chapter08.ipynb
├─ README.md
├─ images/
│  ├─ step02_data_validation.png
│  ├─ graph01.png
│  ├─ graph02.png
│  └─ step06_reproduce.png
└─ reference/
   ├─ chapter08_practice_guide.md
   ├─ chapter08_assignment.md
   ├─ SUBMISSION_GUIDE.md
   ├─ CHAPTER_SUBMISSION_MATRIX.md
   ├─ validate_ch08_public_release.py
   └─ ch08-public-qa.yml
```

## 이번 장에서 확인할 핵심

1. 분석 질문과 완료 기준 정의
2. 입력 데이터 구조·결측·중복 확인
3. 전처리 전후 비교
4. PK 결측/중복과 FK 미매칭 확인
5. 안전한 병합과 행 수 검증
6. `line_total = quantity × unit_price` 확인
7. 금액성 분석 범위를 `completed` 주문으로 고정
8. category / month / customer total을 source total과 교차 검증
9. 대표 시각화 작성
10. 공개 고객 결과의 개인정보 제거
11. LLM 활용 기록 작성
12. 전체 프로젝트 재실행 및 최종 Validation PASS 확인

## 실행에 사용하는 주요 파일

```text
data/raw/customers.csv
data/raw/products.csv
data/raw/orders.csv
data/raw/order_items.csv
scripts/run_midterm_project.py
src/__init__.py
src/data_loader.py
src/preprocessing.py
src/eda.py
src/visualization.py
src/midterm_project.py
```

위 파일 중 Chapter 08 실행에 부족했던 공식 Public 자료는 강사 저장소 기준으로 추가했습니다. 기존 `src/preprocessing.py`와 `data/raw`의 네 CSV는 이미 저장소에 있었기 때문에 그대로 사용합니다.

## 공식 자료 보관 위치

강사 Public 저장소에서 Chapter 08 안내에 명시된 자료는 `assignments/chapter08/reference/`에 별도 보관했습니다.

```text
chapter08_practice_guide.md       # 단계별 실습 가이드
chapter08_assignment.md           # Notebook에 옮겨 작성할 답안 템플릿
SUBMISSION_GUIDE.md               # 공통 제출 가이드
CHAPTER_SUBMISSION_MATRIX.md      # Chapter별 제출/Evidence 기준
validate_ch08_public_release.py   # Public QA 참고 스크립트
ch08-public-qa.yml                # Public QA GitHub Actions 참고 파일
```

`chapter08.ipynb`는 공식 `notebooks/ch08_midterm_project.ipynb`를 제출용 위치인 `assignments/chapter08/chapter08.ipynb`로 가져와 작업하도록 구성했습니다.

## 작업 순서

`chapter08.ipynb`를 위에서부터 실행하면서 실제 결과를 확인하고, 각 결과 아래 Markdown 셀에 본인의 관찰·해석·한계·추가 확인 사항을 작성합니다.

마지막에는 프로젝트 루트에서 아래 명령을 실행합니다.

```bash
python scripts/run_midterm_project.py
```

그리고 Notebook의 핵심 수치와 스크립트 결과가 일치하는지 확인합니다.

## 제출 예정 파일

```text
assignments/chapter08/chapter08.ipynb
```

별도의 Markdown 답안 파일을 제출하는 방식이 아니라, 답안 내용은 Notebook의 Markdown 셀에 작성합니다.
