# Chapter 07 준비용 data/processed 재생성 기록

## 입력

이 저장소에는 공식 Chapter 05 전용 Raw(practice/chapter05/data/raw)가 없어 프로젝트 공통 `data/raw`를 입력으로 사용했습니다. 전처리 함수는 공식 `src/preprocessing.py`를 그대로 사용했습니다.

## 전처리 전후 크기 비교

```text
    dataset  rows_raw  columns_raw  rows_processed  columns_processed
  customers       150            6             150                  6
order_items       764            5             764                  6
     orders       300            5             300                  7
   products       100            4             100                  4
```

## 중복 점검

```text
    dataset  row_duplicate_count    key_column  key_duplicate_count
  customers                    0   customer_id                    0
   products                    0    product_id                    0
     orders                    0      order_id                    0
order_items                    0 order_item_id                    0
```

## 전처리 후 파일 간 관계 점검

```text
                                               check  invalid_count
  orders.customer_id exists in customers.customer_id              0
      order_items.order_id exists in orders.order_id              0
order_items.product_id exists in products.product_id              0
```
