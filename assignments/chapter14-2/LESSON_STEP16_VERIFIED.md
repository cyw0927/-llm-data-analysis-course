> **강의 STEP24 실제 저장 완료:** Raw5 PROCESSED, 자동 정제52/26/5, 현재 서울 소비강도22=97.07 반영. 과거2201/119.08은 Raw와 비공개26행 보관에 유지했습니다. [STEP17~24 검증 기록](LESSON_STEP24_VERIFIED.md)

# 강의 STEP 13~16: 실제 HTTP 응답 및 소비 지표 정정

검증일: 2026-10-19 (Asia/Seoul). 기존 Make Scenario **7992550**을 재사용했다. 새 시나리오·중복 HTTP 모듈은 만들지 않았다.

## 실제 단독 실행 결과

| 강의 단계 | 실제 Make 결과 |
|---|---|
| STEP 13 NAVER Trend | POST, HTTP 200, 원문 문자열에 startDate/endDate/results 존재, 4개 키워드·52개 관측값 |
| STEP 14 관광 체류 | GET, HTTP 200, `resultCode=0000`, OK, totalCount=26/item=26, 코드21·관광체류강도 |
| STEP 15 관광 소비 | GET, HTTP 200, `resultCode=0000`, OK, totalCount=26/item=26, **코드22·관광소비강도**. 서울 97.07 |
| STEP 16 NAVER Local | GET, HTTP 200, 5개 대표 장소, title/category/address/roadAddress/mapx/mapy/link 확인 |

모든 HTTP는 **Parse response=No**다. 응답 JSON을 문자열로 받은 뒤 검증 과정에서만 해석했다. 실제 실행은 각 HTTP의 `Run this module only`로 수행했고 Supabase 저장 모듈은 실행하지 않았다. 체류 모듈은 결과창 확인 중 추가 단독 실행도 있었으며 DB 저장에는 연결되지 않았다.

기존 요청 설정 중 예시와 달라도 유효한 값은 유지했다.

