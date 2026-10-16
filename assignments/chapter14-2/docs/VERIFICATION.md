# Chapter 14-2 검증/제출 체크리스트

**검증 전 운영·프로덕션 배포 금지.** 실제 성공만 체크하고 서비스에 표시되는 수치 출처/기준 기간 기록.

## STEP 0~3 Supabase
- [ ] 프로젝트 생성, URL·Publishable Key 확인
- [ ] 001_init.sql 실행, regions/naver_trend/tourism_demand/local_places/ai_region_analysis/collection_runs 6개 테이블 확인
- [ ] 각 테이블 RLS 활성화/anon SELECT 정책 점검
- [ ] Dashboard에는 Publishable Key, Make에는 Secret Key로 역할 분리
- [ ] 서비스 키가 공개 저장소와 브라우저에 없는지 점검

## STEP 4~9 Seed
- [ ] 실제 수집 Raw 파일 확보(출처·기준일 기록)
- [ ] seed/prepare_seed.py 실행(파싱 오류 0건, 중복 검증)
- [ ] processed/tourism_demand_seed.csv 결측·중복·날짜·숫자 검사
- [ ] Supabase CSV Import, 테이블 row_count > 0
- [ ] 002_verify.sql 중복 쿼리 결과 0행, 최신 날짜 확인

## STEP 10~28 Make
- [ ] Make Code/pandas 가능 여부 확인. 안 되면 순수 Python/기본 모듈/SQL 사용
- [ ] NAVER Trend Daily: Run once → 필드 검사 → Upsert → 중복 없음
- [ ] Tourism Demand Daily: 체류·소비 Run once → 기준월·지역코드 검증 → Upsert
- [ ] NAVER Local Daily: 응답 5개 이내·mapx 경도·mapy 위도/HTML 제거 검증 → Upsert
- [ ] AI Summary Daily: Supabase 검증 결과만 LLM에 전달 → 결과 Upsert
- [ ] collection_runs 실행 성공·실패 기록 검증 (Secret 로그 절대 금지)
- [ ] 4개 Scenario 전부 수동 PASS 후에만 매일 스케줄 사용자가 승인하여 켜기

## STEP 29~40 Dashboard
- [ ] npm install / npm run dev / npm run build
- [ ] Supabase 실데이터 조회 (키/권한/RLS 검증)
- [ ] 지역·카테고리 필터와 KPI, NAVER 상대 검색 관심도 차트 표시
- [ ] NAVER Maps, marker 실제 위치·경도/위도 표시
- [ ] 저장된 최신 AI 분석 표시(실시간 LLM 호출 아님)
- [ ] 오류/빈 데이터 상태·모바일 화면 확인
- [ ] 외부 NAVER/관광 원본 API는 Dashboard에서 호출하지 않음

## STEP 41~50 배포
- [ ] Git status에서 .env.local 및 비밀키 제외
- [ ] Vercel Root Directory = assignments/chapter14-2/dashboard
- [ ] Vercel 환경변수는 NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_NAVER_MAP_NCP_KEY_ID만 사용
- [ ] Preview URL 검증 후에만 Production 배포
- [ ] Production 화면·지도 마커·차트·실데이터 확인

## 실제 제출 증빙
Supabase 테이블/Seed Import/최신 데이터, Make 4개 Scenario와 History, Dashboard 지도와 차트·AI 요약, GitHub URL 및 Vercel Preview/Production URL. API 키·Secret·개인정보 캡처 금지.

## 현재 이 저장소에서 자동으로 증명할 수 없는 항목
Supabase 계정 프로젝트 생성, Make 계정 로그인/시나리오 활성화, NAVER Maps 도메인 등록, Vercel 프로젝트 연결/실배포는 실제 사용자 계정 권한 및 서비스 설정 필요.
