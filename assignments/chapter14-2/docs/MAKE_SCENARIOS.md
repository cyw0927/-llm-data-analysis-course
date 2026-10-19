> **2026-10-19 상태 갱신:** 수집 자동화는 HTTP 4개 → Supabase Create a Row 1개 → Raw Trigger로 실제 2회 검증했습니다. 최신 결과와 실행 방법은 [STEP4_VERIFIED.md](../STEP4_VERIFIED.md)를 기준으로 보세요. 아래 내용은 이전 초기 구성 기록이며 기존 프로젝트를 다시 생성하거나 이전 4개 시나리오 구성을 적용하지 마세요.

# Make 운영 수집 설정 — 4개 독립 Scenario (강의 STEP 10~28)

목적: **매일 Make → 검증 → Supabase Upsert**, AI 요약 결과도 Supabase에 별도 저장. Chapter 14-1 Gmail/PDF 자동화와 직접 연결하지 않는다. 최초 테스트는 전부 **Run once**. 비밀값은 Make Connection/HTTP 비밀 헤더에만 저장하며 JSON 출력·스크린샷·DB error_message에 기록하지 않는다.

## 0. 사전 조건
1. Supabase SQL 001_init.sql 적용 및 필요한 Seed 데이터 검증.
2. NAVER API HUB Search Trend, NAVER Local Search, 한국관광공사 체류·소비 강도 API 사용 신청.
3. 한국관광공사 Swagger에서 체류·소비 **정확한 endpoint/파라미터/JSON 필드**를 확인.
4. AI 요약에 사용할 GPT/Gemini/Claude **하나의 서비스**만 설정.
5. Make Code Python은 제공 플랜·내장 라이브러리 확인. pandas가 없다면 순수 Python/Iterator/JSON Parser 또는 Supabase SQL/View 선택. Make Code가 아예 없다면 기본 Make 모듈로 진행.

## Scenario 1 — CH14-2 NAVER Trend Daily
- Scheduler는 비활성으로 저장하고 HTTP POST `https://naverapihub.apigw.ntruss.com/search-trend/v1/search`.
- Headers: `X-NCP-APIGW-API-KEY-ID`, `X-NCP-APIGW-API-KEY`, `Content-Type: application/json`.
- Body: `startDate/endDate` 현재 수집 기간에 맞게 설정, `timeUnit=month`, keywordGroups 여행/축제/캠핑/맛집.
- Run once: `results[].title`, `data[].period`, `data[].ratio`, 숫자 0~100, 네 키워드 검증.
- 날짜 + 키워드 단위로 매핑 후 Supabase REST:
  `POST https://<PROJECT-REF>.supabase.co/rest/v1/naver_trend?on_conflict=reference_date,keyword`.
- Headers: `apikey`와 `Authorization: Bearer <SUPABASE_SECRET_KEY>`, `Content-Type: application/json`, `Prefer: resolution=merge-duplicates,return=representation`.
- 두 번 Run once해도 (reference_date, keyword) 중복 0건이어야 한다.
- ratio는 **전국 상대 검색 관심도**, 검색 건수·지역별 값 아님.

## Scenario 2 — CH14-2 Tourism Demand Daily
- Scheduler (비활성) → 한국관광공사 **체류/소비 각각 HTTP 호출** → JSON 검사 → 키(region_code, 기준월)로 합치기 → Supabase Upsert → collection_runs.
- API Swagger 응답 성공 `resultCode=0000` 확인. `totalCount`에 따라 페이지 처리. 응답에 실제 item 행이 없는 200은 실패.
- 실제 체류 응답 예: `baseYm=202509`, `areaCd=11`, `signguCd=0`이면 서울 전체, `signguCd=11110`이면 종로구. `tarSjrnDsIxVal`은 체류 강도.
- 소비 응답의 value 키는 실제 JSON 확인 전 하드코딩하지 말 것.
- 두 API의 지역코드·월이 **정확히 일치**해야 합친다. 일치하지 않는 행은 억지로 채우지 않고 별도 로그 기록.
- 월 `202509`는 표준 `reference_date=2025-09-01`로 저장 (수집일과 구분).
- Supabase REST: `/rest/v1/tourism_demand?on_conflict=reference_date,region_code`, `Prefer: resolution=merge-duplicates` 적용.
- 성공/실패·행수는 `collection_runs` 기록. API 키가 포함된 오류 URL 절대 기록 금지.

## Scenario 3 — CH14-2 NAVER Local Daily
- Scheduler 비활성 → GET `https://naverapihub.apigw.ntruss.com/search/v1/local` (NAVER API HUB Local)
- Headers: NAVER Client ID/Secret; Query: 지역+관광지/맛집/카페/숙박, `display=5`, `start=1`, `sort=comment`, `format=json`.
- `items[]`에서 `title,link,category,address,roadAddress,mapx,mapy` 추출.
- `title` HTML 강조 태그 제거, `place_key` = SHA256(region_code|search_category|clean_name|normalized_address).
- `mapx → longitude`, `mapy → latitude`. WGS84 값인지 숫자 범위 확인. 좌표 누락 행은 null 표시하고 마커 생성 안 함.
- Supabase REST `/rest/v1/local_places?on_conflict=place_key`. 새로운 검색결과가 이전 모든 장소를 삭제하지 않도록 관리.
- 실제 검색 결과는 지역 전체 장소 DB가 아닌 **대표 최대 5개**다.

## Scenario 4 — CH14-2 AI Region Summary Daily
- Scheduler 비활성 → Supabase 검증된 최신 지역 지표·장소 수 조회 → LLM → JSON 검증/정리 → `ai_region_analysis` Upsert.
- Input에 지역코드/기준일/체류·소비 강도/장소 카테고리 개수/전국 NAVER Trend 상대지수(지역값으로 혼동 금지)를 포함.
- 프롬프트: 「입력에 없는 숫자 만들지 말고 관찰·한계·추가 확인만 작성. 두 지표를 같은 척도로 직접 비교하지 말고 원인을 단정하지 말 것.」
- 저장: `analysis_date,region_code,summary,limitations,llm_provider,model_name`.
- 고유키 `analysis_date + region_code`; 새로 실행해도 같은 날짜 같은 지역 1행 유지.
- 사용한 모델명·분석 시점 기록. 호출 실패 시 비어 있는 요약을 성공 처리하지 말 것.

## 예약 활성화 전 Gate
- Seed PASS
- 각 Scenario Run once 결과 실제 row와 Supabase DB 값 대조
- 재실행 중복 0건
- `collection_runs` 결과 확인
- 그다음에만 Asia/Seoul에서 1일 1회; 예시 실행 순서는 Trend→Tourism→Local→AI (원본 최신 데이터가 저장된 **후** AI 실행)

Vercel/Next.js는 Supabase **조회 전용**. 외부 API 호출, Make Secret Key, Gemini Secret Key를 브라우저/프런트 코드에 넣지 않는다.
