# Chapter 14-2 — 관광 데이터 수집·저장 및 지도 기반 AI Dashboard

수업 목표: **외부 API → Make → 검증/Upsert → Supabase → AI 요약 저장 → Next.js 지도 Dashboard → GitHub/Vercel**.

이 폴더는 **안전한 초기 스캐폴딩**이다. 실제 운영 연동 성공·배포 완료를 의미하지 않는다. Chapter 14-1의 로컬 PDF/Gmail 자동화와 별개다.

## 실행 상태
- [x] Supabase 6개 테이블, RLS, View SQL **실행 준비** (라이브 DB에 실행한 것은 아님; `collection_runs`는 공개 읽기 차단)
- [x] Python+pandas Seed 전처리 스크립트 및 오프라인 테스트 기본 구성
- [x] Next.js/TypeScript/Tailwind/Recharts/NAVER Maps + Supabase 읽기 Dashboard 기초
- [x] Make 4개 Scenario 설정 가이드 및 배포 체크리스트
- [ ] Supabase 프로젝트 생성과 SQL Editor에서 실제 마이그레이션 적용
- [ ] 실제 Raw/Seed 수집과 CSV 데이터 검증, Supabase Import
- [ ] NAVER Local Search 및 NAVER Maps 사용 설정
- [ ] Make 4개 Scenario Run once, 인증키 설정 및 매일 1회 예약 활성화
- [ ] 로컬 Dashboard 데이터·지도 표시 실물 확인
- [ ] Vercel Preview / Production 배포 및 운영 URL 검증

## 폴더 개요

```text
assignments/chapter14-2/
├── sql/001_init.sql           # Supabase DDL, RLS, 읽기 정책, 집계 뷰
├── seed/
│   ├── prepare_seed.py         # CSV + 실제 관광 API JSON을 Seed CSV로
│   ├── config.example.json     # 관광공사 실제 필드명 확인 후 매핑
│   ├── raw/.gitkeep            # 직접 획득한 실제 Raw만 놓을 것
│   └── processed/.gitkeep      # 실행하면 CSV 생성
├── dashboard/
│   ├── package.json
│   ├── .env.local.example
│   ├── src/app/page.tsx
│   ├── src/components/
│   └── src/lib/
├── docs/MAKE_SCENARIOS.md
├── docs/VERIFICATION.md
└── tests/test_prepare_seed.py
```

## 1. Supabase부터 (강의 STEP 0~3)

1. https://supabase.com/ 가입 → 새 프로젝트 (예: `tourism-dashboard`), URL/Publishable Key 확인
2. **SQL Editor**에서 `sql/001_init.sql` 전체 실행 후 Table Editor에서 6개 테이블 확인
3. RLS 및 공개 읽기 정책 검토. Dashboard에는 **Publishable Key**, Make HTTP에는 **Secret Key**만 사용
4. Secret Key는 GitHub, 브라우저, `NEXT_PUBLIC_*`에 넣지 말 것

## 2. Seed 전처리 (STEP 4~9)

```powershell
cd C:\dev\llm-data-analysis-course\assignments\chapter14-2
python -m pip install pandas
python seed\prepare_seed.py --help
python -m unittest discover -s tests -v
```

입력 방식 A: `seed/raw/tourism_seed.csv`에 `reference_date,region_code,stay_strength,consumption_strength` 컬럼을 채운 **실제 데이터**를 놓고 실행.

입력 방식 B: 이미 받아둔 Chapter 14-1 `tourism_stay_*.json`와 `tourism_consumption_*.json`을 `seed/raw/`에 **복사**하고 `seed/config.example.json`의 실제 필드 매핑을 검증 후 실행. `baseYm=202509`는 **2025-09-01** (기준월의 첫째 날)로 변환한다. 서울 전체 행과 시군구 행은 서로 다른 region_code로 구분한다. 필드명이나 매칭이 확인되지 않으면 중단한다.

검증된 실수집 `naver_trend.csv`가 있다면 `seed/raw/naver_trend.csv`로 복사할 수 있다. 없는 입력은 SKIP으로 남긴다. `seed/processed/*.csv` 생성 후 눈으로 검사하고 Supabase Table Editor에서 해당 테이블로 Import.

> Chapter 14-1 원본 파일을 이 폴더로 옮기거나 덮어쓰지 말 것. 가져와야 하면 **복사만** 수행.

## 3. Make 수집/AI 자동화

`docs/MAKE_SCENARIOS.md`의 4개 독립 Scenario를 참조. **매일 예약은 Run once 검증 완료 후**에만 설정한다. Make Code에서 pandas가 제공되지 않을 수 있으므로 순수 Python·기본 모듈·Supabase SQL을 우선 검토한다.

## 4. Next.js Dashboard (STEP 29~40)

Node.js/npm이 설치된 Windows PowerShell에서:

```powershell
cd C:\dev\llm-data-analysis-course\assignments\chapter14-2\dashboard
npm install
Copy-Item .env.local.example .env.local
# .env.local 편집: Supabase URL, Publishable Key, NAVER Maps 키 ID
npm run dev
```

http://localhost:3000 접속. **설정 누락 시 안내 화면**이 뜨도록 설계되어 있다. 데이터가 없으면 빈 상태가 보이며 가짜 데이터를 만들지 않는다. Dashboard는 **외부 NAVER/관광 API를 직접 호출하지 않고 Supabase만 읽는다** (지도 JS 로딩은 NAVER Maps SDK).

## 5. 배포 (STEP 41~50)

`docs/VERIFICATION.md`의 Gate를 확인한 뒤 Vercel에서 GitHub 저장소 Import 시 **Root Directory를 `assignments/chapter14-2/dashboard`로 설정**. 브라우저용 env 세 개만 Vercel 환경변수에 입력. Supabase Secret Key는 Vercel Dashboard 환경변수로도 전달하지 않는다.

**Git 루트는 이미 `C:\dev\llm-data-analysis-course`이므로 여기서 별도 `git init` 하지 말 것.**

## 의미 구분
NAVER Trend ratio는 **전국 검색의 상대 관심도**, 관광공사 체류/소비 강도는 **지역별 API 고유 지표**다. 둘을 동일 지표로 병합하거나 인과관계로 단정하지 않는다. NAVER Local의 `mapx`는 경도, `mapy`는 위도다.

공식 참고: [NAVER Trend](https://api.ncloud-docs.com/docs/naver-api-hub-search-trend) · [지역별 관광 수요 강도](https://www.data.go.kr/data/15151868/openapi.do) · [NAVER Local](https://api.ncloud-docs.com/docs/naver-api-hub-search-local) · [NAVER Maps JS](https://navermaps.github.io/maps.js.ncp/docs/)
