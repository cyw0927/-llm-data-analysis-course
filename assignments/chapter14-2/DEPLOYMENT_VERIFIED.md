# Chapter 14-2 — GitHub·Vercel 실제 배포 검증

검증일: 2026-10-19 (Asia/Seoul).

## 실행 주소

- 운영: https://tourism-dashboard-cyw0927.vercel.app/
- Preview: https://tourism-dashboard-cyw0927-ret9qrquu-dkrakaksakst-8648.vercel.app/
- GitHub: https://github.com/cyw0927/-llm-data-analysis-course/tree/main/assignments/chapter14-2
- Vercel 프로젝트: https://vercel.com/dkrakaksakst-8648/tourism-dashboard-cyw0927
- GitHub 검사: https://github.com/cyw0927/-llm-data-analysis-course/actions/runs/39217039636 (b8f2b4c, 성공).

## 배포 구성

- GitHub 원본 저장소 cyw0927/-llm-data-analysis-course를 연결했다. coffee 저장소는 변경하지 않았다.
- Vercel Hobby, Next.js, 루트 assignments/chapter14-2/dashboard. 다른 과제를 배포 대상으로 포함하지 않았다.
- Production 추적 브랜치는 main. 비운영 브랜치는 Preview용이다.
- 등록 환경변수는 NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_NAVER_MAP_NCP_KEY_ID 세 개뿐이다. Production과 Preview에 적용했다. Secret/Service Role/API Client Secret은 등록하지 않았다.
- 기존 Supabase 프로젝트를 그대로 조회한다. 새 DB나 중복 통합을 만들지 않았다.
- NAVER Maps는 로컬 URL, 운영 URL, 검증 Preview URL과 그 브랜치 URL만 추가 허용했다. 일·월 1,000회, 초과 사용 불허 설정을 유지한다.

## 실행 검증

- 구현 커밋 b8f2b4cfb857b750df16604f693127d6390b3d96를 GitHub main에 일반 push했다. 이전 원격과 비교 후 적용했으며 강제 push는 사용하지 않았다.
- 비밀키 검사: 업로드 대상 37파일에서 기존 실제 인증정보와 키 패턴 미검출. .env.local과 artifacts는 Git 제외 확인.
- Python 16개, 대시보드 Node 12개, TypeScript 및 Next.js production build 통과. 새 CI 환경에서도 .next/types가 없을 때 성공하도록 typecheck에 next typegen을 추가했다.
- GitHub Actions에서도 Python 테스트와 대시보드 테스트·타입 검사·빌드가 통과했다.
- 운영 HTTP 200. 로그인 없는 요청에서 2026-10-19 AI 분석과 소비강도 97.07을 확인했다. 응답 HTML에 Secret Key 패턴 미검출.
- 운영 및 Preview 모두 서울 체류 89.81 / 소비 97.07, 장소·지도 마커 17개, 전국 검색 13개월·52관측값, 최신 AI 요약 표시를 확인했다.
- 운영 카페 선택 시 마커 5개, 최근 관측 6개월 선택 시 24관측값으로 변화했다. 브라우저 error/warn 로그는 0건이었다.
- 실제 활성 탭에 390×844 viewport를 적용하여 모바일을 검증했다. 스크롤바 제외 DOM 폭 375px와 문서 폭 375px가 일치해 가로 넘침이 없었다. KPI·필터·지도 확인. 모바일에서 경복궁 검색 시 마커 1개 확인.
- 이전 모바일 검증 실패 원인은 viewport 설정이 선택된 다른 탭에 적용된 것이었다. 대시보드 탭을 실제 활성화한 뒤 해결했고, 임시 viewport는 원래대로 복구했다.

## 배포 이력과 절차 차이

최초 배포 생성 화면에서는 Preview로 안내됐으나 Vercel의 최초 배포는 실제로 Production으로 분류되었다. 이 첫 배포(7FnXmXSX76Km6pWDcciKtMnmN1C1, b8f2b4c)는 48초 후 Ready였고 즉시 운영 검증했다. Preview를 먼저 거친 것으로 기록하지 않는다.

이후 소스 트리를 바꾸지 않은 별도 커밋 d05e04db05d5dcf991793c9ee2dcd6d43fe37599를 deploy/ch14-2-preview-20261019에 올려 독립 Preview(Fhvhz7FgqyQsEAYiHn85MUvorVSn)를 만들었다. 해당 Preview의 실제 데이터·지도·AI도 검증한 후 이 보고서를 main에 올린다.

## 보존 및 운영 주의점

Chapter14-1과 기존 다른 과제의 수정/미추적 파일은 보존했고 커밋에 포함하지 않았다. Supabase 기존 데이터는 삭제/초기화하지 않았다. Make 수집 및 AI 시나리오의 자동 스케줄은 여전히 꺼져 있다. 배포는 완료됐지만 예약 수집 활성화는 별도 사용자 승인이 필요하다. 관광 관측월은 2025-09이며 최신 검색과 기간 차이를 화면에 표시한다.

증거는 로컬 artifacts/evidence/vercel-production-map.jpg, vercel-production-mobile.jpg, vercel-preview-map.jpg, vercel-preview-ready.jpg와 dashboard-mobile-390.jpg에 보존한다. 이미지와 개인 실행 자료는 Git에 올리지 않는다.
