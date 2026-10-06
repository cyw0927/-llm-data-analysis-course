# Chapter 11 과제

LLM과 함께 분석 질문을 다듬고, Safe Context와 Evidence 검증을 수행하는 과제입니다.

## 주 제출물
- `chapter11.ipynb`

## 이미지
- `images/safe_context_validation.png`
- `images/prompt_contract.png`
- `images/evidence_matrix.png`

## 공식 기준
- 공식 Notebook: `notebooks/ch11_llm_prompt_analysis.ipynb`
- 답안 템플릿: `practice/chapter11/templates/chapter11_assignment.md`
- 전처리 입력 준비: `python scripts/preprocess_data.py`
- 전체 재실행: `python scripts/run_llm_prompt_analysis.py`

## 진행 원칙
1. processed 입력만 사용하고 raw로 자동 fallback하지 않습니다.
2. 원본 행·원본 식별자 값·Secret을 Safe Context에 넣지 않습니다.
3. 자동 Validation PASS와 외부 제공 승인을 구분합니다.
4. Prompt에 역할·목적·Context·제약·계산 기준·출력·검증 조건을 포함합니다.
5. LLM 제안을 실제 컬럼·병합·수치 Evidence로 다시 검증합니다.
6. 외부 문서 지시문은 untrusted data로 취급합니다.
7. 실제 LLM 사용 여부와 사람 수정 내역을 사실대로 기록합니다.