- NAVER Trend: 최근 365일부터 어제까지 월별 여행/축제/캠핑/맛집. 실제 요청일 범위와 API가 응답하는 월별 기간은 원문 파일에 각각 기록했다.
- 관광: 이미 성공한 기준월 `202509`, 서울 `areaCd=11`, pageNo=1, numOfRows=100. 최신 공표월을 자동 탐색했다는 뜻은 아니다.
- Local: 기존 `서울 관광명소`, display=5, start=1, sort=random 유지. random은 공식 API의 정확도순 옵션이다. format 미지정 시 기본 json이다. 강의의 `서울 관광지`/comment도 유효한 다른 검색 예시이며 필수값으로 보지 않았다. [NAVER 공식 문서](https://api.ncloud-docs.com/docs/naver-api-hub-search-local)
- Local 좌표는 실제 문자열 값을 읽고 기존 좌표 검증기로 1e7 배율을 정규화한 뒤 국내 위·경도 범위 및 서울 주소를 확인했다. 대표 5건이며 전체 관광지 수가 아니다.

실행 이력:

- [NAVER Trend 11:24:24 — 1 operation, Success](https://eu1.make.com/3207920/scenarios/7992550/logs/1412014071ad475db9e9098b661ff153)
- [관광 체류 11:25:08 — 1 operation, Success](https://eu1.make.com/3207920/scenarios/7992550/logs/95f5e1ab6c8e48cfa4d1805f06bde119)
- [NAVER Local 11:28:34 — 1 operation, Success](https://eu1.make.com/3207920/scenarios/7992550/logs/89f2984740394280bc4fc42ae79c451b)
- [관광 소비22 11:33:57 — 1 operation, Success](https://eu1.make.com/3207920/scenarios/7992550/logs/1dbffd2a3eca47bea610cd956f1477be)

## 중요 정정: 2201과 22는 다른 지표

이전 작업은 성공 응답의 행 수와 매핑은 확인했지만 **소비 지표의 의미를 잘못 판단**했다. `2201`의 수치를 강의의 관광소비강도와 같은 것으로 설명한 부분을 정정한다.

| 코드 | 실제 응답 지표명 | 202509 서울 값 |
|---|---|---:|
| 2201 | 외지인 소비액 | 119.08 |
| **22** | **관광소비강도** | **97.07** |

두 요청 모두 HTTP 200과 `0000`을 반환하므로 성공 코드만으로는 지표가 맞는지 확인할 수 없다. API가 세부 지표들을 제공한다는 설명은 [한국관광공사 공식 API 안내](https://www.data.go.kr/data/15151868/openapi.do)에서도 확인된다. 코드·지표명·수치의 차이는 이번 실제 응답 두 종류를 대조해 확인했다.

Make의 소비 모듈 **코드 한 항목만 2201→22로 수정**했다. URL·인증정보·다른 파라미터·Raw 매핑은 유지했다. 소비 모듈에 잘못된 `tarSjrnDsIxCd`가 없고 쿼리 이름에 뒤 공백도 없는 것을 확인했다.

## 승인된 DB 호환 수정 및 기존 값 보존

기존 처리 함수가 2201만 허용하고 있었으므로 사용자 요청에 따라 `sql/006_correct_consumption_metric.sql`을 실제 Supabase에 적용했다.

1. `tourism_demand.consumption_metric_code` 추가. 기존 26행은 연결된 Raw의 실제 코드로부터 2201임을 표시했다. 기존 관측값·ID·시각·raw_id는 바꾸지 않았다.
2. 비공개 `tourism_demand_metric_archive`에 기존 26행 전체와 원본 참조를 보관했다. RLS 활성화, anon/authenticated/public 접근 차단.
3. `process_tourism_demand_raw()`가 앞으로 **22만** 소비강도로 처리하도록 수정했다. 새로 처리한 행에는 metric_code=22를 기록한다. 기존 2201을 조용히 소비강도로 받아들이지 않는다.

실제 DB 검증은 새 소비22 응답과 기존 Raw 1의 나머지 원문을 넣어 전체 Trigger를 호출하되, **트랜잭션을 ROLLBACK**했다. 시험 안에서는 PROCESSED·서울97.07·code22 저장과 보관된119.08을 확인했다. 시험 후 확인:

- 기존 Raw 1·2의 전체 행 지문 일치, 새 Raw 영구 저장 없음.
- 기존 지역26/NAVER52/관광26/장소16/AI1의 **모든 기존 컬럼 값·ID·수집 시각 동일**. 허용된 신규 메타데이터만 추가.
- 보관 테이블26행, 공개 SELECT 불가.
- 현재 관광 테이블의 서울 값은 **기존119.08/code2201/raw_id2 그대로**다. 97.07로 영구 갱신한 것은 아니다.
- 이후 정상 수집을 저장하면 현재 테이블에는 code22가 반영되고, 기존 2201 관측값은 Raw와 보관 테이블에 남는다.

따라서 현재 Dashboard와 기존 AI 요약의 119.08을 관광소비강도라고 해석하면 안 된다. 다음 실제 배치 적재·화면 검증 때 metric_code=22 데이터로 전환하고 AI 요약도 새 지표를 기준으로 재생성해야 한다. 이번에는 기존 AI 내용을 덮어쓰지 않았다.

## 검사 및 재현

- 별도 PostgreSQL에서 호환 수정 검사 **9개 통과**: 기존 값 보존, 26행 보관, migration 반복, 실제22 값, 기존119.08 보존, 재실행 중복 방지, 잘못된2201 거부, 후속 오류 시 롤백, 보관 테이블 공개 접근 차단.
- 실제 Supabase Trigger 시험 **PASS** 후 롤백.
- Make 저장 후 새로 불러온 구성에서도 코드22와 Parse response=No를 재확인했다.
- Chapter14-1은 수정하지 않았다. Make 일정은 Inactive/On demand 유지. 추가 NAVER Cloud 로그인은 필요하지 않았다.

기존 DB에는 새 `006`만 적용했다. 새 테스트 DB를 만들 때는 `001 → 003 → 006` 순서로 적용해야 한다. **006 이후에 003을 단독 재적용하면 옛2201 함수로 돌아가므로 피한다.** 기존 003 파일은 역사 기록과 이전 회귀 검사 재현을 위해 보존한다.

```powershell
cd C:\dev\llm-data-analysis-course\assignments\chapter14-2\sql\tests
npm ci
npm run test:metric22
```

테스트는 로컬 `artifacts/batch-20261019-104333/`와 `artifacts/lesson-step16/consumption-request22.json`의 실제 응답을 사용한다. 이 입력은 Git 제외이며 운영 DB를 호출하지 않는다.

실제 응답·대조 기록: `artifacts/lesson-step16/`. 화면 증거: `artifacts/evidence/lesson-step16-http1.jpg`~`http4.jpg`, `lesson-step16-db-rollback.jpg`. 키가 포함될 수 있는 수정 전 Make 백업은 Git 제외 private 파일로 보존한다.

강의 STEP16 및 추가 승인된 DB 호환 수정까지 진행했다. STEP17의 새 영구 배치 적재, AI 재생성, 지도·배포는 이번에 수행하지 않았다.
