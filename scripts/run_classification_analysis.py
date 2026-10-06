"""Run the Chapter 10 leakage-aware classification analysis.

Run from the project root or any working directory:

    python scripts/run_classification_analysis.py

Prerequisite:

    python scripts/prepare_ch10_data.py

The workflow selects both the candidate model and the decision threshold using
Validation metrics only, freezes both choices, and only then evaluates the
frozen (model, threshold) pair and a DummyClassifier on the Final Test split.
"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classification import run_classification_analysis  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    """Run the synchronized Chapter 10 classification workflow."""
    result = run_classification_analysis(
        processed_dir=PROCESSED_DIR,
        report_dir=REPORT_DIR,
        test_size=0.2,
        val_size=0.2,
        random_state=42,
    )

    print("10장 분류 분석 완료")

    print("\n[타깃 분포]")
    print(result["target_distribution"].to_string(index=False))

    print("\n[Feature Audit]")
    print(result["feature_audit"].to_string(index=False))

    print("\n[Train / Validation / Test 분할]")
    print(result["split_summary"].to_string(index=False))

    print("\n[Validation 후보 모델 비교]")
    print(result["validation_comparison"].to_string(index=False))

    print("\n[Validation으로 고정한 모델]")
    print(result["selected_model_name"])

    print("\n[Validation으로 고정한 threshold]")
    print(result["selected_threshold"])

    print("\n[Final Test: Baseline vs Frozen Model]")
    print(result["test_metrics"].to_string(index=False))

    print("\n[Confusion Matrix]")
    print(result["confusion"].to_string(index=False))

    print("\n[자동 Validation]")
    print(result["validation"].to_string(index=False))

    print("\n[저장된 결과 파일]")
    for name, path in result["output_paths"].items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
