"""Chapter 12 execution policy: Execution Gate, sandbox/package review, limited run.

The automatic gate can only say DO_NOT_EXECUTE or HUMAN_REVIEW_REQUIRED.
It never produces an EXECUTE state; approval is a human decision recorded in
the revision log.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.llm_code_validation import (
    DATASET_FILES,
    DEFAULT_STATIC_SCAN_EXAMPLE,
    assert_validation_ready,
    build_dataset_inventory,
    build_error_fix_prompt_template,
    build_feature_audit,
    build_leakage_review_table,
    load_validation_data,
    reconcile_totals,
    safe_category_sales,
    safe_monthly_sales,
    scan_generated_code,
    source_completed_total,
    summarize_static_scan,
    validate_primary_keys,
    validate_relationship_keys,
    validate_required_columns,
)


DEFAULT_FEATURE_LISTS = {
    "regression": ["payment_method", "order_month", "order_dayofweek", "gender", "age", "city"],
    "classification": ["payment_method", "item_count", "total_quantity", "order_amount", "age", "city"],
}

SANDBOX_CHECKLIST_ITEMS = [
    ("복사한 소량 샘플만 사용", "운영 데이터가 아니라 복사본인지 확인"),
    ("input read-only 적용", "입력 파일이 읽기 전용으로 바뀌었는지 확인"),
    ("API Key / DB password / cloud credential 없음", "실행 환경 변수에 Secret이 없는지 확인"),
    ("disposable environment", "실행 후 지워도 되는 폴더인지 확인"),
    ("쓰기 경로 allowlist", "output 폴더 밖에 쓰기가 없는지 확인"),
    ("network deny by default", "네트워크 호출 코드가 없는지, OS 수준 차단이 되는지 확인"),
    ("CPU / memory / timeout / process / disk limit", "어떤 제한을 실제로 걸었는지 확인"),
    ("실행 전 baseline 기록", "실행 전 파일 목록/hash/크기 저장"),
    ("실행 후 변경 비교", "실행 후 생성/수정/삭제 파일 비교"),
]

PACKAGE_REVIEW_ITEMS = [
    "정말 필요한가?",
    "공식 package 이름과 source인가?",
    "typosquatting 위험은 없는가?",
    "exact version을 고정했는가?",
    "Python 호환성을 확인했는가?",
    "transitive dependency를 검토했는가?",
    "install script를 검토했는가?",
    "격리 환경인가?",
    "requirements / lock에 기록하는가?",
    "조직 정책에 맞는가?",
]

REVIEW_CHECKLIST_ITEMS = [
    "Generated Code를 실행 전에 읽었는가?",
    "processed 입력에서 시작했는가?",
    "필수 컬럼 / PK / FK를 확인했는가?",
    "merge validate / 행 수 / 미매칭을 확인했는가?",
    "line_total = quantity x unit_price를 검증했는가?",
    "completed 범위를 유지했는가?",
    "source total과 grouped total을 대조했는가?",
    "AST Static Scan을 실행했는가?",
    "회귀/분류 Feature Contract를 구분했는가?",
    "Sandbox와 Package 위험을 검토했는가?",
    "사람이 APPROVE / REVISE / BLOCK을 판단했는가?",
    "실행 후 파일/행 수/총합/범위를 다시 검증했는가?",
]


def build_sandbox_execution_checklist() -> pd.DataFrame:
    """All items start as REVIEW. A human changes them after checking real evidence."""
    return pd.DataFrame(
        [{"item": item, "what_to_check": note, "status": "REVIEW"} for item, note in SANDBOX_CHECKLIST_ITEMS]
    )


def build_package_install_review() -> pd.DataFrame:
    frame = pd.DataFrame([{"question": q, "status": "REVIEW"} for q in PACKAGE_REVIEW_ITEMS])
    frame["initial_decision"] = "DO_NOT_INSTALL_UNTIL_REVIEWED"
    return frame


def build_llm_code_review_checklist() -> pd.DataFrame:
    return pd.DataFrame([{"check_item": item, "status": "REVIEW"} for item in REVIEW_CHECKLIST_ITEMS])


def build_human_revision_log(entries: list[dict] | None = None, execution_approved: bool = False) -> pd.DataFrame:
    """Human revision log. execution_approved stays False until a human approves."""
    if not entries:
        entries = [
            {
                "item": "(아직 검토 전)",
                "llm_draft": "-",
                "human_revision": "-",
                "reason": "-",
            }
        ]
    frame = pd.DataFrame(entries)
    frame["execution_approved"] = execution_approved
    return frame


def evaluate_feature_contracts(feature_lists: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Audit each feature list. FORBIDDEN -> FAIL, REVIEW/UNKNOWN -> REVIEW, otherwise PASS."""
    feature_lists = feature_lists or DEFAULT_FEATURE_LISTS
    audits = []
    for problem, features in feature_lists.items():
        audit = build_feature_audit(features, problem)
        audit.insert(0, "problem", problem)
        audits.append(audit)
    return pd.concat(audits, ignore_index=True)


