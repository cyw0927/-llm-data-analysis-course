> **소비 지표 정정(2026-10-19):** 이전 2201/119.08은 외지인 소비액이며 강의의 소비강도22/97.07과 다릅니다. 기존 값은 보존했고 Make와 DB 호환을 정정했습니다. [STEP13~16 검증 기록](LESSON_STEP16_VERIFIED.md)을 우선 보세요.

> 번호 안내: 이 문서의 1~4는 자체 작업 묶음 번호입니다. 강의 STEP 5~8의 CSV 결과는 [LESSON_STEP8_VERIFIED.md](LESSON_STEP8_VERIFIED.md)를 보세요.

# Chapter 14-2 — 1~4단계 검증 기록

검증일: 2026-10-19 (Asia/Seoul). 이번 범위는 기존 코드 보존·통합, 추가 SQL, Make 수집 구성, 실제 원본→자동 정제 검증까지다. 지도·AI 자동화·GitHub 반영·Vercel 배포는 다음 단계다.

## 기존 프로젝트와 보존

- 기준 경로: `C:\dev\llm-data-analysis-course\assignments\chapter14-2`
- 기준 GitHub: https://github.com/cyw0927/-llm-data-analysis-course/tree/main/assignments/chapter14-2
- `C:\dev\tourism-dashboard`는 `cyw0927/coffee`의 대시보드 작업 복제본이다. 그곳의 미커밋 개선분 13개 파일을 백업 후 위 과제 폴더로 복사했다. 원본 복제본과 별도 `C:\dev\coffee`는 수정하지 않았다.
- Chapter 14-1과 Chapter 13의 기존 사용자 변경은 수정하지 않았다.
- GitHub main과 로컬 HEAD는 점검 당시 `2ab6a45`로 같았다. 이번 변경은 로컬에 저장했으며 아직 커밋/푸시하지 않았다.
- 기존 파일 백업, DB 점검 전후 스냅샷, 인증정보를 포함할 수 있는 Make 백업은 Git 제외 `artifacts/`에 보존한다. 업로드하지 말 것.

## 실제 연결 결과

| 대상 | 실제 확인 결과 |
|---|---|
| NAVER Trend | 성공, 월별 4키워드 × 13개월 = 52행 |
| 관광 체류 | `resultCode=0000`, 26행/totalCount=26, 기준월 202509, 지표 21 |
| 관광 소비 | `resultCode=0000`, 26행/totalCount=26, 기준월 202509, 지표 **2201** |
| NAVER Local | 서울 관광명소, display=5, start=1, sort=random, 실제 5건 |
| Supabase | 기존 프로젝트 `eoujbpxqmqtfxjlrybiz`, 추가 migration 적용 |
| Make | 기존 Scenario **7992550** 수정, 아래 실행 2회 모두 Success/5 operations |

관광 기준월은 기존 성공 설정 202509를 사용했다. 최신 공표월 자동 발견까지 구현했다는 의미가 아니다. NAVER의 마지막 월은 월중 누적 상대 관심도이며 관광 지표와 관측 기간이 다르다. Local은 전체 관광지 목록이 아닌 대표 검색 결과다.

## Make 수집 시나리오

이름: **Tourism Dashboard | Raw collection**

`HTTP #1 NAVER Trend → HTTP #2 체류 → HTTP #3 소비 → HTTP #12 NAVER Local → Supabase #11 Create a Row`

- HTTP 4개 모두 Parse response = No.
- Supabase 연결: `Chapter 14-2 Supabase Raw`. 서버 키는 Make에만 저장한다.
- Table=`raw_api_data`, source=`BATCH_RAW`.
- `naver_trend_raw={{1.data}}`, `tourism_demand_raw={{2.data}}`, `tourism_consumption_raw={{3.data}}`, `naver_local_raw={{12.data}}`.
- id/run_id/fetched_at/process_status/processed_at/error_message는 매핑하지 않고 DB 기본값과 Trigger가 관리한다.
- Iterator, Router, Filter, AI 모듈 없음. 자동 일정 **Inactive / On demand**.
- 기존 GPT-5 nano AI/HTTP 저장 설정은 수정 전 백업에 보존했다. 별도 DB→AI 시나리오는 이번에 만들지 않았다. 14-1 Gmail 시나리오도 수정하지 않았다.
- 비밀 값 없는 구성 참고 파일: `make/raw-collection.template.json`. 연결/키를 직접 지정하기 전에는 실행용이 아니다.

실행 증거:

