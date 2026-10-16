# PART 2 — Make 온라인 자동화 구축 가이드

**이 과제는 PART 1의 로컬 Python, PDF, reports 폴더를 전혀 사용하지 않는다.** Make 클라우드 내부에서 API 데이터를 직접 조회하고 요약해 Gmail로 발송한다.

## 2026-10-16 계정 내 실제 확인 결과

[Tourism Trend Weekly Report](https://eu1.make.com/3207920/scenarios/7989174/edit)을 새로 생성했다.
NAVER → 관광 체류 → 관광 소비 → HTTP Gemini 호출까지 실제 Run once가 성공했다.
NAVER 52행, 관광 각각 resultCode=0000/26행, LLM HTTP 200과 생성문 수치를 직접 확인했다.
LLM 앞에는 관광 두 응답의 resultCode가 모두 0000인지 확인하는 필터를 뒀다.
최초 요약에서 체류와 소비 지표를 비교하는 표현을 발견해 지침을 보강하고 재실행한 문장을 다시 검토했다.
Make는 **On demand·Inactive**다. Gmail Send an email 모듈을 추가하고 Google 연결 화면까지 준비했으며,
권한 연결·수신인·실제 발송과 예약 활성화는 사용자 확인 전에는 실행하지 않는다.
Gmail을 추가하기 전 성공한 API/LLM 실행과, Gmail까지 포함된 전체 성공을 구분한다.

로컬 `.env` 키를 이 Scenario에 저장하고 Run once하는 것은 사용자가 명시적으로 승인했다.
인증정보가 들어간 개인 설정은 `.make-private/`에 두어 Git에서 제외한다. 이 폴더를 공유하거나 커밋하지 않는다.
로컬 PDF·분석 CSV·Raw 데이터를 Make에 올리지 않는다.

## 필수 준비

- https://www.make.com/ 계정
- NAVER Cloud Search Trend Client ID / Client Secret (발급 및 활성화)
- 공공데이터포털 관광 체류/소비 강도 API Service Key, Swagger에서 확인한 실제 endpoint/필수 파라미터
- Gemini/OpenAI/Claude 중 한 서비스의 API 키/Make 연결
- 본인의 Google/Gmail 계정 OAuth 연결

## Scenario 구조

```text
Make Scheduler (On demand로 시작)
  → HTTP / Make a request : POST NAVER Search Trend
  → HTTP / Make a request : GET 관광 수요 API
  → LLM : 검증된 핵심 숫자만 간단히 요약
  → Gmail / Send an email : 본인 메일로 송신
```

## STEP 25~26 — Scenario 만들기

Make에서 이름 Tourism Trend Weekly Report로 새 Scenario 생성. Schedule은 **처음엔 On demand**, 매번 Run once로 검증한다.

## STEP 27 — NAVER HTTP

- Method: POST
- URL: https://naverapihub.apigw.ntruss.com/search-trend/v1/search
- Headers: X-NCP-APIGW-API-KEY-ID, X-NCP-APIGW-API-KEY, Content-Type=application/json
- Body는 월 단위 timeUnit=month, groupName 여행·축제·캠핑·맛집 네 그룹. startDate/endDate는 실행 시점을 기준으로 조정.

```json
{
  "startDate": "2026-01-01",
  "endDate": "2026-10-15",
  "timeUnit": "month",
  "keywordGroups": [
    {"groupName":"여행","keywords":["여행"]},
    {"groupName":"축제","keywords":["축제"]},
    {"groupName":"캠핑","keywords":["캠핑"]},
    {"groupName":"맛집","keywords":["맛집"]}
  ]
}
```

실행 날짜는 필요에 맞게 변경. Run once 후 **HTTP 200, results → title/data → period/ratio 실제 값**을 확인한다. ratio는 실제 검색 건수가 아니다.

## STEP 28 — 관광공사 HTTP (실제 호출로 검증된 값)

HTTP 모듈을 **두 개**로 나눠 각각 GET으로 호출한다. serviceKey는 Make 연결/변수에 보관하고 문서·스크린샷에 노출하지 않는다.

공통 Query: `numOfRows=100`, `pageNo=1`, `MobileOS=ETC`, `MobileApp=AppTest`, `baseYm=202509`, `areaCd=11`, `_type=json`, `serviceKey=<본인 키>`

| 구분 | URL | 추가 Query | 값 필드 |
|---|---|---|---|
| 체류 강도 | `https://apis.data.go.kr/B551011/AreaTarDemDsService/areaTarSjrnDsList` | `tarSjrnDsIxCd=21` | `tarSjrnDsIxVal` |
| 소비 강도 | `https://apis.data.go.kr/B551011/AreaTarDemDsService/areaTarExpDsList` | `tarExpDsIxCd=2201` | `tarExpDsIxVal` |

- 응답 구조: `response.header.resultCode == "0000"`(성공), 데이터는 `response.body.items.item[]`, 서울 기준 26건(`totalCount` 확인).
- 행 필드: `baseYm`, `areaCd`, `areaNm`, `signguCd`, `signguNm`, 값 필드. `signguNm="_"`(`signguCd="0"`)는 시도 전체 집계 행이므로 시군구와 구분한다.
- Run once 후 `resultCode`가 `0000`인지, 지역·기준월·강도 값이 실제로 들어 있는지 확인한다. (로컬 Python 수집에서 위 설정으로 26건/26건 수집 확인됨)
- 값이 100건을 넘는 지역을 조회한다면 `totalCount`만큼 pageNo를 늘려 반복 조회해야 한다.

## STEP 29~30 — 단순 가공 + LLM

NAVER 최신 상대 관심도와 관광 대표 지표 몇 건만 넘긴다. Make에서 복잡한 pandas 수준의 통계 분석이나 무리한 공통키 merge를 재현하지 않는다.

LLM 프롬프트 예:

> 제공하는 NAVER ratio는 상대지수이며 실제 검색 건수가 아닙니다. 관광 수요 강도는 API가 정의한 지역별 지표입니다. 제공한 수치만으로 1) 기준일 2) 검색 관심도 3) 지역 관광 수요 4) 관찰되는 패턴 5) 인과관계로 단정할 수 없는 점 6) 다음 확인사항을 짧게 작성하세요. 없는 숫자·사실은 생성하지 마세요. 체류 강도와 소비 강도도 서로 다른 지표이므로 크기를 직접 비교하지 말고 각각 별개로 서술하세요.

