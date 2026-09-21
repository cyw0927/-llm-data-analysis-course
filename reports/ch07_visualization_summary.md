# Chapter 7 데이터 시각화 요약 보고서

## 1. 시각화 목적

전처리된 온라인 쇼핑몰 데이터를 사용해 질문에 맞는 그래프를 만들고 축·범위·해석을 검증했습니다.

## 2. 생성한 그래프 목록

```text
             chart                         question                                   scope      interpretation_point                                 file_name
    카테고리별 완료 주문 금액         카테고리별 완료 주문 금액은 어떻게 다른가?                        completed orders  금액 차이는 수량·단가 등 추가 지표로 확인    ch07_category_completed_amount_bar.png
       월별 완료 주문 금액           월별 완료 주문 금액은 어떻게 변하는가?     completed orders + valid order_date    증감은 관찰이며 원인은 추가 데이터 필요    ch07_monthly_completed_amount_line.png
          상품 가격 분포            상품 가격은 어떤 구간에 몰려 있는가?                          product master 상품 구성 분포이며 판매 선호를 의미하지 않음               ch07_product_price_hist.png
상품 가격과 완료 주문 판매 수량 상품 가격과 완료 주문 판매 수량은 어떤 패턴을 보이는가?  completed orders aggregated by product           관계는 인과를 의미하지 않음 ch07_price_completed_quantity_scatter.png
 완료 주문 구매 금액 상위 고객   완료 주문 구매 금액 상위 고객군은 어떻게 구성되는가? completed orders aggregated by customer   Top N이며 충성도를 자동 의미하지 않음    ch07_top_customers_anonymized_barh.png
       주문 상태별 주문 수            주문 상태별 주문 수는 어떻게 다른가?                              all orders 상태 분포만으로 취소·환불 원인을 알 수 없음                 ch07_order_status_bar.png
```

## 3. 분석 범위

- 카테고리·월·상품·고객 금액성 그래프는 `order_status == "completed"` 범위를 사용합니다.
- 상품 가격 히스토그램은 주문 상태와 무관한 상품 마스터 가격 분포입니다.
- 주문 상태별 주문 수 그래프는 전체 주문을 사용합니다.
- `line_total`은 주문 상세의 `quantity × unit_price`이며 회계상 순매출로 단정하지 않습니다.

## 4. 주요 해석 원칙

- 카테고리별 완료 주문 금액 차이는 판매 수량·단가 등 추가 지표와 함께 봅니다.
- 월별 증감은 관찰이며 프로모션·계절성 같은 원인은 추가 데이터가 필요합니다.
- 가격 분포는 상품 구성을 보여 주며 고객 선호를 직접 의미하지 않습니다.
- 가격과 판매 수량의 관계는 인과관계를 의미하지 않습니다.
- 상위 고객 그래프는 Top N 일부이며 익명 라벨을 사용합니다.
- 주문 상태별 건수만으로 취소·환불 원인을 알 수 없습니다.

## 5. 다음 단계

다음 장에서는 검증된 집계표와 그래프를 작은 데이터 분석 프로젝트로 연결합니다.
