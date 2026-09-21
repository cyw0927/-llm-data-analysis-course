"""Chapter 07 준비: data/processed 재생성 스크립트.

이 저장소에는 공식 Chapter 05 실습용 Raw(practice/chapter05/data/raw, 의도적으로
결측/중복/이상값/PK-FK 오류가 섞인 전용 데이터셋)가 포함되어 있지 않습니다.
대신 프로젝트 공통 data/raw(이미 저장소에 있고 Chapter 08 실습에서도 사용한 파일)를
입력으로 사용하여, 공식 Chapter 05 전처리 함수(src/preprocessing.py)를 그대로
실행합니다. 이렇게 만든 data/processed/*_clean.csv를 기준으로 Chapter 07
visualization.csv를 다시 생성해 두 파일이 서로 어긋나지 않도록 맞춥니다.

실행 방법:
    python scripts/rebuild_processed_data.py

입력:
    data/raw/customers.csv
    data/raw/products.csv
    data/raw/orders.csv
    data/raw/order_items.csv

출력:
    data/processed/customers_clean.csv
    data/processed/products_clean.csv
    data/processed/orders_clean.csv
    data/processed/order_items_clean.csv
    reports/ch07_prep_relationship_check.md
"""

from pathlib import Path

from src.data_loader import load_sales_data
from src.preprocessing import (
    compare_shapes,
    duplicate_summary,
    preprocess_sales_data,
    save_processed_data,
    validate_relationships,
)


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "ch07_prep_relationship_check.md"


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)

    raw_data = load_sales_data(RAW_DIR)
    processed_data = preprocess_sales_data(raw_data)

    print("[전처리 전후 크기 비교]")
    comparison = compare_shapes(raw_data, processed_data)
    print(comparison.to_string(index=False))

    print("\n[중복 점검]")
    duplicates = duplicate_summary(
        processed_data,
        key_columns={
            "customers": "customer_id",
            "products": "product_id",
            "orders": "order_id",
            "order_items": "order_item_id",
        },
    )
    print(duplicates.to_string(index=False))

    print("\n[전처리 후 파일 간 관계 점검]")
    relationship_checks = validate_relationships(processed_data)
    print(relationship_checks.to_string(index=False))

    saved_paths = save_processed_data(processed_data, PROCESSED_DIR)
    print("\n[저장한 전처리 파일]")
    for path in saved_paths:
        print("-", path)

    REPORT_PATH.write_text(
        "# Chapter 07 준비용 data/processed 재생성 기록\n\n"
        "## 입력\n\n"
        "이 저장소에는 공식 Chapter 05 전용 Raw(practice/chapter05/data/raw)가 없어 "
        "프로젝트 공통 `data/raw`를 입력으로 사용했습니다. "
        "전처리 함수는 공식 `src/preprocessing.py`를 그대로 사용했습니다.\n\n"
        "## 전처리 전후 크기 비교\n\n"
        "```text\n" + comparison.to_string(index=False) + "\n```\n\n"
        "## 중복 점검\n\n"
        "```text\n" + duplicates.to_string(index=False) + "\n```\n\n"
        "## 전처리 후 파일 간 관계 점검\n\n"
        "```text\n" + relationship_checks.to_string(index=False) + "\n```\n",
        encoding="utf-8",
    )
    print(f"\n[요약 저장] {REPORT_PATH}")


if __name__ == "__main__":
    main()
