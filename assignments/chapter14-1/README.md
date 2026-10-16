# Chapter 14-1 — 데이터 분석 자동화 입문

첨부된 수업 자료 Chapter 14-1을 기준으로 한 **실습용 구현**. 로컬 Python 자동화(PART 1)와 Make 온라인 자동화(PART 2)는 **서로 연결하지 않는 독립 과제**다.

## 현재 상태

- **2026-10-16 실제 검증:** NAVER 52행, 관광 체류/소비 각각 26행, 분석 요약 30행, Gemini 요약 및 한글 PDF 생성 PASS. 최종 코드 직접 실행·배치 재실행·작업 스케줄러 수동 실행 모두 성공. 단위테스트 16개 통과. 상세 근거는 EVIDENCE.md 참조.
- Make에 독립 Scenario `Tourism Trend Weekly Report`를 생성했고 NAVER·관광 체류·소비·LLM의 실제 Run once를 검증했다. Gmail 연결/발송과 예약 실행은 별도 확인이 필요하며 아직 완료로 표시하지 않는다. PART 1의 파일을 읽거나 업로드하지 않는다.
- 수업의 관광공사 API: https://www.data.go.kr/data/15151868/openapi.do
- 수업의 NAVER 공식 문서: https://api.ncloud-docs.com/docs/naver-api-hub-search-trend
- 이 폴더는 GitHub의 기존 Chapter 13 과제나 기존 YES24 도서 실습과 별개다.

## PART 1 로컬 자동화 (Windows PowerShell)

프로젝트 루트: C:\dev\llm-data-analysis-course

```powershell
cd C:\dev\llm-data-analysis-course
git status --short --branch
# 기존 변경사항이 있으면 먼저 보존하고 원격 변경을 확인한다.
git fetch origin main
cd assignments\chapter14-1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

PowerShell 실행 정책 오류가 난다면 **해당 터미널에서만** Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 를 실행한 뒤 다시 활성화한다.

### 실제로 설정할 정보

1. NAVER Cloud Platform → NAVER API HUB → Search Trend: Client ID / Client Secret을 발급받아 .env의 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET에 입력.
2. 공공데이터포털에서 **한국관광공사_지역별 관광 수요 강도** 활용신청. 체류·소비 API를 **Swagger에서 직접 각각 실행**하여 서비스 키, 정확한 Endpoint URL과 필수 파라미터를 확인한다.
3. .env의 TOURISM_SERVICE_KEY, TOURISM_STAY_URL, TOURISM_CONSUMPTION_URL을 채운다. config/tourism_params.json 안의 stay/consumption.params를 Swagger에서 확인한 필수 파라미터로 갱신한다.
4. 첫 수집에 성공한 뒤 data/raw/tourism_stay_*.json, tourism_consumption_*.json의 **실제 필드명**을 눈으로 확인하고 config/tourism_params.json의 fields.region/period/value를 각각 입력한다. 필드명을 추측해 넣지 않는다.
5. 본인이 선택한 LLM(Gemini 기본 구현)의 LLM_API_KEY / LLM_MODEL을 .env에 입력한다. 다른 제공자를 사용하려면 src/generate_llm_report.py의 호출 함수를 교체한다.
6. .env 파일은 .gitignore 대상이다. API Key를 노트북 출력·GitHub·스크린샷에 노출하지 않는다.

### 수동 테스트: 한 단계씩 PASS 확인

```powershell
python src\collect_naver.py
python src\collect_tourism.py
python src\analyze.py
python src\generate_llm_report.py
python src\generate_pdf.py
```

검증:
- NAVER: HTTP 200 **뿐만 아니라** 4개 키워드와 유효한 period/ratio, data/processed/naver_trend.csv 확인. ratio는 실제 검색 건수가 아닌 **기간 내 상대지수**다.
- 관광공사: 체류·소비 각각 Raw JSON을 열어 실제 지역/기간/지표가 있는지 확인. 샘플·오류메시지는 데이터가 아니다.
- 분석: NAVER 월별 그래프, 관광 체류/소비 상위 지역 그래프, reports/analysis_summary.csv 각각 검증. **서로 다른 두 API 행을 임의로 merge하지 않음**.
- LLM: reports/llm_summary.md 숫자를 Python 계산값과 직접 비교, 인과관계 단정·환각이 없는지 검토.
- PDF: reports/tourism_trend_report_YYYY-MM-DD.pdf를 열어 한글·날짜·본문·그림을 직접 검사한다.

### 파이프라인 재실행 → 그다음 스케줄러

```powershell
python run_pipeline.py
.\run_pipeline.bat
Get-Content logs\pipeline_*.log
python -m unittest discover -s tests -v
```

모든 단계 PASS → PDF 실물 검증 → 같은 명령 두 번째 실행하여 중복·오염 없음을 확인 → 그 후 Windows 작업 스케줄러에 run_pipeline.bat 등록.

작업 스케줄러: 프로그램 C:\Windows\System32\cmd.exe, 인수 /c "C:\dev\llm-data-analysis-course\assignments\chapter14-1\run_pipeline.bat", 시작 위치 C:\dev\llm-data-analysis-course\assignments\chapter14-1. 예시 주기는 매주 월요일 오전 9시. 등록명 `Chapter14-1-TourismTrend`, 매주 월요일 09:00 (2026-10-15 기존 등록, 2026-10-16 10:27 수동 실행 검증, LastResult=0; 기존 활성 상태 유지, 다음 예약 2026-10-19 09:00 KST). `.venv`는 `python -m venv .venv --system-site-packages`로 생성(기업 보안 정책이 새 venv의 numpy DLL을 차단하는 환경 대응).

## PART 2 Make (별도 온라인 실습)

MAKE_GUIDE.md 참조. Make Scheduler → NAVER HTTP → 관광 HTTP → LLM → Gmail. 로컬 PDF/코드/reports를 Make와 연결하거나 업로드하지 않는다.

## 결과 폴더

```text
assignments/chapter14-1/
  .env.example, .gitignore, requirements.txt
  config/tourism_params.json
  src/collect_naver.py, collect_tourism.py, analyze.py
  src/generate_llm_report.py, generate_pdf.py
  run_pipeline.py, run_pipeline.bat
  data/raw/                  (실행 시 자동 생성·gitignore)
  data/processed/            (실행 시 자동 생성·gitignore)
  reports/                   (실행 시 자동 생성·gitignore)
  logs/                      (실행 시 자동 생성·gitignore)
  MAKE_GUIDE.md, EVIDENCE.md, tests/
```

## 중요 해석 원칙

**API 성공 ≠ 분석 성공. 자동 실행 성공 ≠ 검증 완료. 동시 변화 ≠ 인과관계. LLM 요약 ≠ 확인된 사실.**

## 제출

EVIDENCE.md의 로컬·Make 증빙을 채워 제출한다. 인증정보/이메일 개인정보는 화면 캡처에서 가린다.
