# Chapter 8 중간 프로젝트 보고서

## 1. 분석 목적

온라인 쇼핑몰 데이터를 사용해 completed 주문 기준 금액과 고객 구매 패턴을 분석했습니다.

## 2. 분석 기준

- 금액성 분석은 `order_status == "completed"`인 주문만 포함했습니다.
- `line_total = quantity × unit_price` 관계를 검증했습니다.
- 취소·환불 등 non-completed 주문을 포함한 금액은 전체 주문 상세 금액으로 구분했습니다.
- 공개 고객 결과에서는 이름·연락처·원본 고객 ID를 제외하고 순위 기반 익명 라벨을 사용했습니다.
- 병합은 관계 검증, `validate`, 행 수, 미매칭을 확인했습니다.
- 같은 completed 범위의 카테고리·월·고객 총합을 source total과 대조했습니다.

## 3. 데이터 개요

```text
    dataset  rows  columns  missing_values  duplicated_rows
  customers   150        6               0                0
   products   100        4               0                0
     orders   300        5               0                0
order_items   764        5               0                0
```

## 4. 전처리 전후 비교

```text
    dataset  rows_raw  columns_raw  rows_processed  columns_processed
  customers       150            6             150                  6
order_items       764            5             764                  6
     orders       300            5             300                  7
   products       100            4             100                  4
```

## 5. 키와 관계 점검

### PK

```text
    dataset           key  missing_count  duplicate_count status detail
  customers   customer_id              0                0   PASS       
   products    product_id              0                0   PASS       
     orders      order_id              0                0   PASS       
order_items order_item_id              0                0   PASS       
```

### FK

```text
                                               check  invalid_count status
  orders.customer_id exists in customers.customer_id              0   PASS
      order_items.order_id exists in orders.order_id              0   PASS
order_items.product_id exists in products.product_id              0   PASS
```

### 병합

```text
                  merge    validate  before_rows  after_rows  row_count_preserved  unmatched_count status
      order_id → orders many_to_one          764         764                 True                0   PASS
  product_id → products many_to_one          474         474                 True                0   PASS
customer_id → customers  one_to_one          100         100                 True                0   PASS
```

## 6. line_total과 날짜 검증

```text
                             check   source  row_count  mismatch_count status
line_total = quantity × unit_price existing        764               0   PASS
```

```text
                                 check  invalid_count  affected_amount status
completed rows with invalid order_date              0              0.0   PASS
```

## 7. 전체 주문 상세 금액과 completed 주문 기준 금액

```text
                 scope      amount  detail_rows
       all_order_items 255610000.0          764
 completed_order_items 148990000.0          474
excluded_non_completed 106620000.0          290
```

## 8. total consistency

```text
          source      amount  difference_from_completed  matches_completed status
completed_source 148990000.0                        0.0               True   PASS
        category 148990000.0                        0.0               True   PASS
         monthly 148990000.0                        0.0               True   PASS
        customer 148990000.0                        0.0               True   PASS
```

## 9. 최종 Validation

```text
                                 check                value             expected status
                          pk_integrity             all PASS             all PASS   PASS
                          fk_integrity                    0                    0   PASS
                     merge_checks_pass             all PASS             all PASS   PASS
                line_total_consistency                    0                    0   PASS
           completed_total_consistency            all match            all match   PASS
          category_sales_ratio_pct_sum                100.0                100.0   PASS
completed_rows_with_invalid_order_date                    0                    0   PASS
          public_customer_columns_safe no forbidden columns no forbidden columns   PASS
```

## 10. 카테고리별 completed 주문 기준 금액

```text
category  total_quantity  total_sales  sales_ratio
     스포츠             295     31743000        21.31
    전자기기             259     26400000        17.72
    생활용품             272     23915000        16.05
      뷰티             223     23383000        15.69
      식품             133     16573000        11.12
      도서             149     16389000        11.00
      패션             111     10587000         7.11
```

## 11. 월별 completed 주문 기준 금액

```text
order_month  total_sales  order_count  avg_order_value
    2025-07      5869000            8         733625.0
    2025-08     15621000           18         867833.0
    2025-09     10190000           13         783846.0
    2025-10     25766000           26         991000.0
    2025-11      8812000           12         734333.0
    2025-12     11501000           14         821500.0
    2026-01     17423000           22         791955.0
    2026-02      9749000           17         573471.0
    2026-03     13429000           14         959214.0
    2026-04     17553000           23         763174.0
    2026-05      8063000           11         733000.0
    2026-06      2826000            4         706500.0
    2026-07      2188000            2        1094000.0
```

## 12. completed 주문 구매 금액 상위 익명 고객

```text
customer_label city  order_count  total_sales  avg_order_value
   Customer 01   성남            5      4100000         820000.0
   Customer 02   고양            4      3996000         999000.0
   Customer 03   수원            4      3880000         970000.0
   Customer 04   서울            5      3590000         718000.0
   Customer 05   서울            4      3523000         880750.0
   Customer 06   인천            2      3191000        1595500.0
   Customer 07   성남            2      3178000        1589000.0
   Customer 08   광주            3      3153000        1051000.0
   Customer 09   서울            4      3093000         773250.0
   Customer 10   부산            2      2990000        1495000.0
```

## 13. 주문 상태별 주문 수

```text
order_status  order_count  order_ratio
   completed          184        61.33
   cancelled           64        21.33
    refunded           52        17.33
```

## 14. 해석 메모

```text
                analysis                                    observation                           caution              next_question
카테고리별 completed 주문 기준 금액    completed 주문 기준 금액 비중이 높은 카테고리를 확인할 수 있습니다. 금액이 높은 이유가 판매 수량인지 단가인지 구분해야 합니다.   카테고리별 평균 판매 단가는 어떻게 다른가?
   월별 completed 주문 기준 금액 시간에 따른 completed 주문 기준 금액의 증가와 감소를 확인할 수 있습니다.     프로모션이나 계절성이 원인이라고 단정할 수 없습니다. 주문 수와 평균 주문 금액 중 무엇이 변했는가?
  고객별 completed 주문 구매 금액     completed 주문 기준 구매 금액이 높은 고객군을 확인할 수 있습니다.       일회성 고액 구매와 반복 구매를 구분해야 합니다.    최근 구매일과 구매 빈도는 어떻게 다른가?
             주문 상태별 주문 수                 완료, 취소, 환불 주문의 분포를 확인할 수 있습니다.       주문 상태의 정의와 처리 기준을 확인해야 합니다.       취소율과 환불률은 월별로 달라지는가?
```

## 15. 한계점

- 현재 데이터만으로 고객 만족도나 이탈 이유를 분석할 수 없습니다.
- 금액 변동의 원인을 설명하려면 프로모션, 광고, 재고, 계절성 데이터가 필요합니다.
- completed 주문 기준 금액은 실제 회계상 순매출과 같은 의미라고 단정하지 않습니다.
- 고객별 결과는 익명화된 분석용 요약이며 개인을 평가하는 용도로 사용하면 안 됩니다.
- 자동 Validation PASS는 정해 둔 구조·수치 검증을 통과했다는 뜻이며 해석의 타당성은 사람이 별도로 확인해야 합니다.

## 16. 다음 단계

- 카테고리별 판매 수량과 평균 판매 단가를 함께 비교합니다.
- 월별 주문 수와 평균 주문 금액의 변화를 분리해 확인합니다.
- 고객별 최근 구매일과 구매 빈도를 추가합니다.
- 주문 취소율과 환불률의 월별 변화를 분석합니다.
