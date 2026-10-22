"""검증된 계산 결과의 한국어 서술 요약만 LLM에 맡긴다."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"


def build_prompt(summary_records: list[dict]) -> str:
    if not summary_records:
        raise ValueError("LLM에게 보낼 검증된 분석 결과가 없습니다.")
    return (
        "당신은 데이터 분석 보고서 작성 보조자입니다. 다음 수치는 Python에서 계산된 데이터입니다.\n"
        + json.dumps(summary_records, ensure_ascii=False, indent=2)
        + "\n아래 순서대로 간결한 한국어 보고서를 작성하세요:\n"
          "1. 분석 기준 시점과 데이터 출처\n"
          "2. 검색 관심도 특징\n3. 지역 관광 체류/소비 강도 특징\n"
          "4. 함께 관찰되는 패턴\n5. 말할 수 없는 것\n6. 추가 확인 사항\n"
          "반드시 지킬 규칙: NAVER ratio는 실제 검색 건수가 아닌 상대지수. "
          "두 API의 단위·지역·기간이 다르므로 숫자를 직접 비교하거나 인과를 단정하지 말 것. "
          "입력에 없는 숫자·지역·원인·날짜를 만들지 말 것. "
          "출처별 기준 시점과 결측/범위의 한계를 밝힐 것. "
          "period는 수집 시각이 아닌 관측 기준 기간이다. "
          "부분 월과 완전한 전월의 차이를 추세나 수요 급감으로 단정하지 말 것. "
          "관광 순위는 note의 조회 지역 범위 안의 순위이며 전국 순위가 아니다."
    )


def main() -> None:
    load_dotenv(BASE / ".env")
    if os.getenv("LLM_PROVIDER", "gemini").lower() != "gemini":
        raise RuntimeError("현재 기본 구현은 Gemini만 지원합니다. 다른 공급자는 호출 함수 추가 필요.")
    api_key, model = os.getenv("LLM_API_KEY"), os.getenv("LLM_MODEL")
    if not api_key or not model:
        raise RuntimeError("LLM_API_KEY, LLM_MODEL을 .env에 설정하세요.")
    path = REPORTS / "analysis_summary.csv"
    df = pd.read_csv(path)
    required = {"source", "metric", "period", "label", "value", "unit", "note"}
    if df.empty or not required.issubset(df.columns) or df["value"].isna().any():
        raise ValueError("분석 요약이 비었거나 필수 컬럼·수치가 유효하지 않습니다.")
    records = df.to_dict("records")
    from google import genai
    from google.genai import errors, types
    client = genai.Client(api_key=api_key)  # 변수 유지: 체이닝 시 클라이언트가 먼저 닫힘
    prompt = build_prompt(records)
    response = None
    for attempt in range(1, 6):  # 429/503 같은 일시 오류만 재시도
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # 이 과제는 함수 도구를 사용하지 않으므로 AFC 경고를 방지한다.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                ),
            )
            break
        except (errors.ServerError, errors.ClientError) as exc:
            if getattr(exc, "code", None) not in (429, 503) or attempt == 5:
                raise
            wait = 10 * attempt
            print(f"[RETRY] LLM {exc.code} 일시 오류, {wait}초 후 재시도 ({attempt}/5)")
            time.sleep(wait)
    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise RuntimeError("LLM이 빈 결과를 반환했습니다.")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "llm_summary.md").write_text(
        f"# 관광 트렌드 요약\n\n생성 시각(UTC): "
        f"{datetime.now(timezone.utc).isoformat()}\n\n"
        f"> 사람의 숫자·인과 표현 검수가 필요한 AI 초안입니다.\n\n{text}\n",
        encoding="utf-8",
    )
    print("[PASS] LLM 초안 생성: reports/llm_summary.md")
    print("[REVIEW REQUIRED] 원본 분석 수치와 문장이 일치하는지 확인하세요.")


if __name__ == "__main__":
    main()
