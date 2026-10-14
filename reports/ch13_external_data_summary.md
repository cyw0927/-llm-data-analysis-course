# Chapter 13 외부 데이터 수집 준비 요약

## 1. 분석 질문과 외부 데이터 계획
```text
              analysis_question       external_data_needed           provider                                 source_type                                                     official_url reference_date               collection_range  join_key license_or_terms  collection_enabled interpretation_caution
 특정 월 완료 주문 금액 변동과 함께 볼 외부 요인은? 공휴일·날씨·행사 중 질문에 필요한 최소 데이터                    official_file / official_api / limited_html                                                                                                                  날짜 또는 월                                False       동시 변화는 원인 증명이 아님
특정 지역 완료 주문 금액 차이와 함께 볼 지역 지표는?       인구·관광·지역 통계 중 필요한 지표                                   official_file / official_api                                                                                                                  행정구역 코드                                False     지역 단위·기준일·표본 차이 확인
   특정 검색어 결과가 시간에 따라 어떻게 달라지는가?          공식 검색 API의 제한된 결과 Naver Search API 등                                official_api https://developers.naver.com/docs/serviceapi/search/blog/blog.md                query / page / collection time 검색어·수집 시각     현재 공식 정책 재확인               False    검색 결과는 전체 시장·여론이 아님
```

## 2. 수집 방법 우선순위
```text
     method  priority                 strength                             required_checks
      공식 파일         1             원본 보존·재현이 쉬움                      제공기관·기준일·인코딩·라이선스·hash
     공식 API         2              최신성·자동화에 유리 공식 문서·method·인증·rate limit·pagination·오류 구조
제한적 공개 HTML         3 API가 없는 공개 페이지의 최소 정보 확인                이용약관·robots.txt·저작권·개인정보·요청량
```

## 3. 내부 데이터 연결 기준
```text
connection_key            normalization               validation
          날짜/월        날짜형·시간대·일/월 단위 통일       기간 겹침·키 중복·월 누락 확인
            지역        공식 행정구역 코드와 명칭 매핑          미매칭 지역·경계 변경 확인
       상품 카테고리          내부·외부 분류 체계 매핑표 오른쪽 키 고유성·many_to_one 확인
           키워드 검색어 정의·정렬·page·수집 UTC 기록      대표성·페이지 범위·검색 정책 확인
            위치       좌표계·위도/경도·거리 단위 확인           좌표 오류·누락·범위 확인
```

## 4. 네트워크 실행 기본 상태
```text
                flag  default       status
      RUN_PUBLIC_API    False SAFE_DEFAULT
       RUN_NAVER_API    False SAFE_DEFAULT
RUN_CRAWLING_EXAMPLE    False SAFE_DEFAULT
    POLICY_CONFIRMED    False SAFE_DEFAULT
```

## 5. 수집 전 체크리스트
```text
                                               check_item status memo
                                  분석 질문에 필요한 최소 외부 데이터인가? REVIEW     
                                    공식 다운로드 파일을 먼저 확인했는가? REVIEW     
                                  공식 API를 크롤링보다 우선 확인했는가? REVIEW     
                              제공기관·공식 URL·데이터 기준일을 기록했는가? REVIEW     
                        라이선스·이용약관·출처표시 조건을 현재 문서에서 확인했는가? REVIEW     
                            데이터 기준일과 실제 UTC 수집 시각을 구분했는가? REVIEW     
                  API Key를 .env 또는 승인된 Secret 저장소에 보관했는가? REVIEW     
                     Key·Secret·인증 헤더가 화면·로그·Git에 남지 않는가? REVIEW     
       요청 URL·HTTP method·parameter·인증 위치를 공식 문서에서 확인했는가? REVIEW     
                        연결·읽기 timeout과 HTTP 오류 처리를 포함했는가? REVIEW     
                        재시도 대상이 429·일시적 5xx 등으로 제한되어 있는가? REVIEW     
                retry 설정과 rate limit 관리를 같은 것으로 혼동하지 않는가? REVIEW     
                     Retry-After와 서비스별 rate limit을 확인했는가? REVIEW     
                     pagination 범위와 종료 조건을 공식 문서에서 확인했는가? REVIEW     
               페이지를 읽는 동안 원본이 바뀌어도 같은 snapshot으로 보이지 않는가? REVIEW     
         JSON 응답 크기를 Content-Length와 실제 수신 바이트 모두로 제한했는가? REVIEW     
               HTTP 200과 JSON 파싱 성공, API 업무 성공을 각각 구분했는가? REVIEW     
URL validator가 완전한 SSRF 차단이 아니라 defence-in-depth임을 이해하는가? REVIEW     
                 raw·processed·metadata를 서로 다른 경로에 저장하는가? REVIEW     
                              raw snapshot을 조용히 덮어쓰지 않는가? REVIEW     
                raw snapshot의 보유기간·접근범위·재배포 가능 여부를 검토했는가? REVIEW     
                 SHA-256은 무결성 확인이며 데이터 타당성 보증이 아님을 이해하는가? REVIEW     
                            행·열·dtype·결측·중복·파싱 실패를 확인했는가? REVIEW     
                           내부 데이터와 연결할 키·시간대·분석 단위가 명확한가? REVIEW     
                           외부 오른쪽 키 중복과 병합 전후 행 수를 확인했는가? REVIEW     
                        크롤링 전 robots.txt와 이용약관을 각각 확인했는가? REVIEW     
                   robots.txt 허용을 접근 권한·저작권 허가로 오해하지 않는가? REVIEW     
                     로그인·CAPTCHA·paywall·접근 제한을 우회하지 않는가? REVIEW     
                        개인정보·민감정보·저작물 원문을 불필요하게 저장하지 않는가? REVIEW     
                             검색 결과를 전체 시장·여론으로 일반화하지 않는가? REVIEW     
                            외부 변수의 동시 변화를 인과관계로 단정하지 않는가? REVIEW     
           수집한 외부 HTML·검색 텍스트를 LLM context에 그대로 신뢰하지 않는가? REVIEW     
           외부 문서 안의 문장이 지시문처럼 실행되지 않도록 최소 권한·사람 승인을 거치는가? REVIEW     
                  LLM이 만든 API 코드를 현재 공식 문서와 사람이 다시 비교했는가? REVIEW     
```

## 핵심 원칙
- 공식 파일 → 공식 API → 제한적 공개 HTML 순으로 검토합니다.
- 네트워크 실행은 기본 비활성화이며 현재 공식 문서·정책 확인 후에만 명시적으로 활성화합니다.
- API Key·Secret은 화면·로그·Git에 남기지 않습니다.
- raw snapshot은 덮어쓰지 않고 processed와 metadata를 분리합니다.
- 데이터 기준일과 UTC 수집 시각을 구분하고 SHA-256을 기록합니다.
- 외부 오른쪽 키 고유성, 병합 전후 행 수, left_only를 확인합니다.
- 검색 결과·상관관계를 전체 시장·여론·인과관계로 과장하지 않습니다.
