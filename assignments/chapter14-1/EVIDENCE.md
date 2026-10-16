# Chapter 14-1 실제 검증 기록

검증일: 2026-10-16 (Asia/Seoul). 저장소: `C:\dev\llm-data-analysis-course`, 과제: `assignments/chapter14-1`.
강의자료: 첨부 `붙여넣은 텍스트(1)(3).txt`의 PART 1/2 요구를 대조했다.

## 기존 작업 보존

- 조사 시작 시 로컬 main과 GitHub main 모두 `8332d2a8174e0463922728698cad8d22431ae367`.
- `7fa8abf`의 관광 정상코드 `0000` 허용 수정이 포함되어 있으며 실제 호출에서도 확인했다.
- Chapter 13 이미지 4개 수정 및 YES24 관련 미추적 파일은 사용자 작업으로 남겨 두었다.
- `.env`의 키 값은 출력·수정·커밋하지 않았다. 기존 reports/processed/logs는 Git 제외된 `data/verification_backups/`에 보존했다.
- 별도 참조 경로 `C:\dev\llm-data-analysis-ebook\chapter14-1`는 이번 조사 시 존재하지 않았다.

## PART 1 — Windows 로컬 자동화

| 항목 | 결과와 근거 |
|---|---|
| NAVER 실제 수집 | PASS. 4개 키워드 × 13개월 = 52행, period 2025-10-01~2026-10-01, ratio 0~100, 결측/기간-키워드 중복 없음 |
| 관광 실제 수집 | PASS. 체류·소비 각각 resultCode=0000, totalCount=26, 실제 26행 |
| 관광 범위 | 202509, areaCd=11(서울), 25개 자치구 + 시도 전체 집계 1개. 전체 행을 자치구 순위에서 제외 |
| 관광 필드 | region=signguNm, period=baseYm, stay=tarSjrnDsIxVal, consumption=tarExpDsIxVal, area=areaNm |
| 분석 | PASS. analysis_summary.csv 30행. Raw JSON과 NAVER CSV를 독립 재계산해 최신 값·전월 차이·상위10·시도 전체 수치를 대조 |
| 분리 분석 | PASS. NAVER 전국 검색 ratio와 관광 서울 강도 데이터를 행 단위로 merge하지 않음 |
| 그래프 | PASS. Malgun Gothic, 월별 NAVER 및 서울 체류·소비 그래프의 한글·제목·수치·기간 확인 |
| LLM | PASS. 기존 설정 Gemini 사용. 수치·기간·지역을 대조하고 입력 자료가 뒷받침하지 않는 키워드 성격 분류는 검토 과정에서 제거 |
| PDF | PASS. tourism_trend_report_2026-10-16.pdf. 검토한 최종 3페이지 전체를 이미지로 렌더링하여 한글·본문·3개 그래프·잘림 여부 확인 |
| Python 직접 실행 | 10:25:02~10:25:35 PIPELINE SUCCESS (초기 확인 실행도 10:24:01 성공) |
| 배치 재실행 | 10:26:20~10:26:45 PIPELINE SUCCESS, 종료코드 0 |
| 재실행 일관성 | NAVER 52행·관광 각26행·요약30행 유지, 중복 없음. 직접/배치/스케줄러 실행 요약 CSV SHA256 동일 |
| 스케줄러 수동 실행 | Chapter14-1-TourismTrend, 10:27:08 시작~10:27:37 PIPELINE SUCCESS, LastTaskResult=0 |
| 기존 예약 상태 | 조사 전부터 Enabled=True. 주 월요일 09:00, 다음 2026-10-19 09:00 KST. 예약 주기와 활성 상태 변경 없음 |
| 실제 예약 실행 | 미확인. 수동 실행과 구분하며 첫 실제 예약 후 로그/PDF 생성 시각을 확인해야 함 |
| 단위테스트 | `python -m unittest discover -s tests -v`: 16개 PASS. 과제 폴더에서 실행 |

