"""Chapter 10 leakage-aware classification analysis utilities.

The workflow separates model/threshold selection from final test evaluation:

1. keep the target to exactly two classes (completed=0, cancelled=1),
2. build order-level features and verify line_total = quantity * unit_price,
3. merge order features with customers and reject silent join losses,
4. split into Train / Validation / Test with stratified sampling,
5. learn preprocessing inside sklearn Pipelines (Train only),
6. select the candidate model using Validation metrics only,
7. select the decision threshold using Validation metrics only,
8. freeze model + threshold before touching Final Test,
9. evaluate Baseline and the frozen model on Final Test only,
10. save an internal (identifier-bearing) prediction table separately from
    the public, privacy-safe prediction table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "is_cancelled"

NUMERIC_FEATURES = [
    "order_month",
    "order_dayofweek",
    "age",
    "item_count",
    "total_quantity",
    "order_amount",
    "category_count",
    "customer_tenure_days",
]
CATEGORICAL_FEATURES = ["payment_method", "gender", "city", "dominant_category"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

ALLOWED_TARGET_STATUSES = {"completed": 0, "cancelled": 1}
EXCLUDED_STATUSES_EXAMPLE = {"refunded"}

FORBIDDEN_FEATURES = {
    "is_cancelled",
    "order_status",
    "order_id",
    "customer_id",
    "product_id",
    "cancel_reason",
    "cancelled_at",
}

FORBIDDEN_REASONS = {
    "is_cancelled": "예측 대상 자체",
    "order_status": "Target을 그대로 담고 있는 사후 정보(취소/환불 확정 상태)",
    "order_id": "주문 식별자",
    "customer_id": "고객 식별자",
    "product_id": "주문 상세가 확인되어야 알 수 있는 식별자",
    "cancel_reason": "취소가 확정된 뒤에만 존재하는 사후 정보(이번 데이터에는 없음)",
    "cancelled_at": "취소가 확정된 뒤에만 존재하는 사후 정보(이번 데이터에는 없음)",
}

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "gender", "age", "city", "signup_date"},
    "orders": {
        "order_id",
        "customer_id",
        "order_date",
        "payment_method",
        "order_status",
    },
    "order_items": {"order_id", "quantity", "unit_price", "product_id"},
    "products": {"product_id", "category"},
}


def make_one_hot_encoder() -> OneHotEncoder:
    """Return a dense encoder compatible with multiple sklearn versions."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def load_classification_source_data(
    processed_dir: str | Path = "data/processed",
) -> dict[str, pd.DataFrame]:
    """Load Chapter10 validated processed files; never silently fall back to raw data."""
    input_dir = Path(processed_dir)
    file_map = {
        "customers": input_dir / "customers_clean.csv",
        "orders": input_dir / "orders_clean.csv",
        "order_items": input_dir / "order_items_clean.csv",
        "products": input_dir / "products_clean.csv",
    }
    missing_files = [path for path in file_map.values() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "Chapter10 모델링 입력이 없습니다. 먼저 `python scripts/prepare_ch10_data.py`를 실행하세요. "
            + "누락 파일: "
            + ", ".join(str(path) for path in missing_files)
        )
    return {name: pd.read_csv(path) for name, path in file_map.items()}


def validate_required_columns(datasets: dict[str, pd.DataFrame]) -> None:
    """Fail fast when a required dataset or modeling column is missing."""
    missing_datasets = sorted(set(REQUIRED_COLUMNS) - set(datasets))
    if missing_datasets:
        raise KeyError(f"필수 데이터셋이 없습니다: {missing_datasets}")
    for name, columns in REQUIRED_COLUMNS.items():
        missing_columns = sorted(columns - set(datasets[name].columns))
        if missing_columns:
            raise KeyError(f"{name}에 필요한 컬럼이 없습니다: {missing_columns}")


def validate_feature_columns(
    feature_columns: Iterable[str] = FEATURE_COLUMNS,
) -> None:
    """Reject target values, identifiers, and post-outcome fields."""
    columns = list(feature_columns)
    leaked_features = sorted(set(columns) & FORBIDDEN_FEATURES)
    if leaked_features:
        raise ValueError(f"입력값에 누수 위험 컬럼이 있습니다: {leaked_features}")
    duplicates = pd.Index(columns)[pd.Index(columns).duplicated()].tolist()
    if duplicates:
        raise ValueError(f"입력값 목록에 중복 컬럼이 있습니다: {duplicates}")


def _require_unique_key(df: pd.DataFrame, key: str, dataset: str) -> None:
    if key not in df.columns:
        raise KeyError(f"{dataset}.{key} 컬럼이 없습니다.")
    missing_count = int(df[key].isna().sum())
    duplicate_count = int(df[key].duplicated().sum())
    if missing_count or duplicate_count:
        raise ValueError(
            f"{dataset}.{key} 검증 실패: "
            f"missing={missing_count}, duplicate={duplicate_count}"
        )


