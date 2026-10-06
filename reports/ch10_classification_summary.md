# Chapter 10 분류 분석 요약 보고서

## 1. 분석 목적과 예측 시점
주문이 생성된 직후 시점에서, 그 주문이 이후 취소될지(cancelled=1) 완료될지(completed=0)를 추정합니다.
refunded 등 다른 상태는 타깃 범위에서 제외했습니다.

## 2. 타깃 분포
```text
 is_cancelled     label  count  ratio_pct
            0 completed    184      74.19
            1 cancelled     64      25.81
```

## 3. Feature Audit
```text
              column  selected            role                                                                                                               reason
         order_month      True allowed_feature                                                                                      예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정
     order_dayofweek      True allowed_feature                                                                                      예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정
                 age      True allowed_feature                                                                                           고객 비식별 특성, 주문 생성 시점에 이미 확정
          item_count      True allowed_feature                                                                                             장바구니 내용, 주문 생성 시점에 이미 확정
      total_quantity      True allowed_feature                                                                                             장바구니 내용, 주문 생성 시점에 이미 확정
        order_amount      True allowed_feature                                                                                             장바구니 내용, 주문 생성 시점에 이미 확정
      category_count      True allowed_feature                                                                                   장바구니에 담긴 카테고리 다양성, 주문 생성 시점에 이미 확정
customer_tenure_days      True allowed_feature 가입일이 주문일보다 이전인 경우에만 계산(주문일 - 가입일). 가입일이 주문일보다 나중인 경우(이 데이터에서 56건)는 주문 시점에 아직 존재하지 않는 정보라 결측으로 남기고 Pipeline이 대체값으로 채움
      payment_method      True allowed_feature                                                                                      예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정
              gender      True allowed_feature                                                                                           고객 비식별 특성, 주문 생성 시점에 이미 확정
                city      True allowed_feature                                                                                           고객 비식별 특성, 주문 생성 시점에 이미 확정
   dominant_category      True allowed_feature                                                                                장바구니에서 가장 많이 담긴 카테고리, 주문 생성 시점에 이미 확정
       cancel_reason     False       forbidden                                                                                  취소가 확정된 뒤에만 존재하는 사후 정보(이번 데이터에는 없음)
        cancelled_at     False       forbidden                                                                                  취소가 확정된 뒤에만 존재하는 사후 정보(이번 데이터에는 없음)
         customer_id     False       forbidden                                                                                                               고객 식별자
        is_cancelled     False       forbidden                                                                                                             예측 대상 자체
            order_id     False       forbidden                                                                                                               주문 식별자
        order_status     False       forbidden                                                                                 Target을 그대로 담고 있는 사후 정보(취소/환불 확정 상태)
          product_id     False       forbidden                                                                                              주문 상세가 확인되어야 알 수 있는 식별자
```

## 4. Train / Validation / Test 분할
```text
     split  rows  ratio_pct  cancelled_count  cancelled_pct
     train   148      59.68               38          25.68
validation    50      20.16               13          26.00
      test    50      20.16               13          26.00
```

## 5. Validation 후보 모델 비교
```text
              model  accuracy  precision   recall       f1
Logistic Regression      0.74        0.5 0.230769 0.315789
Dummy Most Frequent      0.74        0.0 0.000000 0.000000
      Random Forest      0.74        0.0 0.000000 0.000000
```

선택 모델: **Logistic Regression**, 선택 threshold: **0.2**

## 6. Final Test 결과
```text
              model           selection_role  threshold  accuracy  precision   recall       f1
Dummy Most Frequent                 baseline        0.5      0.74   0.000000 0.000000 0.000000
Logistic Regression selected_from_validation        0.2      0.58   0.346154 0.692308 0.461538
```

Baseline 대비 F1 변화: +0.4615

## 7. Confusion Matrix (Frozen Model)
```text
              model          cell  count
Logistic Regression   TN (완료->완료)     20
Logistic Regression FP (완료->취소위험)     17
Logistic Regression   FN (취소->완료)      4
Logistic Regression TP (취소->취소위험)      9
```

## 8. 자동 검증 Evidence
```text
                             check value status
            binary_target_contract  True   PASS
         forbidden_feature_overlap     0   PASS
             strict_merge_contract  True   PASS
       all_splits_have_two_classes  True   PASS
    selected_model_from_validation  True   PASS
selected_threshold_from_validation   0.2   PASS
         public_prediction_privacy     0   PASS
             test_rows_for_metrics    50   PASS
```

## 9. 사람 검토 체크리스트
```text
                                check_item status
          completed=0, cancelled=1만 사용했는가?      □
           refunded와 기타 상태를 타깃 범위에서 제외했는가?      □
                         예측 시점을 명확히 정의했는가?      □
       target, ID, 사후 정보를 feature에서 제외했는가?      □
line_total = quantity * unit_price를 검증했는가?      □
                   주문 단위 특징과 병합 관계를 검증했는가?      □
         전처리가 Pipeline 안에서 Train으로만 학습되는가?      □
                   모델을 Validation에서 선택했는가?      □
            Threshold를 Validation에서 선택했는가?      □
                  Final Test 전에 선택을 고정했는가?      □
                       공개 결과에 원본 식별자가 없는가?      □
                      낮은 성능도 숨기지 않고 기록했는가?      □
```

## 10. 해석 시 주의사항
- Accuracy만으로는 클래스 불균형 문제를 판단할 수 없습니다.
- Threshold를 낮추면 recall이 오르고 FP가 늘 수 있으며, 높이면 그 반대입니다.
- 이번 분할은 교육용 random stratified split이며, 실제 운영 전에는 시간 순서 기반 out-of-time 평가가 필요합니다.
- 예측 패턴만으로 취소의 실제 원인을 단정하지 않습니다.
