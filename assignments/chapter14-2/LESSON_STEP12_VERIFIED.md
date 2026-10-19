> **소비 지표 정정(2026-10-19):** 이전 2201/119.08은 외지인 소비액이며 강의의 소비강도22/97.07과 다릅니다. 기존 값은 보존했고 Make와 DB 호환을 정정했습니다. [STEP13~16 검증 기록](LESSON_STEP16_VERIFIED.md)을 우선 보세요.

# 강의 STEP 9~12 검증 기록

검증일: 2026-10-19 (Asia/Seoul). 이번 범위는 강의자료 STEP 9~12다. 기존 데이터와 자동화 설정을 읽기 전용으로 확인했으며 새 수집 실행, CSV 재적재, DB 구조 변경, 스케줄 활성화는 하지 않았다.

| 강의 단계 | 실제 확인 결과 |
|---|---|
| STEP 9 Seed 검증 SQL | 관광 26행, 날짜·지역 중복 0, 체류·소비 결측 0, 예상 기준일 2025-09-01. 서울 값 89.81 / 119.08 등 CSV와 일치 |
| STEP 10 운영 구조 | 기존 Make Scenario 7992550을 다시 읽어 HTTP 4개 → Supabase Create a Row 1개 확인 |
| STEP 11 Make 단순화 원칙 | Iterator·Router·JSON Parse·Filter·AI 전처리 없음. HTTP 4개 모두 Parse response=No. 후속 행별 저장 없이 Raw 한 번 저장 |
| STEP 12 Raw 구조 | Table Editor에서 `raw_api_data` 직접 확인. 강의 필수 컬럼 12개 및 추가 처리 건수 컬럼 1개 존재. 원문 컬럼 4개 모두 text |

## STEP 9: Seed SQL

- `tourism_demand`: **26행**.
- `(reference_date, region_code)` 중복 키: **0개**.
- `stay_strength` 또는 `consumption_strength` 결측 행: **0개**.
- 최신 기준일: **2025-09-01**. 현재 수집 날짜와 관측 기준월을 구분한다. 최신 공표월을 자동 발견한 결과는 아니다.
- 최근 표본: 서울(11) 89.81/119.08, 종로구(11110) 84.26/108.49, 중구(11140) 81.33/199.21.
- 관광 CSV SHA256은 STEP 8과 동일: `63b76c96ad483c0688d0467a6143bd02233b6ef1b4abed8d2c5581fbaf83aad8`.

## STEP 10~11: 책임 분리

```text
Make: NAVER Trend → 관광 체류 → 관광 소비 → NAVER Local → Supabase Create a Row
DB:   raw_api_data → AFTER INSERT Trigger → 처리 함수 3개 → 정제 테이블
```

기존 시나리오 이름은 `Tourism Dashboard | Raw collection`이다. 모듈 ID는 1, 2, 3, 12, 11 순서이며 총 5개다. 마지막 모듈은 Raw 컬럼에 `{{1.data}}`, `{{2.data}}`, `{{3.data}}`, `{{12.data}}`를 각각 매핑한다. `source=BATCH_RAW`이고 ID와 처리 상태는 DB가 관리한다. 고립된 모듈도 없다.

Make에서 배열을 Iterator로 나누면 뒤의 저장 모듈이 행 수만큼 반복될 수 있다. 현재 구성은 원본 배치 1건을 저장하고 DB가 정제하므로 수집 시나리오에 전처리 모듈을 더할 필요가 없다. AI 지역 해석은 뒤 단계의 별도 흐름이다.

이번에는 기존 구성을 조회만 했으며 Run once를 추가 실행하지 않았다. **Inactive / On demand 유지**.

## STEP 12: 실제 Raw 테이블

필수 컬럼:

`id`, `run_id`, `source`, `naver_trend_raw`, `tourism_demand_raw`, `tourism_consumption_raw`, `naver_local_raw`, `fetched_at`, `process_status`, `processed_at`, `error_message`.

추가 컬럼: `processed_counts` (jsonb, 각 처리 건수 기록).

- `id`: bigint identity.
- `run_id`: UUID, 기본값 `gen_random_uuid()`.
- 네 Raw 컬럼: text. 수집 응답을 그대로 보관하고 DB 함수에서 jsonb로 해석한다.
- `source`: 기본값 BATCH_RAW.
- `fetched_at`: timestamptz, 기본값 now().
- `process_status`: 기본값 PENDING. 성공 시 PROCESSED, 실패 시 ERROR를 기록하는 기존 구조다.
- 오류 기록은 응답·인증정보를 노출하지 않도록 SQLSTATE 기반의 안전한 오류 코드로 남긴다.
- Raw RLS 활성화, anon 공개 SELECT 권한 없음. Table Editor에 보이는 것은 로그인한 postgres 역할의 관리 화면이다.

| Raw ID | 상태 | 원문 4개 | JSON 객체 변환 | 처리 건수 | 오류 |
|---|---|---|---|---|---|
| 1 | PROCESSED | 모두 있음 | 모두 정상 | NAVER 52 / 관광 26 / 장소 5 | 없음 |
| 2 | PROCESSED | 모두 있음 | 모두 정상 | NAVER 52 / 관광 26 / 장소 5 | 없음 |

PENDING→PROCESSED 전환은 Trigger 안에서 빠르게 완료되므로 Table Editor에서 PENDING 행이 보이지 않는 것은 정상이다. 이번에는 상태를 보여주려고 기존 행을 PENDING으로 바꾸거나 가짜 데이터를 삽입하지 않았다.

## 재현 및 증거

- 읽기 전용 SQL: `sql/005_verify_lesson9_12.sql`.
- 실제 SQL 결과와 비밀 값 없는 Make 구조 요약: `artifacts/lesson-step12/lesson-step12-audit.json`.
- Table Editor 화면: `artifacts/evidence/lesson-step12-raw-table.jpg`.
- Make 5개 모듈 화면: `artifacts/evidence/lesson-step12-make-flow.jpg`.
- [Supabase Raw Table Editor](https://supabase.com/dashboard/project/eoujbpxqmqtfxjlrybiz/editor/17723?schema=public)
- [기존 Make 시나리오](https://eu1.make.com/3207920/scenarios/7992550/edit)

강의 STEP 12까지 확인했다. 기존 구성에 이후 단계 일부가 이미 구현돼 있지만, 이번 작업에서 STEP 13 이후 설정을 추가 변경하지 않았다. GitHub 푸시·Vercel 배포도 수행하지 않았다.
