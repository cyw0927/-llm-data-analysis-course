# 강의 STEP 17~24: 실제 배치 저장과 자동 처리 완료

검증일: 2026-10-19 (Asia/Seoul). 기존 Make 시나리오·처리 함수·Trigger를 재사용했다. 소비 지표22로 전체 흐름을 **실제 1회 실행해 영구 저장**했다. STEP16의 롤백 시험과 구분한다.

## 단계별 결과

| 강의 단계 | 실제 결과 |
|---|---|
| STEP 17 Raw 저장 연결 | HTTP 4개 → Supabase Create a Row 1개. source=BATCH_RAW 및 네 원문 매핑 일치. id/run_id/fetched_at/상태는 DB 관리 |
| STEP 18 Raw INSERT | 새 Raw **id=5** 저장. 원문 길이 NAVER2344/체류4238/소비4161/Local1405로 모두 0보다 큼 |
| STEP 19 NAVER 함수 | 실제 자동 처리 52행. 4키워드·13개월이므로 강의 예시40과 다른 정상 건수 |
| STEP 20 관광 함수 | 26행 결합, 체류26/소비26 모두 존재, 미완성0, metric_code=22인 행26 |
| STEP 21 Local 함수 | 장소5건, HTML 태그 잔존0, 결측·범위 오류 좌표0. 기존 seed와 같은 SHA256 식별 규칙 및 주소별 실제 자치구 코드 유지 |
| STEP 22~23 Trigger | 비내부 Trigger1개, 활성 O, AFTER INSERT FOR EACH ROW. 함수3개와 Trigger 함수의 지문이 검증된 SQL과 일치 |
| STEP 24 전체 실행 | Make Success, **5 operations**, SQL에서 Raw5 PROCESSED·error NULL·정제52/26/5 확인 |

**함수를 수동 호출하기 전에** 자동 처리 결과를 먼저 조회해 STEP24를 확인했다. 이후 STEP19~21 개별 함수 재실행 검사는 별도 트랜잭션에서 수행하고 ROLLBACK했다. 이 검사는 PASS이며 기존 수집 시각을 추가로 변경하지 않았다.

## 실제 실행 증거

- 시나리오: `7992550`, `Tourism Dashboard | Raw collection`.
- [2026-10-19 15:07:11 실행 — Success, 6초, 5 operations](https://eu1.make.com/3207920/scenarios/7992550/logs/64d384b1aca74f328477281d395961e9)
- 새 run_id: `724e99a4-9226-4c46-a1ab-8071f94be5d0`.
- Raw id: **5**, source: BATCH_RAW, 상태: **PROCESSED**.
- 처리 완료: 2026-10-19 15:07:18 KST.
- 오류: 없음. Raw/보관 테이블 공개 SELECT 권한 없음.
- 실제 Table Editor를 새로고침해 Raw id **1, 2, 5의 총3건**을 확인했다.
- 단일 Trigger 이름은 `after_insert_batch_raw`다. 강의 예시와 이름만 다르므로 중복 생성하거나 기존 것을 삭제하지 않았다.

## 소비 지표 정정의 실제 반영

현재 `tourism_demand` 서울(11), 2025-09-01:

```text
consumption_strength = 97.07
consumption_metric_code = 22
raw_id = 5
```

**이번에는 97.07이 실제 현재 테이블에 반영됐다.** 이전 STEP16에서 현재 테이블의119.08을 유지했던 기록은 당시 롤백 시험의 결과다.

기존 `2201/119.08`은 외지인 소비액 지표이며 소비강도22와 다른 값이다. 기존 Raw1·2 전체 지문과 `tourism_demand_metric_archive`26행의 전체 지문이 실행 전후 동일하다. 따라서 현재 테이블을22로 갱신하면서 기존 원본·관측값도 보존했다.

## 보존 및 품질 확인

| 대상 | 이전 | 이후 | 확인 |
|---|---:|---:|---|
| regions | 26 | 26 | 전체 내용 동일 |
| naver_trend | 52 | 52 | 기존 ID 유지, 새 Raw 기준 Upsert |
| tourism_demand | 26 | 26 | 기존 ID 유지, 올바른22 값으로 Upsert |
| local_places | 16 | 17 | 기존16개 ID 유지, 새 장소1건 추가. 최신 Raw 연결은5건 |
| ai_region_analysis | 1 | 1 | 전체 내용 동일, 이번에 재생성하지 않음 |
| raw_api_data | 2 | 3 | 기존 원문2건 그대로 + 새 배치1건 |
| tourism_demand_metric_archive | 26 | 26 | 전체 내용 및 지문 동일 |

- 날짜·키워드, 날짜·지역, place_key 중복: 모두0.
- 최신 관광26행의 체류·소비 결측:0.
- 최신 관광 Raw의 소비 API resultCode=0000, 지표 코드22만 존재.
- 최신 장소5건의 HTML 태그·결측 좌표·국내 범위 밖 좌표:0.
- Chapter14-1은 수정하지 않았다.
- Make는 **Inactive / On demand** 유지. 이메일 발송, AI 호출, 새 일정 활성화 없음.

## 로컬 파일과 재현

작업 경로: `C:\dev\llm-data-analysis-course\assignments\chapter14-2`.

- `sql/007_verify_lesson17_24.sql`: 읽기 전용 단계별 검증 SQL.
- `sql/008_verify_processors_rollback.sql`: 실제 함수3개 단위 검증 및 롤백.
- `artifacts/lesson-step24/db-before.json`, `db-after.json`: 기존 ID 보존 대조.
- `artifacts/lesson-step24/lesson-step24-db-before.json`, `lesson-step24-db-after.json`: Raw·보관 테이블 지문과 전체 자동 처리 검증 결과.
- `artifacts/lesson-step24/lesson-step24-unit-rollback.json`: 함수 단위 검증 PASS.
- `artifacts/evidence/lesson-step24-make-success.jpg`: 5모듈 모두 성공 화면.

기존 DB에 migration을 다시 실행할 필요는 없었다. 코드22 수정은 이미 적용된006을 그대로 사용했다. 새 테스트 DB를 만드는 경우 `001 → 003 → 006` 순서를 지킨다.

## 다음 구간

STEP25~28에서 **현재 DB의 code22 데이터**를 읽어 AI 요약을 재생성해야 한다. 기존 AI 기록은119.08을 사용한 과거 지표의 해석일 수 있으므로 새97.07의 요약으로 취급하지 않는다. 이번에는 그 기록을 보존했다.

그다음 지도·기간 필터·로컬 화면 검증과 GitHub/Vercel 배포를 진행한다. 예약 실행은 사용자 요청 전까지 켜지 않는다. 이번 작업은 STEP24에서 마쳤다.
