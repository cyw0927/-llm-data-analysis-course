# Chapter 12 코드 검증 요약

- 검사한 코드: `draft_category_sales.py` (실행하지 않고 AST로만 읽음)
- 입력: `C:/dev/llm-data-analysis-course/data/processed` (raw fallback 없음)

## Execution Gate
```text
                axis                status                                      evidence
     schema_and_keys                  PASS                             필수 컬럼/PK/FK 검증 통과
aggregate_validation                  PASS source total = category total = monthly total
          ml_leakage                REVIEW                      FORBIDDEN 0건 / REVIEW 6건
         static_scan                REVIEW          draft_category_sales.py: findings 1건
 sandbox_and_package                REVIEW          체크리스트 전 항목 REVIEW (자동으로 PASS 만들지 않음)
      human_approval               PENDING                                       사람 승인 전
  execution_decision HUMAN_REVIEW_REQUIRED                                              
```

## 정적 스캔 결과
```text
 line       rule severity          detail
   20 file_write   review .to_csv() 파일 저장
```

최종 자동 판정: **HUMAN_REVIEW_REQUIRED**
(DO_NOT_EXECUTE는 자동화 실패가 아니라 검사한 코드에 차단 사유가 있다는 뜻입니다.)
