> **소비 지표 정정(2026-10-19):** 이전 2201/119.08은 외지인 소비액이며 강의의 소비강도22/97.07과 다릅니다. 기존 값은 보존했고 Make와 DB 호환을 정정했습니다. [STEP13~16 검증 기록](LESSON_STEP16_VERIFIED.md)을 우선 보세요.

# 강의 STEP 5~8: Seed CSV 및 기존 적재 확인

검증일: 2026-10-19. **강의자료에 쓰인 STEP 번호** 기준이다. 이전 `STEP4_VERIFIED.md`의 1~4는 별도 작업 묶음 번호이며 강의 STEP 1~4와 다르다.

| 강의 단계 | 결과 |
|---|---|
| STEP 5 원본 준비 | 기존 실제 API 원본 `tourism_stay_20261016_012711.json`, `tourism_consumption_20261016_012711.json` 재사용. 원본 해시 불변 확인 |
| STEP 6 pandas 전처리 | 기존 `seed/prepare_seed.py`로 관광 CSV 26행 재생성. 기존 출력은 먼저 백업 |
| STEP 7 파일 확인 | 기준일 2025-09-01, 지역코드 공백 0, 네 컬럼 결측 0, 날짜·지역 중복 0, 체류·소비 모두 정상 숫자 |
| STEP 8 Supabase 적재 확인 | 기존 `tourism_demand` 26행과 CSV의 26개 날짜·지역 키 및 양쪽 수치가 모두 일치. Table Editor에서 직접 확인. 누락 0, 충돌 0이므로 **재Import는 수행하지 않음** |

CSV: `seed/processed/tourism_demand_seed.csv`

```text
reference_date,region_code,stay_strength,consumption_strength
2025-09-01,11,89.81,119.08
2025-09-01,11110,84.26,108.49
2025-09-01,11140,81.33,199.21
```

CSV는 첫 데이터 준비(Seed)를 위한 파일이다. 운영 수집은 Make가 담당한다. 같은 CSV를 다시 INSERT하면 기존 고유키와 충돌하거나, 부주의한 교체로 원본 추적 `raw_id`를 잃을 수 있어 기존 적재 결과를 대조하는 방식으로 확인했다. 이번 확인에서 DB 변경은 **0건**이며 기존 `raw_id=2`와 모든 ID·수집 시각을 유지했다.

대조 대상은 관광 체류·소비 CSV 26행이다. 보조 NAVER CSV 52행도 재생성됐지만 이번 단계에서 새로 Import하지 않았다. 실제 지도·AI·배포까지 완료했다는 의미는 아니다.

실행 기록과 전처리 전 백업:

- `artifacts/lesson-step8-20261019-111424/seed-import-verification.json`
- `artifacts/lesson-step8-20261019-111424/processed-before/`
- `artifacts/lesson-step8-20261019-111424/supabase-tourism-before.json`
- `artifacts/evidence/lesson-step8-tourism-table.jpg`

CSV SHA256: `63b76c96ad483c0688d0467a6143bd02233b6ef1b4abed8d2c5581fbaf83aad8`

[Supabase Table Editor 관광 테이블](https://supabase.com/dashboard/project/eoujbpxqmqtfxjlrybiz/editor/17629?schema=public)

이번 작업은 강의 STEP 8 확인에서 멈춘다. Make 일정은 그대로 Inactive다. 추가 로그인이나 승인은 필요하지 않았다.
