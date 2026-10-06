"""Chapter 12 LLM-generated analysis code validation utilities.

Generated code is an unreviewed draft. This module separates two questions:

1. Is the analysis valid?  (schema / PK / FK / merge / completed scope / totals)
2. Is the code safe to run? (AST static scan, never executes the scanned code)

Nothing here executes generated code. Code strings are only parsed with ``ast``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

import pandas as pd


DATASET_FILES = {
    "customers": "customers_clean.csv",
    "products": "products_clean.csv",
    "orders": "orders_clean.csv",
    "order_items": "order_items_clean.csv",
}

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "gender", "age", "city", "signup_date"},
    "products": {"product_id", "category", "price"},
    "orders": {"order_id", "customer_id", "order_date", "payment_method", "order_status"},
    "order_items": {
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "line_total",
    },
}

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
}

RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
]


# ---------------------------------------------------------------------------
# 1. processed 입력, 스키마, PK / FK
# ---------------------------------------------------------------------------
def load_validation_data(processed_dir: str | Path = "data/processed") -> dict[str, pd.DataFrame]:
    """Load the four processed files. Never falls back to raw data."""
    input_dir = Path(processed_dir)
    missing = [str(input_dir / name) for name in DATASET_FILES.values() if not (input_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            "processed 입력이 없습니다. raw로 대체하지 않고 중단합니다. "
            "먼저 전처리 스크립트를 실행하세요. 누락 파일: " + ", ".join(missing)
        )
    return {name: pd.read_csv(input_dir / file) for name, file in DATASET_FILES.items()}


def build_dataset_inventory(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {
            "dataset": name,
            "file": DATASET_FILES[name],
            "rows": len(df),
            "columns": df.shape[1],
            "column_names": ", ".join(df.columns),
        }
        for name, df in datasets.items()
    ]
    return pd.DataFrame(rows)


def validate_required_columns(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """A missing dataset or column is a FAIL row, never silently skipped."""
    rows = []
    for name, required in REQUIRED_COLUMNS.items():
        if name not in datasets:
            rows.append(
                {"dataset": name, "required_count": len(required), "missing_columns": "DATASET 없음", "status": "FAIL"}
            )
            continue
        missing = sorted(required - set(datasets[name].columns))
        rows.append(
            {
                "dataset": name,
                "required_count": len(required),
                "missing_columns": ", ".join(missing) if missing else "-",
                "status": "FAIL" if missing else "PASS",
            }
        )
    return pd.DataFrame(rows)


def validate_primary_keys(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, key in PRIMARY_KEYS.items():
        if name not in datasets or key not in datasets[name].columns:
            rows.append({"dataset": name, "primary_key": key, "missing": None, "duplicates": None, "status": "FAIL"})
            continue
        series = datasets[name][key]
        missing = int(series.isna().sum())
        duplicates = int(series.duplicated().sum())
        rows.append(
            {
                "dataset": name,
                "primary_key": key,
                "missing": missing,
                "duplicates": duplicates,
                "status": "PASS" if not missing and not duplicates else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def validate_relationship_keys(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for child, child_key, parent, parent_key in RELATIONSHIPS:
        label = f"{child}.{child_key} -> {parent}.{parent_key}"
        if (
            child not in datasets
            or parent not in datasets
            or child_key not in datasets[child].columns
            or parent_key not in datasets[parent].columns
        ):
            rows.append({"relationship": label, "parent_key_unique": None, "fk_missing": None, "orphan_rows": None, "status": "FAIL"})
            continue
        parent_values = datasets[parent][parent_key]
        child_values = datasets[child][child_key]
        parent_unique = bool(parent_values.is_unique and parent_values.notna().all())
        fk_missing = int(child_values.isna().sum())
        orphan_rows = int((~child_values.dropna().isin(parent_values)).sum())
        rows.append(
            {
                "relationship": label,
                "parent_key_unique": parent_unique,
                "fk_missing": fk_missing,
                "orphan_rows": orphan_rows,
                "status": "PASS" if parent_unique and not fk_missing and not orphan_rows else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def assert_validation_ready(*checks: pd.DataFrame) -> None:
    """Fail-fast when any schema / key check failed."""
    failed = [check.loc[check["status"].eq("FAIL")] for check in checks if (check["status"] == "FAIL").any()]
    if failed:
        raise ValueError("스키마/키 검증 실패:\n" + "\n".join(f.to_string(index=False) for f in failed))


# ---------------------------------------------------------------------------
# 2. merge / completed 집계 / 총합 대조
# ---------------------------------------------------------------------------
def _require_unique(df: pd.DataFrame, key: str, name: str) -> None:
    if key not in df.columns:
        raise KeyError(f"{name}.{key} 컬럼이 없습니다.")
    if df[key].isna().any() or df[key].duplicated().any():
        raise ValueError(f"{name}.{key}가 고유하지 않거나 결측이 있습니다.")


def _completed_item_lines(order_items: pd.DataFrame, orders: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Merge order_items with orders (many_to_one, indicator) and keep completed only."""
    _require_unique(orders, "order_id", "orders")
    items = order_items.copy()
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce")
    items["unit_price"] = pd.to_numeric(items["unit_price"], errors="coerce")
    items["line_total"] = pd.to_numeric(items["line_total"], errors="coerce")
    mismatch = int((items["line_total"] - items["quantity"] * items["unit_price"]).abs().gt(1e-6).sum())

    merged = items.merge(
        orders[["order_id", "order_date", "order_status"]],
        on="order_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    unmatched = int(merged["_merge"].ne("both").sum())
    merged["order_date"] = pd.to_datetime(merged["order_date"], errors="coerce")
    date_failures = int(merged["order_date"].isna().sum())
    completed = merged.loc[merged["order_status"].eq("completed")].drop(columns="_merge").copy()

    checks = [
        {"check": "orders.order_id 고유성", "value": True, "status": "PASS"},
        {"check": "line_total = quantity x unit_price 불일치 행", "value": mismatch, "status": "PASS" if mismatch == 0 else "FAIL"},
        {"check": "merge 전 order_items 행 수", "value": len(items), "status": "INFO"},
        {"check": "merge 후 행 수 (many_to_one이라 같아야 함)", "value": len(merged), "status": "PASS" if len(merged) == len(items) else "FAIL"},
        {"check": "orders와 매칭되지 않은 행", "value": unmatched, "status": "PASS" if unmatched == 0 else "FAIL"},
        {"check": "order_date 변환 실패", "value": date_failures, "status": "PASS" if date_failures == 0 else "FAIL"},
        {"check": "completed 주문 상세 행 수", "value": len(completed), "status": "INFO"},
        {"check": "completed 외 상태가 섞였는가", "value": int(completed["order_status"].ne("completed").sum()), "status": "PASS"},
    ]
    return completed, checks


def source_completed_total(order_items: pd.DataFrame, orders: pd.DataFrame) -> int:
    completed_orders = orders.loc[orders["order_status"].eq("completed"), "order_id"]
    return int(order_items.loc[order_items["order_id"].isin(completed_orders), "line_total"].sum())


def safe_category_sales(
    order_items: pd.DataFrame, products: pd.DataFrame, orders: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """completed 주문의 카테고리별 line_total 합계와 그 검증 결과."""
    _require_unique(products, "product_id", "products")
    completed, checks = _completed_item_lines(order_items, orders)

    before = len(completed)
    merged = completed.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    unmatched = int(merged["_merge"].ne("both").sum())
    category_missing = int(merged["category"].isna().sum())

    sales = (
        merged.groupby("category", as_index=False)["line_total"]
        .sum()
        .rename(columns={"line_total": "sales"})
        .sort_values("sales", ascending=False)
        .reset_index(drop=True)
    )
    source_total = source_completed_total(order_items, orders)
    grouped_total = int(sales["sales"].sum())

    checks += [
        {"check": "products merge 전 completed 행 수", "value": before, "status": "INFO"},
        {"check": "products merge 후 행 수", "value": len(merged), "status": "PASS" if len(merged) == before else "FAIL"},
        {"check": "products와 매칭되지 않은 행", "value": unmatched, "status": "PASS" if unmatched == 0 else "FAIL"},
        {"check": "category 결측", "value": category_missing, "status": "PASS" if category_missing == 0 else "FAIL"},
        {"check": "source total (completed line_total 합)", "value": source_total, "status": "INFO"},
        {"check": "category grouped total", "value": grouped_total, "status": "PASS" if grouped_total == source_total else "FAIL"},
    ]
    return sales, pd.DataFrame(checks)


def safe_monthly_sales(order_items: pd.DataFrame, orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """completed 주문의 월별 line_total 합계와 그 검증 결과."""
    completed, checks = _completed_item_lines(order_items, orders)
    completed["order_month"] = completed["order_date"].dt.to_period("M").astype(str)
    sales = (
        completed.groupby("order_month", as_index=False)["line_total"]
        .sum()
        .rename(columns={"line_total": "sales"})
        .sort_values("order_month")
        .reset_index(drop=True)
    )
    source_total = source_completed_total(order_items, orders)
    grouped_total = int(sales["sales"].sum())
    checks += [
        {"check": "source total (completed line_total 합)", "value": source_total, "status": "INFO"},
        {"check": "monthly grouped total", "value": grouped_total, "status": "PASS" if grouped_total == source_total else "FAIL"},
    ]
    return sales, pd.DataFrame(checks)


def reconcile_totals(source_total: int, category_total: int, monthly_total: int) -> pd.DataFrame:
    ok = source_total == category_total == monthly_total
    return pd.DataFrame(
        [
            {"item": "completed source total", "amount": source_total},
            {"item": "category grouped total", "amount": category_total},
            {"item": "monthly grouped total", "amount": monthly_total},
            {"item": "세 값이 모두 같은가", "amount": "PASS" if ok else "FAIL"},
        ]
    )


# ---------------------------------------------------------------------------
# 3. AST Static Scan (코드를 실행하지 않고 읽기만 한다)
# ---------------------------------------------------------------------------
DEFAULT_STATIC_SCAN_EXAMPLE = '''import pandas as pd
import requests

API_KEY = "sk-example-not-a-real-key"

orders = pd.read_csv("data/processed/orders_clean.csv")
summary = orders.groupby("order_status").size().reset_index(name="count")
summary.to_csv("reports/order_status_summary.csv", index=False)

requests.post(
    "https://example.com/upload",
    json=summary.to_dict("records"),
    headers={"Authorization": API_KEY},
)
'''

SEVERITY_ORDER = {"critical": 3, "high": 2, "review": 1}

DYNAMIC_EXEC_CALLS = {"eval", "exec", "compile", "__import__"}
SHELL_CALLS = {"os.system", "os.popen", "os.startfile"}
NETWORK_MODULES = {"requests", "urllib", "urllib3", "http", "socket", "ftplib", "smtplib", "httpx", "aiohttp"}
DESTRUCTIVE_CALLS = {
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "os.rename",
    "os.replace",
    "shutil.rmtree",
    "shutil.move",
    "shutil.copy",
    "shutil.copyfile",
}
WRITE_METHODS = {"to_csv", "to_excel", "to_parquet", "to_json", "to_pickle", "to_sql", "write_text", "write_bytes", "savefig"}
SECRET_NAME_HINTS = ("api_key", "apikey", "token", "password", "passwd", "secret", "credential")


def _dotted_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _open_mode(call: ast.Call) -> str | None:
    mode_node = None
    if len(call.args) >= 2:
        mode_node = call.args[1]
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode_node = keyword.value
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return mode_node.value
    return None


def scan_generated_code(code: str) -> pd.DataFrame:
    """Scan code text with ast. The code is NEVER executed."""
    findings: list[dict] = []

    def add(node: ast.AST, rule: str, severity: str, detail: str) -> None:
        findings.append(
            {"line": getattr(node, "lineno", 0), "rule": rule, "severity": severity, "detail": detail}
        )

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return pd.DataFrame(
            [{"line": error.lineno or 0, "rule": "syntax_error", "severity": "high", "detail": str(error)}]
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in NETWORK_MODULES:
                    add(node, "network_import", "high", f"네트워크 모듈 import: {alias.name}")
                if alias.name.split(".")[0] in {"subprocess", "ensurepip", "pip"}:
                    add(node, "process_or_install_import", "high", f"프로세스/설치 모듈 import: {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in NETWORK_MODULES:
                add(node, "network_import", "high", f"네트워크 모듈 import: {node.module}")
            if top in {"subprocess", "ensurepip", "pip"}:
                add(node, "process_or_install_import", "high", f"프로세스/설치 모듈 import: {node.module}")
        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            short = name.split(".")[-1]
            if name in DYNAMIC_EXEC_CALLS:
                add(node, "dynamic_execution", "critical", f"{name}() 호출")
            elif name in SHELL_CALLS or name.startswith("subprocess."):
                add(node, "shell_or_subprocess", "critical", f"{name}() 호출")
            elif name.split(".")[0] in NETWORK_MODULES:
                add(node, "network_request", "high", f"{name}() 호출")
            elif name in DESTRUCTIVE_CALLS:
                add(node, "file_delete_or_replace", "high", f"{name}() 호출")
            elif name == "open":
                mode = _open_mode(node)
                if mode and any(flag in mode for flag in "wax+"):
                    add(node, "file_write", "review", f"open(..., '{mode}') 파일 쓰기")
            elif short in WRITE_METHODS:
                add(node, "file_write", "review", f".{short}() 파일 저장")
            if any(
                isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.strip().lower() in {"pip", "ensurepip"}
                for arg in node.args
            ):
                add(node, "package_install", "high", "pip/ensurepip 실행 인자")
        elif isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value.strip():
                for target in node.targets:
                    target_name = _dotted_name(target).lower()
                    if any(hint in target_name for hint in SECRET_NAME_HINTS):
                        add(node, "hardcoded_secret", "critical", f"{target_name}에 문자열 값이 직접 들어 있음")

    columns = ["line", "rule", "severity", "detail"]
    if not findings:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(findings, columns=columns).sort_values(["line", "rule"]).reset_index(drop=True)


def summarize_static_scan(scan: pd.DataFrame) -> str:
    """BLOCKED / REVIEW. 0 findings is REVIEW, never SAFE."""
    if scan.empty:
        return "REVIEW"
    if scan["severity"].isin(["critical", "high"]).any():
        return "BLOCKED"
    return "REVIEW"


# ---------------------------------------------------------------------------
# 4. 회귀 / 분류 Feature Contract
# ---------------------------------------------------------------------------
LEAKAGE_CONTRACT = {
    "regression": {
        "FORBIDDEN": {
            "order_total": "예측 대상 자체",
            "line_total": "금액 정보가 곧 정답(order_total의 재료)",
            "quantity": "금액 계산의 재료라 정답을 간접 노출",
            "unit_price": "금액 계산의 재료라 정답을 간접 노출",
            "item_count": "주문 상세에서 만든 집계라 금액과 직접 연결",
            "total_quantity": "주문 상세에서 만든 집계라 금액과 직접 연결",
            "avg_unit_price": "금액에서 파생된 값",
            "order_status": "주문 이후에 확정되는 상태",
            "order_id": "식별자",
            "customer_id": "식별자",
            "product_id": "식별자",
        },
        "ALLOWED": {
            "payment_method": "주문 시점에 확정",
            "order_month": "주문 시점에 확정",
            "order_dayofweek": "주문 시점에 확정",
            "gender": "고객 비식별 특성",
            "age": "고객 비식별 특성",
            "city": "고객 비식별 특성",
        },
        "REVIEW": {},
    },
    "classification": {
        "FORBIDDEN": {
            "order_status": "Target을 그대로 담은 사후 정보",
            "is_cancelled": "예측 대상 자체",
            "order_id": "식별자",
            "customer_id": "식별자",
            "product_id": "식별자",
            "line_total": "row-level 금액(주문 단위 예측에는 집계값만 검토)",
            "quantity": "row-level 수량",
            "unit_price": "row-level 단가",
            "cancel_reason": "취소가 확정된 뒤에만 존재",
            "cancelled_at": "취소가 확정된 뒤에만 존재",
        },
        "ALLOWED": {
            "payment_method": "주문 시점에 확정",
            "order_month": "주문 시점에 확정",
            "order_dayofweek": "주문 시점에 확정",
            "gender": "고객 비식별 특성",
            "age": "고객 비식별 특성",
            "city": "고객 비식별 특성",
        },
        "REVIEW": {
            "item_count": "주문 생성 시 이미 확정된다는 가정이 맞는지 확인 필요",
            "total_quantity": "주문 생성 시 이미 확정된다는 가정이 맞는지 확인 필요",
            "order_amount": "주문 생성 시 이미 확정된다는 가정이 맞는지 확인 필요",
            "category_count": "장바구니 집계, 예측 시점에 확정된다는 가정 확인 필요",
            "dominant_category": "장바구니 집계, 예측 시점에 확정된다는 가정 확인 필요",
            "customer_tenure_days": "가입일이 주문일보다 늦은 행이 있어 그대로 쓰면 미래 정보 누수 가능",
        },
    },
}


def build_leakage_review_table() -> pd.DataFrame:
    rows = []
    for problem, groups in LEAKAGE_CONTRACT.items():
        for status, features in groups.items():
            for feature, reason in features.items():
                rows.append({"problem": problem, "feature": feature, "status": status, "reason": reason})
    return pd.DataFrame(rows)


def read_feature_columns_from_source(path: str | Path) -> list[str]:
    """Read NUMERIC_FEATURES + CATEGORICAL_FEATURES list literals from a .py file with ast.

    The module is parsed, not imported or executed.
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"NUMERIC_FEATURES", "CATEGORICAL_FEATURES"}:
                found[name] = list(ast.literal_eval(node.value))
    missing = {"NUMERIC_FEATURES", "CATEGORICAL_FEATURES"} - set(found)
    if missing:
        raise ValueError(f"{path}에서 찾지 못한 상수: {sorted(missing)}")
    return found["NUMERIC_FEATURES"] + found["CATEGORICAL_FEATURES"]


def build_feature_audit(features: Iterable[str], problem: str) -> pd.DataFrame:
    if problem not in LEAKAGE_CONTRACT:
        raise ValueError(f"problem은 {sorted(LEAKAGE_CONTRACT)} 중 하나여야 합니다: {problem}")
    contract = LEAKAGE_CONTRACT[problem]
    rows = []
    for feature in features:
        for status in ("FORBIDDEN", "REVIEW", "ALLOWED"):
            if feature in contract[status]:
                rows.append({"feature": feature, "status": status, "reason": contract[status][feature]})
                break
        else:
            rows.append({"feature": feature, "status": "UNKNOWN", "reason": "계약에 없는 feature, 예측 시점을 직접 확인해야 함"})
    return pd.DataFrame(rows)


def validate_feature_list(features: Iterable[str], problem: str) -> bool:
    """Raise when a forbidden feature is used. REVIEW/UNKNOWN stay visible in the audit."""
    features = list(features)
    audit = build_feature_audit(features, problem)
    forbidden = audit.loc[audit["status"].eq("FORBIDDEN"), "feature"].tolist()
    if forbidden:
        raise ValueError(f"{problem} 문제에서 금지된 feature가 있습니다: {forbidden}")
    duplicates = pd.Index(features)[pd.Index(features).duplicated()].tolist()
    if duplicates:
        raise ValueError(f"중복 feature가 있습니다: {duplicates}")
    return True


# ---------------------------------------------------------------------------
# 5. LLM에게 다시 물을 때 쓰는 최소 Context Prompt
# ---------------------------------------------------------------------------
def build_error_fix_prompt_template() -> str:
    return """# 오류 수정 요청 Prompt (최소 Context)

## 분석 목적
(한 문장)

## 필요한 최소 데이터 구조
- dataset 이름과 필요한 컬럼명만 적습니다. 고객 원본 행은 붙이지 않습니다.

## 오류를 재현하는 최소 코드
(문자열 literal / URL / 경로에 개인정보·Secret이 없는지 다시 확인)

## 오류 메시지
(사용자명, 절대 경로, 내부 URL, 토큰을 지운 뒤 붙입니다)

## 검증 Evidence
- merge 전후 행 수:
- 미매칭 수:
- source total과 grouped total 차이:

## 공유하지 않는 것
고객 원본 행, API Key, Token, DB password, 내부 URL, 개인 사용자 경로, 전체 환경변수, 민감 설정 파일
"""


# ---------------------------------------------------------------------------
# 6. Evidence 이미지 (코드로 그린 표/로그 화면)
# ---------------------------------------------------------------------------
DARK_THEME = {
    "background": "#1e1e1e",
    "panel": "#252526",
    "text": "#d4d4d4",
    "header": "#37373d",
    "accent": "#569cd6",
    "pass": "#4ec9b0",
    "warn": "#dcdcaa",
    "fail": "#f48771",
}


def _korean_font() -> str | None:
    from matplotlib import font_manager

    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"]:
        if name in available:
            return name
    return None


def _status_color(value: str) -> str:
    text = str(value)
    if text in {"PASS", "APPROVE", "OK"}:
        return DARK_THEME["pass"]
    if text in {"FAIL", "BLOCKED", "BLOCK", "critical", "high", "DO_NOT_EXECUTE"}:
        return DARK_THEME["fail"]
    if text in {"REVIEW", "REVISE", "review", "HUMAN_REVIEW_REQUIRED", "PENDING"}:
        return DARK_THEME["warn"]
    return DARK_THEME["text"]


def save_dataframe_image(df: pd.DataFrame, path: str | Path, title: str) -> Path:
    """Draw a DataFrame as a dark (editor-like) table image. Values come straight from df."""
    import matplotlib.pyplot as plt

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    font = _korean_font()
    if font:
        plt.rcParams["font.family"] = font
        plt.rcParams["axes.unicode_minus"] = False

    table_df = df.astype(str)
    width = min(max(8, 1.6 * len(table_df.columns) + 0.14 * table_df.map(len).max().sum() / max(len(table_df.columns), 1)), 18)
    height = 0.9 + 0.3 * (len(table_df) + 1)
    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_THEME["background"])
    ax.axis("off")
    ax.set_title(title, color=DARK_THEME["accent"], loc="left", fontsize=12, pad=10)

    table = ax.table(
        cellText=table_df.values.tolist(),
        colLabels=list(table_df.columns),
        cellLoc="left",
        loc="upper left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.35)
    table.auto_set_column_width(col=list(range(len(table_df.columns))))
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#3c3c3c")
        if row == 0:
            cell.set_facecolor(DARK_THEME["header"])
            cell.get_text().set_color(DARK_THEME["accent"])
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor(DARK_THEME["panel"])
            cell.get_text().set_color(_status_color(table_df.iloc[row - 1, col]))
    fig.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def save_text_image(text: str, path: str | Path, title: str) -> Path:
    """Draw real captured text (terminal-like log) as a dark image."""
    import matplotlib.pyplot as plt

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    font = _korean_font()
    if font:
        plt.rcParams["font.family"] = font
        plt.rcParams["axes.unicode_minus"] = False

    lines = text.rstrip("\n").splitlines() or [""]
    width = min(max(8, 0.095 * max(len(line) for line in lines) + 1), 18)
    height = 0.9 + 0.27 * len(lines)
    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_THEME["background"])
    ax.axis("off")
    ax.set_title(title, color=DARK_THEME["accent"], loc="left", fontsize=12, pad=10)
    ax.text(
        0,
        1,
        "\n".join(lines),
        va="top",
        ha="left",
        color=DARK_THEME["text"],
        family=["Consolas", font or "DejaVu Sans Mono"],
        fontsize=10,
        transform=ax.transAxes,
        linespacing=1.4,
    )
    fig.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output