1. [11:05:28 실행 — Success, 9초, 5 operations](https://eu1.make.com/3207920/scenarios/7992550/logs/44e3b8e0be8443859fca09b9419f76dd)
2. [11:06:57 실행 — Success, 8초, 5 operations](https://eu1.make.com/3207920/scenarios/7992550/logs/6189853e5d034a7888bfddc1fca9ca4a)

## DB 검증 결과

추가 SQL: `sql/003_raw_pipeline.sql`. 기존 행 삭제/초기화 없이 raw 테이블, nullable raw_id FK 3개, 인덱스, 처리 함수 3개, AFTER INSERT Trigger를 추가했다.

| Raw ID | 상태 | NAVER | 관광 결합 | 장소 | 오류 |
|---|---|---:|---:|---:|---|
| 1 | PROCESSED | 52 | 26 | 5 | 없음 |
| 2 | PROCESSED | 52 | 26 | 5 | 없음 |

현재 정제 행은 최신 원본 `raw_id=2`를 가리킨다. 이전 Raw 1의 원문·처리 건수 기록도 보존된다. 기존 seed에서 유래한 다른 장소에는 임의의 raw_id를 부여하지 않았다.

| 테이블 | 이전 | 검증 후 | 보존 결과 |
|---|---:|---:|---|
| regions | 26 | 26 | 내용 동일 |
| naver_trend | 52 | 52 | 기존 ID 유지, 최신 응답 Upsert |
| tourism_demand | 26 | 26 | 기존 ID 유지, 26개 지역/동일 기준월 정확히 결합 |
| local_places | 15 | 16 | 기존 15개 ID 유지, 검색 결과의 새 장소 1건 추가 |
| ai_region_analysis | 1 | 1 | 내용 동일, 새 AI 요약 생성 안 함 |

SQL과 기존 Python seed의 장소 식별 규칙을 통일했다: `SHA256(region_code|관광명소|정리한 이름|도로명주소 또는 주소)`. 좌표는 실제 응답의 1e7 배율을 위·경도로 변환하고 국내 범위를 검사한다.

관광 API 정상 코드·전체 페이지·중복·등록 지역·동일 기준월·지표 코드·숫자 범위를 검사한다. 불완전한 체류/소비 결합을 성공으로 처리하지 않는다. 실패하면 모든 정제 변경을 취소하고 원본만 ERROR로 남긴다. 오류 기록에는 SQLSTATE만 남겨 응답/키 노출을 막는다.

- Raw RLS 활성화, anon/authenticated/public 테이블 접근과 처리 함수 실행 권한 없음.
- 실제 Publishable Key로 Raw REST 요청 시 **HTTP 401**.
- 잘못된 장소 좌표를 넣는 실제 DB 검증: ERROR 확인 + 세 정제 테이블의 전체 행/값 불변 확인. 테스트 전체는 `ROLLBACK`하여 테스트 행을 남기지 않았다.
- 로컬과 운영 DB의 네 함수 본문 지문(공백·주석 제외)이 모두 일치했다.

## 로컬 검사 및 재현

- Python 테스트 **16개 통과**.
- Dashboard 동작 테스트 **11개 통과**.
- PostgreSQL 테스트 **19개 통과**: 실제 응답 처리, 중복 방지, 12개 오류/복구 사례, 비공개 접근/함수 실행 차단, migration 재실행.
- TypeScript 검사와 Next.js Production 빌드 통과. 빌드 성공은 지도/실제 배포 성공을 뜻하지 않는다.
- 기존 `ch14-2-tests.yml`에 Dashboard 테스트를 추가하고 Node 24/npm ci를 사용하도록 정리했다. 원격 CI 실행은 아직 하지 않았다.

```powershell
cd C:\dev\llm-data-analysis-course\assignments\chapter14-2
python -m unittest discover -s tests -v
cd dashboard
npm test
npm run typecheck
npm run build
cd ..\sql\tests
npm ci
npm test -- ..\..\artifacts\batch-20261019-104333
```

마지막 PostgreSQL 테스트는 지정 폴더의 실제 API 응답 4개와 `before_*.json` 보존 스냅샷을 별도 테스트 DB에 적재한다. 외부 API/운영 DB를 수정하지 않는다. 이 로컬 fixture 폴더는 Git에 포함하지 않는다.

## 다음 단계

1. NAVER Maps 대표 계정/무료 적용 및 Maps Application·허용 URL·키 확인.
2. Dashboard 기간 필터와 실제 지도 Marker 최종 검증.
3. 검증된 DB 데이터를 읽는 별도 GPT-5 nano AI 요약 자동화 구성·검증.
4. 변경 검토·비밀 값 검사 후 GitHub 커밋/푸시, Vercel Preview → Production 검증.

예약 실행은 사용자의 별도 활성화 요청 전까지 끈다. 기존 데이터 삭제/초기화는 하지 않는다.