def build_execution_gate(
    schema_status: str,
    aggregate_status: str,
    leakage_status: str,
    static_scan_status: str,
    sandbox_status: str,
    evidence: dict[str, str] | None = None,
) -> pd.DataFrame:
    evidence = evidence or {}
    rows = [
        ("schema_and_keys", schema_status),
        ("aggregate_validation", aggregate_status),
        ("ml_leakage", leakage_status),
        ("static_scan", static_scan_status),
        ("sandbox_and_package", sandbox_status),
        ("human_approval", "PENDING"),
    ]
    blocked = any(status in {"FAIL", "BLOCKED"} for _, status in rows)
    decision = "DO_NOT_EXECUTE" if blocked else "HUMAN_REVIEW_REQUIRED"
    rows.append(("execution_decision", decision))
    return pd.DataFrame(
        [{"axis": axis, "status": status, "evidence": evidence.get(axis, "")} for axis, status in rows]
    )


def _all_pass(checks: pd.DataFrame) -> bool:
    return not checks["status"].eq("FAIL").any()


def run_llm_code_validation(
    processed_dir: str | Path = "data/processed",
    report_dir: str | Path = "reports",
    generated_code: str = DEFAULT_STATIC_SCAN_EXAMPLE,
    code_label: str = "DEFAULT_STATIC_SCAN_EXAMPLE",
    feature_lists: dict[str, list[str]] | None = None,
    revision_entries: list[dict] | None = None,
    execution_approved: bool = False,
) -> dict[str, object]:
    """Build every Chapter 12 evidence file. The scanned code is never executed."""
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    datasets = load_validation_data(processed_dir)
    inventory = build_dataset_inventory(datasets)
    required_check = validate_required_columns(datasets)
    primary_key_check = validate_primary_keys(datasets)
    relationship_check = validate_relationship_keys(datasets)
    schema_ok = all(_all_pass(check) for check in [required_check, primary_key_check, relationship_check])

    outputs: dict[str, pd.DataFrame] = {
        "dataset_inventory": inventory,
        "required_column_check": required_check,
        "primary_key_check": primary_key_check,
        "relationship_key_check": relationship_check,
    }

    aggregate_ok = False
    if schema_ok:
        assert_validation_ready(required_check, primary_key_check, relationship_check)
        category_sales, category_validation = safe_category_sales(
            datasets["order_items"], datasets["products"], datasets["orders"]
        )
        monthly_sales, monthly_validation = safe_monthly_sales(datasets["order_items"], datasets["orders"])
        aggregate_ok = _all_pass(category_validation) and _all_pass(monthly_validation)
        outputs.update(
            {
                "category_sales_validated": category_sales,
                "category_sales_validation": category_validation,
                "monthly_sales_validated": monthly_sales,
                "monthly_sales_validation": monthly_validation,
            }
        )

    leakage_review = build_leakage_review_table()
    feature_audit = evaluate_feature_contracts(feature_lists)
    if feature_audit["status"].eq("FORBIDDEN").any():
        leakage_status = "FAIL"
    elif feature_audit["status"].isin(["REVIEW", "UNKNOWN"]).any():
        leakage_status = "REVIEW"
    else:
        leakage_status = "PASS"
    outputs["ml_leakage_review"] = leakage_review
    outputs["ml_feature_audit"] = feature_audit

    static_scan = scan_generated_code(generated_code)
    static_status = summarize_static_scan(static_scan)
    outputs["generated_code_static_scan"] = static_scan

    sandbox_checklist = build_sandbox_execution_checklist()
    package_review = build_package_install_review()
    sandbox_status = "REVIEW" if sandbox_checklist["status"].eq("REVIEW").any() else "PASS"
    outputs["sandbox_execution_checklist"] = sandbox_checklist
    outputs["package_install_review"] = package_review

    evidence = {
        "schema_and_keys": "필수 컬럼/PK/FK 검증" + (" 통과" if schema_ok else " 실패"),
        "aggregate_validation": "source total = category total = monthly total" if aggregate_ok else "집계 검증 실패 또는 미실행",
        "ml_leakage": f"FORBIDDEN {int(feature_audit['status'].eq('FORBIDDEN').sum())}건 / REVIEW {int(feature_audit['status'].isin(['REVIEW', 'UNKNOWN']).sum())}건",
        "static_scan": f"{code_label}: findings {len(static_scan)}건",
        "sandbox_and_package": "체크리스트 전 항목 REVIEW (자동으로 PASS 만들지 않음)",
        "human_approval": "사람 승인 전",
    }
    gate = build_execution_gate(
        schema_status="PASS" if schema_ok else "FAIL",
        aggregate_status="PASS" if aggregate_ok else "FAIL",
        leakage_status=leakage_status,
        static_scan_status=static_status,
        sandbox_status=sandbox_status,
        evidence=evidence,
    )
    outputs["execution_gate"] = gate
    outputs["human_revision_log"] = build_human_revision_log(revision_entries, execution_approved)
    outputs["llm_code_review_checklist"] = build_llm_code_review_checklist()

    paths: dict[str, Path] = {}
    for name, frame in outputs.items():
        path = report_path / f"ch12_{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[name] = path

    prompt_path = report_path / "ch12_error_fix_prompt_template.md"
    prompt_path.write_text(build_error_fix_prompt_template(), encoding="utf-8")
    paths["error_fix_prompt_template"] = prompt_path

    decision = gate.loc[gate["axis"].eq("execution_decision"), "status"].iloc[0]
    summary_path = report_path / "ch12_code_validation_summary.md"
    summary_path.write_text(
        f"""# Chapter 12 코드 검증 요약

- 검사한 코드: `{code_label}` (실행하지 않고 AST로만 읽음)
- 입력: `{Path(processed_dir).as_posix()}` (raw fallback 없음)

## Execution Gate
```text
{gate.to_string(index=False)}
```

## 정적 스캔 결과
```text
{static_scan.to_string(index=False) if not static_scan.empty else '(findings 0건 - SAFE가 아니라 REVIEW)'}
```

최종 자동 판정: **{decision}**
(DO_NOT_EXECUTE는 자동화 실패가 아니라 검사한 코드에 차단 사유가 있다는 뜻입니다.)
""",
        encoding="utf-8",
    )
    paths["code_validation_summary"] = summary_path

    return {"datasets": datasets, "outputs": outputs, "paths": paths, "decision": decision}