Run once 후 **LLM 문장의 수치·기간·지역이 입력 Bundle과 일치하는지** 확인한다.

## STEP 31~32 — Gmail

Google 계정 연결 방식으로 Gmail 앱 Send an email 선택. 수신인: 본인 이메일. 제목 예: [자동보고서] 주간 관광 트렌드 분석. 본문: LLM 출력, 기준일 및 상대지수 경고.

**테스트 발송은 사용자가 본인 계정에서 승인 후 실행**. 실제 받은 편지함에서 제목·본문·기준일 확인. API Key를 이메일에 포함시키지 않는다.

## STEP 33~35 — 예약 실행

Scheduler/NAVER HTTP/관광 HTTP/LLM/Gmail 모든 모듈 Run once 검증 후에만 Weekly Monday 09:00, Timezone Asia/Seoul로 활성화. 최초 예약 실행의 Make History와 실제 이메일 수신 모두 확인한다.

## STEP 36 — 오류 분류

일시 네트워크/API 서버/LLM 장애: 제한적 재시도. API 키 오류, URL 오류, 필수 파라미터 누락, JSON 필드 변화, 빈 데이터, Gmail 권한 오류: **설정 수정 후 재실행**. 자동 반복으로 해결하려 하지 않는다.

## STEP 37 — 스크린샷 제출

Scenario 전체 화면, NAVER HTTP 응답, 관광 HTTP 응답, LLM 출력, Gmail 수신, Schedule 활성화/History. 비밀키·사용자 이메일은 필요한 부분만 마스킹한다.

**주의**: 위의 실제 검증 결과와 설정 가이드를 구분한다. Scenario의 API/LLM 호출은 확인했으나 Gmail 발송·수신 및 예약 실행은 아직 검증되지 않았다.