요약 CSV SHA256: `513b7906aff78bbaa3139f6bb4d6500239cc5323295640506d69f998b6280417`.
실제 실행 근거: `logs/pipeline_20261016.log` (Git 제외). Raw 스냅샷은 타임스탬프별 보존, 처리 CSV는 교체 생성한다.

관광 요청은 두 endpoint 모두 `https://apis.data.go.kr/B551011/AreaTarDemDsService/`를 사용한다.
체류는 `areaTarSjrnDsList`, `tarSjrnDsIxCd=21`; 소비는 `areaTarExpDsList`, `tarExpDsIxCd=2201`.
공통 `baseYm=202509`, `areaCd=11`, `numOfRows=100`, `pageNo=1`, `MobileOS=ETC`, `MobileApp=AppTest`, `_type=json`.
서비스 키는 `.env`에서 읽으며 URL 쿼리/네트워크 예외에서 인증값을 출력하지 않도록 수정했다.

## PART 2 — Make 독립 온라인 자동화

Scenario: [Tourism Trend Weekly Report](https://eu1.make.com/3207920/scenarios/7989174/edit).
조사 시 기존 Scenario 0개, 연결 목록에는 기본 Make AI Provider만 존재. 사용자 직접 로그인 후 구성했다.
사용자는 이 Scenario에 기존 NAVER·관광·Gemini 키 저장 및 Run once를 명시적으로 승인했다.

| 항목 | 결과 |
|---|---|
| 독립 구성 | Make 클라우드가 NAVER → 관광 체류 → 관광 소비 → Gemini를 직접 호출. 로컬 Python·PDF·reports·분석 CSV를 사용하지 않음 |
| NAVER Run once | PASS, HTTP 200, 4개 키워드 × 13행 = 52행. 최신 2026-10-01, 여행 2.19967 / 축제 28.31086 / 캠핑 2.56608 / 맛집 37.99787 |
| 관광 체류 Run once | PASS, HTTP 200, resultCode=0000, 26행, baseYm=202509, 서울 전체 89.81 |
| 관광 소비 Run once | PASS, HTTP 200, resultCode=0000, 26행, baseYm=202509, 서울 전체 119.08 |
| LLM Run once | PASS, HTTP 200, 위 최신 NAVER 값과 관광 전체 대표값을 전달. 두 관광 API의 resultCode=0000 조건 필터 적용 |
| LLM 검토 | 최초 초안의 체류/소비 숫자 직접 비교 표현 발견, 각각 다른 지표로 별개 서술하도록 지침 보강. 10:47~10:48 재실행 HTTP 200, 모든 입력 수치·기준 기간·직접 비교 금지 문구 확인 PASS |
| Gmail | Send an email 모듈 추가, Google 연결 창까지 준비. 연결·발송·수신은 미완료이며 사용자 직접 OAuth 연결 및 발송 동의 필요 |
| 예약 활성화/예약 수신 | On demand, Inactive로 저장. 수행하지 않음. 사용자 동의 및 Gmail 검증 후 진행 |

## 해석과 한계

- NAVER ratio는 실제 검색 건수가 아니다. 최신 2026년 10월은 부분 월이므로 완전한 9월과의 차이를 수요 급감으로 단정할 수 없다.
- 관광은 2025년 9월 서울 조회 범위의 강도이며, 검색 데이터와 관측 시점·지역·단위가 다르다. 전국 순위 또는 인과관계로 일반화하지 않는다.
- 관광 체류와 소비 지표도 각각 별개로 서술하며 숫자 크기로 우열을 정하지 않는다.
- 로컬 재실행은 성공해도 LLM 문장의 의미 검토는 매번 별도로 필요하다. 검토한 PDF는 이후 자동 재실행 시 새 AI 초안으로 갱신될 수 있다.
- API 키·개인 이메일·인증 설정 파일·원본 응답·생성 PDF는 커밋하지 않는다.