# ---------------------------------------------------------------------------
# 제한 실행 (승인된 코드만) + 실행 후 검증
# ---------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_files(root: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(
                {"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": _sha256(path)}
            )
    return pd.DataFrame(rows, columns=["path", "size", "sha256"])


def _force_remove(function, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def diff_snapshots(before: pd.DataFrame, after: pd.DataFrame, allowed_prefix: str = "output/") -> pd.DataFrame:
    before_map = before.set_index("path")["sha256"].to_dict()
    after_map = after.set_index("path")["sha256"].to_dict()
    rows = []
    for path in sorted(set(before_map) | set(after_map)):
        if path not in before_map:
            change = "created"
        elif path not in after_map:
            change = "deleted"
        elif before_map[path] != after_map[path]:
            change = "modified"
        else:
            continue
        rows.append({"path": path, "change": change, "inside_allowed_path": path.startswith(allowed_prefix)})
    return pd.DataFrame(rows, columns=["path", "change", "inside_allowed_path"])


def run_in_limited_sandbox(
    code_path: str | Path,
    processed_dir: str | Path,
    sandbox_dir: str | Path,
    timeout_sec: int = 60,
) -> dict[str, object]:
    """Run ONE approved script inside a disposable copy with limits that are actually applied.

    Applied limits: copied data only, read-only inputs, stripped environment (no secrets),
    cwd = sandbox, timeout, baseline/after file hash comparison.
    Not applied: OS-level network blocking, CPU/memory caps (documented as a limitation).
    """
    sandbox = Path(sandbox_dir)
    if sandbox.exists():
        shutil.rmtree(sandbox, onerror=_force_remove)
    (sandbox / "data" / "processed").mkdir(parents=True)
    (sandbox / "output").mkdir()

    shutil.copy(code_path, sandbox / "approved_code.py")
    for file_name in DATASET_FILES.values():
        target = sandbox / "data" / "processed" / file_name
        shutil.copy(Path(processed_dir) / file_name, target)
        os.chmod(target, stat.S_IREAD)

    baseline = snapshot_files(sandbox)

    safe_env = {
        key: os.environ[key]
        for key in ("SYSTEMROOT", "SystemRoot", "PATH", "TEMP", "TMP", "APPDATA")
        if key in os.environ
    }
    safe_env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    leaked_secret_names = [name for name in safe_env if any(h in name.lower() for h in ("key", "token", "secret", "password"))]

    started = datetime.now()
    timer = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            [sys.executable, "approved_code.py"],
            cwd=sandbox,
            env=safe_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_sec,
        )
        exit_code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        exit_code, stdout, stderr = -1, error.stdout or "", error.stderr or ""
    elapsed = time.perf_counter() - timer
    finished = datetime.now()

    after = snapshot_files(sandbox)
    changes = diff_snapshots(baseline, after)

    run_info = pd.DataFrame(
        [
            ("실행 대상 코드", Path(code_path).name),
            ("실행 대상 sha256", _sha256(Path(code_path))[:16]),
            ("Python", sys.version.split()[0]),
            ("pandas", pd.__version__),
            ("sandbox 폴더", sandbox.name),
            ("입력 파일 수 / read-only", f"{len(DATASET_FILES)}개 / 적용"),
            ("환경변수 전달", ", ".join(sorted(safe_env))),
            ("Secret 이름 환경변수", ", ".join(leaked_secret_names) if leaked_secret_names else "없음"),
            ("timeout 설정(초)", timeout_sec),
            ("시작 시각", started.strftime("%Y-%m-%d %H:%M:%S")),
            ("종료 시각", finished.strftime("%Y-%m-%d %H:%M:%S")),
            ("소요 시간(초)", round(elapsed, 2)),
            ("exit code", exit_code),
            ("timeout 발생", timed_out),
        ],
        columns=["항목", "값"],
    )
    return {
        "run_info": run_info,
        "baseline": baseline,
        "after": after,
        "changes": changes,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "sandbox": sandbox,
    }


