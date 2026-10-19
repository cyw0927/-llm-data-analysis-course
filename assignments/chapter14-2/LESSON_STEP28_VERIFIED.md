# Chapter 14-2 — 강의 STEP 25~28 실제 검증

검증일: 2026-10-19 (Asia/Seoul). STEP 29 예약 활성화 및 이후 Dashboard/배포는 이번 범위에서 진행하지 않음.

## 실제 구성

- 수집 A: 기존 7992550, HTTP 4개 → Supabase Raw 1개 유지.
- AI B: [Tourism Dashboard | AI summary](https://eu1.make.com/3207920/scenarios/8041443/edit), 별도 생성.
- Supabase tourism_demand 조회(서울 전체 11, 소비 지표 코드 22, 최신 관측월 1행) → naver_trend 조회(최근 8행: 2개월 × 4키워드) → local_places 조회(서울 코드 11로 시작, 최근 갱신 5곳) → OpenAI Simple text prompt 1회 → ai_region_analysis Upsert.
- 모델: gpt-5-nano. Make 제공 Simple text prompt이며 별도 OpenAI API 키 연결 없음. 무료 플랜의 Make credits는 사용됨. 무제한 무료 아님. 첫 실행 6.42, 보완 실행 6.79 credits.
- 대표 지역 서울 1개만 분석. 스케줄 Inactive / On demand. 메일 없음.

## 실제 실행 결과

- 16:13:25 첫 실행 성공, 26초, 5 operations. [이력](https://eu1.make.com/3207920/scenarios/8041443/logs/32791de7efe448eab03dd1ecead9d32a). 수치는 맞았으나 검색/장소 설명 누락으로 프롬프트 보완. 첫 입력/출력과 DB 결과는 artifacts/lesson-step28에 보존.
- 16:14:33 보완 실행 성공, 32초, 5 operations. [이력](https://eu1.make.com/3207920/scenarios/8041443/logs/827c88586d3b4582b99e98641f88065c).
- 저장: ai_region_analysis id=3, analysis_date=2026-10-19, region_code=11, model_name=gpt-5-nano. 날짜는 Asia/Seoul 현재 날짜 식 사용. 같은 날짜/지역 재실행은 기존 오늘 행을 Upsert하며 중복 없음.
- 요약 수치: 관광 2025-09 체류 89.81 / 소비 97.07(코드 22); 전국 맛집 ratio 2026-10 46.10507 / 2026-09 75.28529. 대표 장소 낙성대공원·경복궁. 실제 조회값과 모두 일치. raw_id 5 출처 명시.
- 기준 기간·지역 차이, 부분 월 가능성, 상대 관심도와 실제 방문객 수의 차이, 인과 추정 금지를 저장.
- 기존 2026-10-16 AI id=1은 원문 그대로 보존(당시 잘못된 2201 수치 119.08이 있으므로 최신 해석에 사용 금지).
- 전후 원본/정제/보관 행수 동일: raw 3, trend 52, tourism 26, places 17, archive 26. 이번 실행은 수집 API를 호출하지 않음.

## 재현 파일

- make/ai-summary.template.json: 비밀키 없음. 연결 ID는 null로 제거됨. 다른 Make 계정에서 가져올 경우 기존 Supabase API Key 연결을 수동 지정하고, ai_region_analysis Body structure 필드도 재선택해야 함. Supabase 쓰기 Secret은 서버 측 Make 연결에만 보관.
- sql/009_verify_ai_summary.sql: 읽기 전용 검증 SQL.
- artifacts/lesson-step28/ai-validation.json: 기존 요약 보존, 원본 행수 보존, 같은 오늘 ID 유지, 수치·장소·출처 포함 검사 모두 true.
- artifacts/evidence/ai-summary-success.jpg, ai-summary-history.jpg, ai-summary-db.jpg.

## 범위와 한계

검증된 정제 테이블만 입력하고 Raw JSON을 AI에 보내지 않는다. 모델이 JSON 전처리나 원본 수치 수정을 하지 않는다. 공개 관측값만 모델에 전달한다. 현재 프롬프트는 서울과 4개 키워드 수집 설정을 대상으로 하며, 수집 대상 변경 시 프롬프트/조회 개수도 검토해야 한다. 실시간 데이터 유무 자동 차단과 여러 지역 일괄 생성은 아직 구현하지 않았다. Git 커밋/푸시 및 Vercel 배포는 수행하지 않았다.
