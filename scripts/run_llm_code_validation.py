"""Chapter 12 evidence runner.

    python scripts/run_llm_code_validation.py

Prerequisite: data/processed/*_clean.csv (no raw fallback).
The default risky example string is only parsed with AST; it is never executed.
"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_code_validation_policy import run_llm_code_validation  # noqa: E402


def main() -> None:
    result = run_llm_code_validation(
        processed_dir=PROJECT_ROOT / "data" / "processed",
        report_dir=PROJECT_ROOT / "reports",
    )
    print("12장 코드 검증 Evidence 생성 완료 (검사 대상 코드는 실행하지 않았습니다)")
    print("\n[Execution Gate]")
    print(result["outputs"]["execution_gate"].to_string(index=False))
    print("\n[정적 스캔]")
    print(result["outputs"]["generated_code_static_scan"].to_string(index=False))
    print("\n[저장된 파일]")
    for name, path in result["paths"].items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
