> 후속 검증 완료: 모바일과 Vercel 배포 결과는 [DEPLOYMENT_VERIFIED.md](DEPLOYMENT_VERIFIED.md)를 확인하세요. 아래 내용은 STEP41 당시 기록입니다.

# Chapter 14-2 — STEP 30~41 실제 연결 검증

검증일: 2026-10-19 (Asia/Seoul).

## 완료 범위

- STEP 29: 이전 사용자 요청에 따라 수집·AI 스케줄은 Inactive / On demand 유지. 예약 활성화는 별도 승인 전까지 보류.
- STEP 30: STEP 24에서 Raw INSERT→Trigger→정제 52/26/5, STEP 28에서 AI 조회→생성→저장을 실제 실행 검증했다. 이번 단계는 기존 데이터를 읽기만 했고, 별도 수집 Batch를 추가하지 않았다.
- STEP 31~36: 기존 Next.js 소스 재사용. 기존 복제본의 공개 Supabase URL·Publishable Key만 정식 과제 dashboard/.env.local에 복사했다. 원본 환경 파일은 보존. 실제 화면에서 서울 89.81/97.07, 장소 17곳, 전국 검색 관심도 13개월·52행, 2026-10-19 AI 요약 표시를 확인했다.
- 기간 선택을 추가했다. 전체/최근 관측 12개월/6개월 중 선택하며 검색 관심도 차트·관측값 수에 적용된다. 관광 기준월은 2025-09로 별도 표시하고 기간을 억지로 맞추지 않는다. 실제 6개월 선택 시 24행, 4키워드 모두 유지했다.
- STEP 37~38: 기존 Maps Application이 없음을 확인하고 `TourismDashboard` 앱을 등록했다. Dynamic Map만 선택. Web URL은 http://localhost:3000 및 http://127.0.0.1:3000 두 개만 허용. Vercel 주소는 아직 등록하지 않았다.
- 등록 후 현재 계정이 대표 계정이라는 콘솔 확인 완료. 지도 API의 일별·월별 한도를 각각 1,000회, 한도 초과 사용은 허용안함으로 저장했다. 무료 이용량은 대표 계정에 자동 적용된다는 공식 FAQ도 확인했다. 한도 기능은 수초 내 초과 가능성이 있다고 콘솔이 안내하므로 완전한 비용 보장으로 표현하지 않는다.
- 지도 공개 Client ID만 Git 제외 .env.local에 추가했다. Client Secret은 로컬 대시보드·브라우저에 복사하지 않았다. 브라우저에는 지도용 공개 ID와 Supabase Publishable Key만 사용한다.
- STEP 39~41: 지도 타일과 마커 17개, 지역별 KPI, 차트, 저장된 최신 AI 브리핑을 실제 화면에서 확인했다. 대시보드는 NAVER Trend·관광·Local·AI API를 직접 호출하지 않고 Supabase의 정제 테이블과 저장된 요약을 읽는다. 지도 SDK/타일만 NAVER Maps에 연결한다.

## 실제 UI 검증

- 서울 전체: 체류 89.81 / 소비 97.07, 17개 장소·17개 좌표 마커.
- 카페: 5개 장소·5개 마커.
- 종로구 + 카페 + `카멜` 검색: 장소·마커 각각 1개, 체류 84.26 / 소비 92.13. 서울 전체의 AI 요약을 종로구 요약으로 재사용하지 않고 분석 대기를 표시한다.
- AI 최신 분석일 2026-10-19, 모델 gpt-5-nano, source raw_id 5 확인.
- Supabase ai_region_analysis 테이블에 이전 id 1과 오늘 id 3, 총 2개 기록 확인. 과거 데이터 삭제 없음.
- 브라우저 오류·경고 로그 0건(개발 및 배포용 로컬 화면).
- Node 테스트 12개 PASS. TypeScript 검사 PASS. Next.js 15.5.28 production build PASS.
- 로컬 빌드 결과를 `npm run start -- --hostname 127.0.0.1 --port 3000`으로 실행 중.

## 남은 Gate

STEP 42의 모바일 실제 화면 검증은 아직 미완료다. 브라우저 viewport 기능에 390×844를 지정했으나 실제 DOM viewport는 1077px/1265px로 유지되어, 모바일 PASS로 기록하지 않았다. 임시 viewport 설정은 초기화하고 테스트용 중복 탭은 닫았다. 반응형 CSS는 있지만 실제 모바일 렌더링 검증과 동일하게 취급하지 않는다.

GitHub 커밋·Push 및 Vercel Preview/Production 배포는 아직 수행하지 않았다. 기존 coffee 복제본과 Chapter14-1은 수정하지 않았다.

## 증거 및 위치

- 로컬: http://127.0.0.1:3000/
- Supabase AI 테이블: https://supabase.com/dashboard/project/eoujbpxqmqtfxjlrybiz/editor/17652?schema=public
- NAVER Maps 콘솔: https://console.ncloud.com/maps/application
- artifacts/evidence/dashboard-map.jpg, dashboard-map-production.jpg, dashboard-ai-production.jpg, supabase-ai-table.jpg, maps-representative.jpg, maps-limits.jpg
- artifacts/lesson-step36/before: 이번 수정 전 소스 백업.
- artifacts/lesson-step36/dashboard-filter-check.txt: 실제 지역·카테고리·검색 결과.

공식 Maps 정책: https://www.ncloud.com/support/faq/all/2828 및 https://www.ncloud.com/support/faq/all/2829
