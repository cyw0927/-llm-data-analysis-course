"""Chapter 14-1 로컬 자동화: 각 단계 실패 시 즉시 중단."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOGS = BASE / "logs"
STEPS = [
    "src/collect_naver.py",
    "src/collect_tourism.py",
    "src/analyze.py",
    "src/generate_llm_report.py",
    "src/generate_pdf.py",
]


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LOGS / f"pipeline_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()],
    )
    logging.info("PIPELINE START")
    for script in STEPS:
        logging.info("START %s", script)
        result = subprocess.run(
            [sys.executable, script], cwd=BASE, check=False,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        if result.returncode:
            logging.error("FAIL %s: exit=%d; 후속 단계 실행 중단", script, result.returncode)
            raise SystemExit(result.returncode)
        logging.info("PASS %s", script)
    logging.info("PIPELINE SUCCESS")
    print("로그:", path)
    print("주의: 실행 PASS 외에 PDF 화면과 LLM 숫자·문장 사람 검증이 필요합니다.")


if __name__ == "__main__":
    main()