def post_execution_validation(
    run_result: dict[str, object],
    datasets: dict[str, pd.DataFrame],
    output_name: str = "category_sales.csv",
) -> pd.DataFrame:
    """Re-validate AFTER the run with an independent recomputation (not the revised script's code)."""
    sandbox = Path(run_result["sandbox"])
    changes: pd.DataFrame = run_result["changes"]
    output_path = sandbox / "output" / output_name
    rows: list[dict] = []

    def add(check: str, value, ok: bool | None, note: str = "") -> None:
        status = "INFO" if ok is None else ("PASS" if ok else "FAIL")
        rows.append({"check": check, "value": value, "status": status, "note": note})

    add("exit code 0 / timeout 없음", f"{run_result['exit_code']} / {run_result['timed_out']}", run_result["exit_code"] == 0 and not run_result["timed_out"])

    created = changes.loc[changes["change"].eq("created"), "path"].tolist()
    add("생성된 파일이 예상 출력 1개뿐인가", ", ".join(created) or "없음", created == [f"output/{output_name}"])
    add(
        "수정/삭제된 파일 또는 허용 경로 밖 변경",
        int((~changes["inside_allowed_path"]).sum()) if not changes.empty else 0,
        changes.empty or bool(changes["inside_allowed_path"].all()),
        "0이어야 원본 입력이 보존됨",
    )

    inputs_unchanged = bool(
        run_result["baseline"].query("path.str.startswith('data/')", engine="python").reset_index(drop=True).equals(
            run_result["after"].query("path.str.startswith('data/')", engine="python").reset_index(drop=True)
        )
    )
    add("입력 파일 hash가 실행 전후 같은가", inputs_unchanged, inputs_unchanged)

    if output_path.exists():
        produced = pd.read_csv(output_path)
        orders, items, products = datasets["orders"], datasets["order_items"], datasets["products"]
        completed_ids = set(orders.loc[orders["order_status"].eq("completed"), "order_id"])
        completed_items = items[items["order_id"].isin(completed_ids)]
        category_by_product = products.set_index("product_id")["category"]
        expected = (
            completed_items.assign(category=completed_items["product_id"].map(category_by_product))
            .groupby("category")["line_total"]
            .sum()
        )
        source_total = source_completed_total(items, orders)

        add("입력 completed 주문 상세 행 수", len(completed_items), None)
        add("출력 행 수 (카테고리 수)", len(produced), len(produced) == len(expected), f"독립 계산: {len(expected)}개")
        add("출력 합계 = source completed total", int(produced["sales"].sum()), int(produced["sales"].sum()) == source_total, f"source={source_total}")
        produced_map = produced.set_index("category")["sales"].to_dict()
        same = produced_map == expected.to_dict()
        add("카테고리별 금액이 독립 계산과 같은가", same, same)
        add("category 결측 없음", int(produced["category"].isna().sum()), int(produced["category"].isna().sum()) == 0)
    else:
        add("출력 파일 존재", False, False)

    log_text = f"{run_result['stdout']}\n{run_result['stderr']}".lower()
    leaked = [word for word in ("api_key", "password", "token", "secret", "sk-") if word in log_text]
    add("로그에 Secret 흔적이 없는가", ", ".join(leaked) or "없음", not leaked)
    add("외부 네트워크 전송이 없었는가", "정적 스캔상 network 호출 없음", None, "OS 수준 차단은 하지 않아 확정은 못 함 -> REVIEW")
    frame = pd.DataFrame(rows)
    frame.loc[frame["check"].str.startswith("외부 네트워크"), "status"] = "REVIEW"
    return frame