def build_order_item_features(
    order_items: pd.DataFrame,
    products: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate order_items to one row per order and verify line_total = quantity * unit_price.

    When ``products`` is given, also derive basket-composition features
    (``category_count``, ``dominant_category``) that are known at order-creation
    time, the same way ``item_count``/``total_quantity``/``order_amount`` are.
    """
    items = order_items.copy()
    missing = sorted({"order_id", "quantity", "unit_price"} - set(items.columns))
    if missing:
        raise KeyError(f"order_items에 필요한 컬럼이 없습니다: {missing}")

    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce")
    items["unit_price"] = pd.to_numeric(items["unit_price"], errors="coerce")
    invalid = items[["order_id", "quantity", "unit_price"]].isna().any(axis=1)
    if invalid.any():
        raise ValueError(
            "주문 특징을 만들 수 없는 주문 상세 행이 있습니다: "
            f"{int(invalid.sum())}건"
        )

    if (items["quantity"] <= 0).any() or (items["unit_price"] <= 0).any():
        raise ValueError("quantity와 unit_price는 0보다 커야 합니다.")

    expected = items["quantity"] * items["unit_price"]
    if "line_total" in items.columns:
        items["line_total"] = pd.to_numeric(items["line_total"], errors="coerce")
        if items["line_total"].isna().any():
            raise ValueError("order_items.line_total에 숫자 변환 실패가 있습니다.")
        mismatch = (items["line_total"] - expected).abs().gt(1e-6)
        if mismatch.any():
            raise ValueError(
                "line_total과 quantity × unit_price가 일치하지 않는 행이 있습니다: "
                f"{int(mismatch.sum())}건"
            )
    else:
        items["line_total"] = expected

    features = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_id", "size"),
            total_quantity=("quantity", "sum"),
            order_amount=("line_total", "sum"),
        )
        .sort_values("order_id")
        .reset_index(drop=True)
    )

    if products is not None:
        missing_products = sorted({"product_id", "category"} - set(products.columns))
        if missing_products:
            raise KeyError(f"products에 필요한 컬럼이 없습니다: {missing_products}")
        if "product_id" not in items.columns:
            raise KeyError("order_items에 product_id 컬럼이 없어 카테고리 특징을 만들 수 없습니다.")

        items_with_category = items.merge(
            products[["product_id", "category"]], on="product_id", how="left"
        )
        if items_with_category["category"].isna().any():
            raise ValueError(
                "order_items의 product_id가 products에 연결되지 않는 행이 있습니다: "
                f"{int(items_with_category['category'].isna().sum())}건"
            )

        category_count = (
            items_with_category.groupby("order_id")["category"]
            .nunique()
            .rename("category_count")
        )

        category_quantity = (
            items_with_category.groupby(["order_id", "category"], as_index=False)["quantity"]
            .sum()
            .sort_values(["order_id", "quantity", "category"], ascending=[True, False, True])
        )
        dominant_category = (
            category_quantity.drop_duplicates("order_id", keep="first")
            .set_index("order_id")["category"]
            .rename("dominant_category")
        )

        features = features.merge(category_count, on="order_id", how="left")
        features = features.merge(dominant_category, on="order_id", how="left")

    _require_unique_key(features, "order_id", "order_item_features")
    return features


def build_classification_dataset(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Build one-row-per-order modeling data restricted to completed/cancelled orders."""
    datasets = {
        "customers": customers.copy(),
        "orders": orders.copy(),
        "order_items": order_items.copy(),
        "products": products.copy(),
    }
    validate_required_columns(datasets)
    validate_feature_columns()

    customers_data = datasets["customers"]
    orders_data = datasets["orders"]
    items_data = datasets["order_items"]
    products_data = datasets["products"]

    _require_unique_key(customers_data, "customer_id", "customers")
    _require_unique_key(orders_data, "order_id", "orders")
    if orders_data["customer_id"].isna().any():
        raise ValueError("orders.customer_id에 결측치가 있습니다.")

    order_features = build_order_item_features(items_data, products_data)

    merged = orders_data.merge(
        order_features,
        on="order_id",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    unmatched = merged.loc[merged["_merge"].ne("both")]
    if not unmatched.empty:
        raise ValueError(
            "orders와 주문 특징의 관계가 완전하지 않습니다: "
            f"{merged['_merge'].value_counts().to_dict()}"
        )
    model_data = merged.drop(columns="_merge")

    model_data = model_data.merge(
        customers_data[["customer_id", "gender", "age", "city", "signup_date"]],
        on="customer_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    unmatched_customer_count = int(model_data["_merge"].eq("left_only").sum())
    if unmatched_customer_count:
        raise ValueError(
            "orders.customer_id가 customers에 연결되지 않는 주문이 있습니다: "
            f"{unmatched_customer_count}건"
        )
    model_data = model_data.drop(columns="_merge")

    model_data["order_date"] = pd.to_datetime(model_data["order_date"], errors="coerce")
    if model_data["order_date"].isna().any():
        raise ValueError(
            "order_date 날짜 변환 실패가 있습니다: "
            f"{int(model_data['order_date'].isna().sum())}건"
        )
    model_data["order_month"] = model_data["order_date"].dt.month
    model_data["order_dayofweek"] = model_data["order_date"].dt.dayofweek
    model_data["age"] = pd.to_numeric(model_data["age"], errors="coerce")

    # customer_tenure_days: 가입일이 주문일보다 이전일 때만 계산합니다.
    # 가입일이 주문일보다 나중이면(이번 데이터의 56건) 주문 시점에는 아직 존재하지
    # 않았던 정보이므로, 값을 억지로 만들지 않고 결측으로 남겨 Pipeline의
    # median imputation이 처리하도록 합니다.
    model_data["signup_date"] = pd.to_datetime(model_data["signup_date"], errors="coerce")
    tenure_days = (model_data["order_date"] - model_data["signup_date"]).dt.days
    model_data["customer_tenure_days"] = tenure_days.where(tenure_days >= 0)
    model_data = model_data.drop(columns="signup_date")

    if not set(model_data["order_status"].unique()) >= set(ALLOWED_TARGET_STATUSES):
        raise ValueError(
            "order_status에 completed/cancelled가 모두 존재해야 합니다: "
            f"{sorted(model_data['order_status'].unique())}"
        )

    in_scope = model_data["order_status"].isin(ALLOWED_TARGET_STATUSES)
    model_data = model_data.loc[in_scope].copy()
    model_data[TARGET_COLUMN] = (
        model_data["order_status"].map(ALLOWED_TARGET_STATUSES).astype(int)
    )

    return model_data.sort_values(["order_date", "order_id"]).reset_index(drop=True)


def build_merge_checks(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    model_data: pd.DataFrame,
) -> pd.DataFrame:
    """Record before/after row counts for the two merges as public evidence."""
    order_features = build_order_item_features(order_items)
    rows = [
        {
            "merge": "orders <-> order_item_features",
            "relationship": "one_to_one",
            "left_rows": len(orders),
            "right_rows": len(order_features),
            "unmatched_count": 0,
        },
        {
            "merge": "orders -> customers",
            "relationship": "many_to_one",
            "left_rows": len(orders),
            "right_rows": len(customers),
            "unmatched_count": 0,
        },
        {
            "merge": "target scope filter (completed/cancelled only)",
            "relationship": "row_filter",
            "left_rows": len(orders),
            "right_rows": len(model_data),
            "unmatched_count": len(orders) - len(model_data),
        },
    ]
    return pd.DataFrame(rows)


def build_data_quality_checks(
    order_items: pd.DataFrame,
    customers: pd.DataFrame | None = None,
    orders: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Public, identifier-free data quality evidence for order_items (and, if given, signup/tenure)."""
    items = order_items.copy()
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce")
    items["unit_price"] = pd.to_numeric(items["unit_price"], errors="coerce")
    expected = items["quantity"] * items["unit_price"]
    line_total_mismatch = 0
    if "line_total" in items.columns:
        line_total_mismatch = int(
            (pd.to_numeric(items["line_total"], errors="coerce") - expected)
            .abs()
            .gt(1e-6)
            .sum()
        )
    rows = [
        {"check": "quantity_positive", "failing_rows": int((items["quantity"] <= 0).sum())},
        {"check": "unit_price_positive", "failing_rows": int((items["unit_price"] <= 0).sum())},
        {"check": "line_total_matches_quantity_times_unit_price", "failing_rows": line_total_mismatch},
    ]

    if customers is not None and orders is not None:
        merged = orders[["customer_id", "order_date"]].merge(
            customers[["customer_id", "signup_date"]], on="customer_id", how="left"
        )
        merged["order_date"] = pd.to_datetime(merged["order_date"], errors="coerce")
        merged["signup_date"] = pd.to_datetime(merged["signup_date"], errors="coerce")
        signup_after_order = int((merged["signup_date"] > merged["order_date"]).sum())
        rows.append(
            {
                "check": "signup_date_after_order_date (customer_tenure_days를 결측 처리한 건수)",
                "failing_rows": signup_after_order,
            }
        )

    return pd.DataFrame(rows)


def build_target_distribution(model_data: pd.DataFrame) -> pd.DataFrame:
    counts = model_data[TARGET_COLUMN].value_counts().sort_index()
    total = int(counts.sum())
    return pd.DataFrame(
        {
            "is_cancelled": counts.index,
            "label": ["completed" if v == 0 else "cancelled" for v in counts.index],
            "count": counts.to_numpy(),
            "ratio_pct": (counts.to_numpy() / total * 100).round(2),
        }
    )


ALLOWED_FEATURE_REASONS = {
    "order_month": "예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정",
    "order_dayofweek": "예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정",
    "age": "고객 비식별 특성, 주문 생성 시점에 이미 확정",
    "item_count": "장바구니 내용, 주문 생성 시점에 이미 확정",
    "total_quantity": "장바구니 내용, 주문 생성 시점에 이미 확정",
    "order_amount": "장바구니 내용, 주문 생성 시점에 이미 확정",
    "category_count": "장바구니에 담긴 카테고리 다양성, 주문 생성 시점에 이미 확정",
    "customer_tenure_days": (
        "가입일이 주문일보다 이전인 경우에만 계산(주문일 - 가입일). "
        "가입일이 주문일보다 나중인 경우(이 데이터에서 56건)는 주문 시점에 "
        "아직 존재하지 않는 정보라 결측으로 남기고 Pipeline이 대체값으로 채움"
    ),
    "payment_method": "예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정",
    "gender": "고객 비식별 특성, 주문 생성 시점에 이미 확정",
    "city": "고객 비식별 특성, 주문 생성 시점에 이미 확정",
    "dominant_category": "장바구니에서 가장 많이 담긴 카테고리, 주문 생성 시점에 이미 확정",
}


def build_feature_audit() -> pd.DataFrame:
    allowed = [
        {
            "column": column,
            "selected": True,
            "role": "allowed_feature",
            "reason": ALLOWED_FEATURE_REASONS.get(
                column, "예측 시점(주문 생성 직후)에 이미 확정되어 있다고 가정"
            ),
        }
        for column in FEATURE_COLUMNS
    ]
    forbidden = [
        {
            "column": column,
            "selected": False,
            "role": "forbidden",
            "reason": FORBIDDEN_REASONS[column],
        }
        for column in sorted(FORBIDDEN_FEATURES)
    ]
    return pd.DataFrame(allowed + forbidden)


def split_train_val_test(
    model_data: pd.DataFrame,
    test_size: float = 0.2,
    val_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified random split preserving the class ratio in Train/Validation/Test."""
    required = {TARGET_COLUMN, *FEATURE_COLUMNS}
    missing = sorted(required - set(model_data.columns))
    if missing:
        raise KeyError(f"분할에 필요한 컬럼이 없습니다: {missing}")

    train_val, test_data = train_test_split(
        model_data,
        test_size=test_size,
        random_state=random_state,
        stratify=model_data[TARGET_COLUMN],
    )
    relative_val_size = val_size / (1 - test_size)
    train_data, val_data = train_test_split(
        train_val,
        test_size=relative_val_size,
        random_state=random_state,
        stratify=train_val[TARGET_COLUMN],
    )

    for name, split in [("Train", train_data), ("Validation", val_data), ("Test", test_data)]:
        if split[TARGET_COLUMN].nunique() < 2:
            raise ValueError(f"{name} split에 클래스가 2개 모두 존재하지 않습니다.")

    return (
        train_data.reset_index(drop=True),
        val_data.reset_index(drop=True),
        test_data.reset_index(drop=True),
    )


def build_split_summary(
    train_data: pd.DataFrame,
    val_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> pd.DataFrame:
    total_rows = len(train_data) + len(val_data) + len(test_data)
    rows = []
    for name, split in [("train", train_data), ("validation", val_data), ("test", test_data)]:
        cancelled = int(split[TARGET_COLUMN].sum())
        rows.append(
            {
                "split": name,
                "rows": len(split),
                "ratio_pct": round(len(split) / total_rows * 100, 2),
                "cancelled_count": cancelled,
                "cancelled_pct": round(cancelled / len(split) * 100, 2),
            }
        )
    return pd.DataFrame(rows)


def make_preprocessor() -> ColumnTransformer:
    """Create numeric/categorical preprocessing that is fit on Train only."""
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", make_one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )


def make_classification_models(random_state: int = 42) -> dict[str, Pipeline]:
    """Create fixed candidates used for Validation-only model selection."""
    return {
        "Dummy Most Frequent": Pipeline(
            [("preprocessor", make_preprocessor()), ("model", DummyClassifier(strategy="most_frequent"))]
        ),
        "Logistic Regression": Pipeline(
            [
                ("preprocessor", make_preprocessor()),
                ("model", LogisticRegression(max_iter=1000, random_state=random_state)),
            ]
        ),
        "Random Forest": Pipeline(
            [
                ("preprocessor", make_preprocessor()),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=5,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def evaluate_predictions(y_true, y_pred) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def cross_validate_on_validation(
    models: dict[str, Pipeline],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> pd.DataFrame:
    """Fit every candidate on Train and score once on Validation (Test untouched)."""
    validate_feature_columns(X_train.columns)
    rows: list[dict[str, Any]] = []
    for model_name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_val)
        metrics = evaluate_predictions(y_val, pred)
        rows.append({"model": model_name, **metrics})
    return (
        pd.DataFrame(rows)
        .sort_values(["f1", "recall", "precision"], ascending=False)
        .reset_index(drop=True)
    )


def select_model_from_validation(validation_comparison: pd.DataFrame) -> str:
    """Freeze the best non-baseline candidate using Validation F1/Recall/Precision."""
    candidates = validation_comparison.loc[
        ~validation_comparison["model"].eq("Dummy Most Frequent")
    ].sort_values(["f1", "recall", "precision"], ascending=False)
    if candidates.empty:
        raise ValueError("선택할 비베이스라인 모델 결과가 없습니다.")
    return str(candidates.iloc[0]["model"])


def select_threshold_from_validation(
    model: Pipeline,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    thresholds: Iterable[float] = tuple(round(t, 2) for t in np.arange(0.1, 0.91, 0.05)),
) -> tuple[float, pd.DataFrame]:
    """Score candidate thresholds on Validation probabilities only."""
    probabilities = model.predict_proba(X_val)[:, 1]
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        pred = (probabilities >= threshold).astype(int)
        metrics = evaluate_predictions(y_val, pred)
        rows.append({"threshold": float(threshold), **metrics})
    threshold_metrics = pd.DataFrame(rows)
    ranked = threshold_metrics.sort_values(
        ["f1", "recall", "precision"], ascending=False
    ).reset_index(drop=True)
    if ranked.empty:
        raise ValueError("threshold 후보 결과가 없습니다.")
    selected_threshold = float(ranked.iloc[0]["threshold"])
    return selected_threshold, threshold_metrics.sort_values("threshold").reset_index(drop=True)


def train_and_evaluate_final(
    models: dict[str, Pipeline],
    selected_model_name: str,
    selected_threshold: float,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Evaluate only Baseline and the frozen (model, threshold) pair on Final Test."""
    validate_feature_columns(X_train.columns)
    if selected_model_name == "Dummy Most Frequent":
        raise ValueError("선택 모델은 비베이스라인 후보여야 합니다.")
    if selected_model_name not in models or "Dummy Most Frequent" not in models:
        raise KeyError("최종 평가에 필요한 모델이 없습니다.")

    rows: list[dict[str, Any]] = []
    predictions: dict[str, np.ndarray] = {}
    probabilities: dict[str, np.ndarray] = {}
    for model_name in ["Dummy Most Frequent", selected_model_name]:
        model = models[model_name]
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        threshold = 0.5 if model_name == "Dummy Most Frequent" else selected_threshold
        pred = (proba >= threshold).astype(int)
        metrics = evaluate_predictions(y_test, pred)
        rows.append(
            {
                "model": model_name,
                "selection_role": (
                    "baseline" if model_name == "Dummy Most Frequent" else "selected_from_validation"
                ),
                "threshold": threshold,
                **metrics,
            }
        )
        predictions[model_name] = pred
        probabilities[model_name] = proba

    comparison = pd.DataFrame(rows)
    return comparison.reset_index(drop=True), predictions, probabilities


def build_confusion_matrix(y_true, y_pred, model_name: str) -> pd.DataFrame:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return pd.DataFrame(
        [
            {"model": model_name, "cell": "TN (완료->완료)", "count": int(tn)},
            {"model": model_name, "cell": "FP (완료->취소위험)", "count": int(fp)},
            {"model": model_name, "cell": "FN (취소->완료)", "count": int(fn)},
            {"model": model_name, "cell": "TP (취소->취소위험)", "count": int(tp)},
        ]
    )


def plot_target_distribution(
    target_distribution: pd.DataFrame,
    figure_dir: str | Path = "reports/figures",
    filename: str = "ch10_target_distribution.png",
) -> Path:
    """Draw completed vs cancelled counts as a bar chart."""
    import matplotlib.pyplot as plt

    output_dir = Path(figure_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    korean = configure_korean_font()

    fig, ax = plt.subplots(figsize=(5, 4))
    colors = ["#4C72B0", "#C44E52"]
    bars = ax.bar(target_distribution["label"], target_distribution["count"], color=colors)
    for bar, ratio in zip(bars, target_distribution["ratio_pct"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{ratio:.1f}%",
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("건수" if korean else "count")
    ax.set_title("클래스 분포 (completed vs cancelled)" if korean else "Class distribution")
    fig.tight_layout()
    output_path = output_dir / filename
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_validation_comparison(
    validation_comparison: pd.DataFrame,
    figure_dir: str | Path = "reports/figures",
    filename: str = "ch10_validation_comparison.png",
) -> Path:
    """Draw a grouped bar chart of precision/recall/f1 across Validation candidate models."""
    import matplotlib.pyplot as plt

    output_dir = Path(figure_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    korean = configure_korean_font()

    models = validation_comparison["model"].tolist()
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(7.5, 5))
    for i, metric in enumerate(metrics):
        ax.bar(x + (i - 1) * width, validation_comparison[metric], width, label=metric)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=10)
    ax.set_ylabel("score")
    ax.set_title(
        "Validation 후보 모델 비교" if korean else "Validation candidate model comparison"
    )
    ax.legend()
    fig.tight_layout()
    output_path = output_dir / filename
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_threshold_curve(
    threshold_metrics: pd.DataFrame,
    selected_threshold: float,
    figure_dir: str | Path = "reports/figures",
    filename: str = "ch10_threshold_curve.png",
) -> Path:
    """Draw precision/recall/f1 curves across candidate thresholds."""
    import matplotlib.pyplot as plt

    output_dir = Path(figure_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    korean = configure_korean_font()

    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot(threshold_metrics["threshold"], threshold_metrics["precision"], marker="o", label="precision")
    ax.plot(threshold_metrics["threshold"], threshold_metrics["recall"], marker="o", label="recall")
    ax.plot(threshold_metrics["threshold"], threshold_metrics["f1"], marker="o", label="f1")
    ax.axvline(
        selected_threshold,
        color="gray",
        linestyle="--",
        label=(f"selected threshold={selected_threshold}"),
    )
    ax.set_xlabel("threshold")
    ax.set_ylabel("score")
    ax.set_title(
        "Validation Threshold 비교" if korean else "Validation threshold comparison"
    )
    ax.legend()
    fig.tight_layout()
    output_path = output_dir / filename
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def build_confusion_matrix_grid(y_true, y_pred) -> pd.DataFrame:
    """Return the confusion matrix as an actual 2x2 grid (rows=actual, cols=predicted)."""
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return pd.DataFrame(
        matrix,
        index=pd.Index(["실제: completed(0)", "실제: cancelled(1)"], name="actual"),
        columns=pd.Index(["예측: completed(0)", "예측: cancelled(1)"], name="predicted"),
    )


def configure_korean_font() -> bool:
    from matplotlib import font_manager

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in [
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]:
        if font_name in available_fonts:
            import matplotlib.pyplot as plt

            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return True
    return False


def plot_confusion_matrix(
    y_true,
    y_pred,
    model_name: str,
    figure_dir: str | Path = "reports/figures",
) -> Path:
    """Draw an actual 2x2 confusion matrix heatmap and save it as a PNG figure."""
    import matplotlib.pyplot as plt

    output_dir = Path(figure_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    korean = configure_korean_font()
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(matrix, cmap="Blues")

    labels = (
        ["완료 (0)", "취소 (1)"] if korean else ["completed (0)", "cancelled (1)"]
    )
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(labels)
    ax.set_xlabel("예측(predicted)" if korean else "predicted")
    ax.set_ylabel("실제(actual)" if korean else "actual")
    ax.set_title(
        f"Confusion Matrix: {model_name}" if not korean else f"Confusion Matrix: {model_name}"
    )

    cell_labels = np.array([["TN", "FP"], ["FN", "TP"]])
    threshold = matrix.max() / 2 if matrix.max() else 0
    for row in range(2):
        for col in range(2):
            count = matrix[row, col]
            color = "white" if count > threshold else "black"
            ax.text(
                col,
                row,
                f"{cell_labels[row, col]}\n{count}",
                ha="center",
                va="center",
                color=color,
                fontsize=13,
                fontweight="bold",
            )

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    output_path = output_dir / "ch10_confusion_matrix.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def create_prediction_result(
    test_data: pd.DataFrame,
    y_test: pd.Series,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    model_name: str,
    threshold: float,
) -> pd.DataFrame:
    if len(test_data) != len(y_test) or len(y_test) != len(y_pred):
        raise ValueError("테스트 데이터와 예측값의 길이가 일치하지 않습니다.")
    result = test_data[["order_id"]].reset_index(drop=True).copy()
    result["actual_is_cancelled"] = y_test.reset_index(drop=True)
    result["predicted_is_cancelled"] = y_pred
    result["cancel_probability"] = y_proba.round(4)
    result["model"] = model_name
    result["threshold"] = threshold
    result["outcome"] = np.select(
        [
            (result["actual_is_cancelled"] == 0) & (result["predicted_is_cancelled"] == 0),
            (result["actual_is_cancelled"] == 0) & (result["predicted_is_cancelled"] == 1),
            (result["actual_is_cancelled"] == 1) & (result["predicted_is_cancelled"] == 0),
        ],
        ["TN", "FP", "FN"],
        default="TP",
    )
    return result


def public_prediction_result(prediction_result: pd.DataFrame) -> pd.DataFrame:
    """Drop order_id and add a non-identifying record_id for public release."""
    public = prediction_result.drop(columns=["order_id"]).reset_index(drop=True)
    public.insert(0, "record_id", np.arange(1, len(public) + 1))
    return public[
        [
            "record_id",
            "actual_is_cancelled",
            "predicted_is_cancelled",
            "cancel_probability",
            "model",
            "threshold",
        ]
    ]


def build_leakage_checklist() -> pd.DataFrame:
    check_items = [
        "completed=0, cancelled=1만 사용했는가?",
        "refunded와 기타 상태를 타깃 범위에서 제외했는가?",
        "예측 시점을 명확히 정의했는가?",
        "target, ID, 사후 정보를 feature에서 제외했는가?",
        "line_total = quantity * unit_price를 검증했는가?",
        "주문 단위 특징과 병합 관계를 검증했는가?",
        "전처리가 Pipeline 안에서 Train으로만 학습되는가?",
        "모델을 Validation에서 선택했는가?",
        "Threshold를 Validation에서 선택했는가?",
        "Final Test 전에 선택을 고정했는가?",
        "공개 결과에 원본 식별자가 없는가?",
        "낮은 성능도 숨기지 않고 기록했는가?",
    ]
    return pd.DataFrame({"check_item": check_items, "status": ["□"] * len(check_items)})


def build_classification_validation(
    train_data: pd.DataFrame,
    val_data: pd.DataFrame,
    test_data: pd.DataFrame,
    selected_model_name: str,
    selected_threshold: float,
    validation_comparison: pd.DataFrame,
    public_prediction: pd.DataFrame,
) -> pd.DataFrame:
    """Create machine-checkable evidence for the core Chapter10 rules."""
    leaked_features = sorted(set(FEATURE_COLUMNS) & FORBIDDEN_FEATURES)
    binary_target_ok = set(pd.concat([train_data[TARGET_COLUMN], val_data[TARGET_COLUMN], test_data[TARGET_COLUMN]]).unique()) == {0, 1}
    merge_ok = True  # enforced structurally by build_classification_dataset's validate= merges
    splits_have_two_classes = all(
        split[TARGET_COLUMN].nunique() == 2 for split in [train_data, val_data, test_data]
    )
    selected_in_validation = selected_model_name in set(validation_comparison["model"])
    threshold_in_range = 0.0 < selected_threshold < 1.0
    forbidden_columns_public = sorted(
        set(public_prediction.columns) & (FORBIDDEN_FEATURES | {"source_index"})
    )
    rows = [
        ["binary_target_contract", binary_target_ok, binary_target_ok],
        ["forbidden_feature_overlap", len(leaked_features), not leaked_features],
        ["strict_merge_contract", merge_ok, merge_ok],
        ["all_splits_have_two_classes", splits_have_two_classes, splits_have_two_classes],
        ["selected_model_from_validation", selected_in_validation, selected_in_validation],
        ["selected_threshold_from_validation", selected_threshold, threshold_in_range],
        ["public_prediction_privacy", len(forbidden_columns_public), not forbidden_columns_public],
        ["test_rows_for_metrics", len(test_data), len(test_data) >= 2],
    ]
    validation = pd.DataFrame(rows, columns=["check", "value", "passed"])
    validation["status"] = validation["passed"].map({True: "PASS", False: "FAIL"})
    failed = validation.loc[validation["status"].eq("FAIL")]
    if not failed.empty:
        raise ValueError(
            "분류 분석 핵심 검증에 실패했습니다:\n" + failed.to_string(index=False)
        )
    return validation.drop(columns="passed")


def build_classification_summary(
    model_data: pd.DataFrame,
    target_distribution: pd.DataFrame,
    split_summary: pd.DataFrame,
    feature_audit: pd.DataFrame,
    validation_comparison: pd.DataFrame,
    selected_model_name: str,
    selected_threshold: float,
    test_metrics: pd.DataFrame,
    confusion: pd.DataFrame,
    validation: pd.DataFrame,
    checklist: pd.DataFrame,
) -> str:
    selected_row = test_metrics.loc[test_metrics["model"].eq(selected_model_name)].iloc[0]
    baseline_row = test_metrics.loc[test_metrics["model"].eq("Dummy Most Frequent")].iloc[0]

    return f"""# Chapter 10 분류 분석 요약 보고서

## 1. 분석 목적과 예측 시점
주문이 생성된 직후 시점에서, 그 주문이 이후 취소될지(cancelled=1) 완료될지(completed=0)를 추정합니다.
refunded 등 다른 상태는 타깃 범위에서 제외했습니다.

## 2. 타깃 분포
```text
{target_distribution.to_string(index=False)}
```

## 3. Feature Audit
```text
{feature_audit.to_string(index=False)}
```

## 4. Train / Validation / Test 분할
```text
{split_summary.to_string(index=False)}
```

## 5. Validation 후보 모델 비교
```text
{validation_comparison.to_string(index=False)}
```

선택 모델: **{selected_model_name}**, 선택 threshold: **{selected_threshold}**

## 6. Final Test 결과
```text
{test_metrics.to_string(index=False)}
```

Baseline 대비 F1 변화: {selected_row['f1'] - baseline_row['f1']:+.4f}

## 7. Confusion Matrix (Frozen Model)
```text
{confusion.to_string(index=False)}
```

## 8. 자동 검증 Evidence
```text
{validation.to_string(index=False)}
```

## 9. 사람 검토 체크리스트
```text
{checklist.to_string(index=False)}
```

## 10. 해석 시 주의사항
- Accuracy만으로는 클래스 불균형 문제를 판단할 수 없습니다.
- Threshold를 낮추면 recall이 오르고 FP가 늘 수 있으며, 높이면 그 반대입니다.
- 이번 분할은 교육용 random stratified split이며, 실제 운영 전에는 시간 순서 기반 out-of-time 평가가 필요합니다.
- 예측 패턴만으로 취소의 실제 원인을 단정하지 않습니다.
"""


def save_classification_outputs(
    model_data: pd.DataFrame,
    target_distribution: pd.DataFrame,
    feature_audit: pd.DataFrame,
    merge_checks: pd.DataFrame,
    data_quality_checks: pd.DataFrame,
    split_summary: pd.DataFrame,
    validation_comparison: pd.DataFrame,
    threshold_metrics: pd.DataFrame,
    test_metrics: pd.DataFrame,
    prediction_result: pd.DataFrame,
    confusion: pd.DataFrame,
    validation: pd.DataFrame,
    checklist: pd.DataFrame,
    selected_model_name: str,
    selected_threshold: float,
    y_test: pd.Series,
    y_pred: np.ndarray,
    report_dir: str | Path = "reports",
) -> dict[str, Path]:
    output_dir = Path(report_dir)
    figure_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "target_distribution": output_dir / "ch10_target_distribution.csv",
        "feature_audit": output_dir / "ch10_feature_audit.csv",
        "merge_checks": output_dir / "ch10_merge_checks.csv",
        "data_quality_checks": output_dir / "ch10_data_quality_checks.csv",
        "split_summary": output_dir / "ch10_split_summary.csv",
        "validation_model_comparison": output_dir / "ch10_validation_model_comparison.csv",
        "validation_threshold_metrics": output_dir / "ch10_validation_threshold_metrics.csv",
        "test_metrics": output_dir / "ch10_test_metrics.csv",
        "classification_predictions": output_dir / "ch10_classification_predictions.csv",
        "confusion_matrix": output_dir / "ch10_confusion_matrix.csv",
        "classification_validation": output_dir / "ch10_classification_validation.csv",
        "classification_summary": output_dir / "ch10_classification_summary.md",
    }

    target_distribution.to_csv(paths["target_distribution"], index=False, encoding="utf-8-sig")
    feature_audit.to_csv(paths["feature_audit"], index=False, encoding="utf-8-sig")
    merge_checks.to_csv(paths["merge_checks"], index=False, encoding="utf-8-sig")
    data_quality_checks.to_csv(paths["data_quality_checks"], index=False, encoding="utf-8-sig")
    split_summary.to_csv(paths["split_summary"], index=False, encoding="utf-8-sig")
    validation_comparison.to_csv(paths["validation_model_comparison"], index=False, encoding="utf-8-sig")
    threshold_metrics.to_csv(paths["validation_threshold_metrics"], index=False, encoding="utf-8-sig")
    test_metrics.to_csv(paths["test_metrics"], index=False, encoding="utf-8-sig")
    public_prediction_result(prediction_result).to_csv(
        paths["classification_predictions"], index=False, encoding="utf-8-sig"
    )
    confusion.to_csv(paths["confusion_matrix"], index=False, encoding="utf-8-sig")
    validation.to_csv(paths["classification_validation"], index=False, encoding="utf-8-sig")
    paths["confusion_matrix_figure"] = plot_confusion_matrix(
        y_test, y_pred, selected_model_name, figure_dir
    )

    summary_text = build_classification_summary(
        model_data=model_data,
        target_distribution=target_distribution,
        split_summary=split_summary,
        feature_audit=feature_audit,
        validation_comparison=validation_comparison,
        selected_model_name=selected_model_name,
        selected_threshold=selected_threshold,
        test_metrics=test_metrics,
        confusion=confusion,
        validation=validation,
        checklist=checklist,
    )
    paths["classification_summary"].write_text(summary_text, encoding="utf-8")
    return paths


def run_classification_analysis(
    processed_dir: str | Path = "data/processed",
    report_dir: str | Path = "reports",
    test_size: float = 0.2,
    val_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, object]:
    """Run the complete Chapter10 workflow with Validation-only selection."""
    data = load_classification_source_data(processed_dir)
    model_data = build_classification_dataset(
        customers=data["customers"],
        orders=data["orders"],
        order_items=data["order_items"],
        products=data["products"],
    )
    train_data, val_data, test_data = split_train_val_test(
        model_data, test_size=test_size, val_size=val_size, random_state=random_state
    )
    X_train = train_data[FEATURE_COLUMNS].copy()
    X_val = val_data[FEATURE_COLUMNS].copy()
    X_test = test_data[FEATURE_COLUMNS].copy()
    y_train = train_data[TARGET_COLUMN].copy()
    y_val = val_data[TARGET_COLUMN].copy()
    y_test = test_data[TARGET_COLUMN].copy()

    models = make_classification_models(random_state=random_state)
    validation_comparison = cross_validate_on_validation(models, X_train, y_train, X_val, y_val)
    selected_model_name = select_model_from_validation(validation_comparison)

    fitted_selected_model = models[selected_model_name]
    fitted_selected_model.fit(X_train, y_train)
    selected_threshold, threshold_metrics = select_threshold_from_validation(
        fitted_selected_model, X_val, y_val
    )

    test_metrics, predictions, probabilities = train_and_evaluate_final(
        models=models,
        selected_model_name=selected_model_name,
        selected_threshold=selected_threshold,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
    )

    prediction_result = create_prediction_result(
        test_data=test_data,
        y_test=y_test,
        y_pred=predictions[selected_model_name],
        y_proba=probabilities[selected_model_name],
        model_name=selected_model_name,
        threshold=selected_threshold,
    )
    confusion = build_confusion_matrix(
        y_test, predictions[selected_model_name], selected_model_name
    )

    target_distribution = build_target_distribution(model_data)
    feature_audit = build_feature_audit()
    merge_checks = build_merge_checks(data["customers"], data["orders"], data["order_items"], model_data)
    data_quality_checks = build_data_quality_checks(
        data["order_items"], customers=data["customers"], orders=data["orders"]
    )
    split_summary = build_split_summary(train_data, val_data, test_data)
    public_prediction = public_prediction_result(prediction_result)

    validation = build_classification_validation(
        train_data=train_data,
        val_data=val_data,
        test_data=test_data,
        selected_model_name=selected_model_name,
        selected_threshold=selected_threshold,
        validation_comparison=validation_comparison,
        public_prediction=public_prediction,
    )
    checklist = build_leakage_checklist()

    output_paths = save_classification_outputs(
        model_data=model_data,
        target_distribution=target_distribution,
        feature_audit=feature_audit,
        merge_checks=merge_checks,
        data_quality_checks=data_quality_checks,
        split_summary=split_summary,
        validation_comparison=validation_comparison,
        threshold_metrics=threshold_metrics,
        test_metrics=test_metrics,
        prediction_result=prediction_result,
        confusion=confusion,
        validation=validation,
        checklist=checklist,
        selected_model_name=selected_model_name,
        selected_threshold=selected_threshold,
        y_test=y_test,
        y_pred=predictions[selected_model_name],
        report_dir=report_dir,
    )

    return {
        "data": data,
        "model_data": model_data,
        "train_data": train_data,
        "val_data": val_data,
        "test_data": test_data,
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "models": models,
        "target_distribution": target_distribution,
        "feature_audit": feature_audit,
        "merge_checks": merge_checks,
        "data_quality_checks": data_quality_checks,
        "split_summary": split_summary,
        "validation_comparison": validation_comparison,
        "selected_model_name": selected_model_name,
        "threshold_metrics": threshold_metrics,
        "selected_threshold": selected_threshold,
        "test_metrics": test_metrics,
        "predictions": predictions,
        "probabilities": probabilities,
        "prediction_result": prediction_result,
        "public_prediction": public_prediction,
        "confusion": confusion,
        "validation": validation,
        "checklist": checklist,
        "output_paths": output_paths,
    }
