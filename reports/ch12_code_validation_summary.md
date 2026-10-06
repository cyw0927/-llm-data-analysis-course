# Chapter 12 코드 검증 요약

- 검사한 코드: `DEFAULT_STATIC_SCAN_EXAMPLE` (실행하지 않고 AST로만 읽음)
- 입력: `C:/dev/llm-data-analysis-course/data/processed` (raw fallback 없음)

## Execution Gate
```text
                axis         status                                      evidence
     schema_and_keys           PASS                             필수 컬럼/PK/FK 검증 통과
aggregate_validation           PASS source total = category total = monthly total
          ml_leakage         REVIEW                      FORBIDDEN 0건 / REVIEW 3건
         static_scan        BLOCKED      DEFAULT_STATIC_SCAN_EXAMPLE: findings 4건
 sandbox_and_package         REVIEW          체크리스트 전 항목 REVIEW (자동으로 PASS 만들지 않음)
      human_approval        PENDING                                       사람 승인 전
  execution_decision DO_NOT_EXECUTE                                              
```

## 정적 스캔 결과
```text
 line             rule severity                   detail
    2   network_import     high 네트워크 모듈 import: requests
    4 hardcoded_secret critical api_key에 문자열 값이 직접 들어 있음
    8       file_write   review          .to_csv() 파일 저장
   10  network_request     high       requests.post() 호출
```

최종 자동 판정: **DO_NOT_EXECUTE**
(DO_NOT_EXECUTE는 자동화 실패가 아니라 검사한 코드에 차단 사유가 있다는 뜻입니다.)
