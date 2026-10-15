"""NAVER 검색 관심도와 관광공사 지역 데이터를 '별개 분석' 후 단일 보고서에 정리."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data/raw"
PROCESSED = BASE / "data/processed"
REPORTS = BASE / "reports"


def extract_records(node: object) -> list[dict]:
    """중첩 JSON에서 객체 행 목록 발견. 실제 키 값은 config에서 별도로 확인."""
    if isinstance(node, list):
        records = [item for item in node if isinstance(item, dict)]
        if records:
            return records
        for item in node:
            found = extract_records(item)
            if found:
                return found
    if isinstance(node, dict):
        for key in ("item", "items", "data", "rows", "list", "result", "body", "response"):
            if key in node:
                found = extract_records(node[key])
                if found:
                    return found
        for value in node.values():
            if isinstance(value, (dict, list)):
                found = extract_records(value)
                if found:
                    return found
    return []


def tourism_frame(payload: object, mapping: dict, name: str) -> pd.DataFrame:
    required = ("region", "period", "value")
    if not all(mapping.get(field) for field in required):
        raise ValueError(f"{name}: config/tourism_params.json 의 fields(region/period/value)를 "
                         "실제 Swagger 응답에 맞춰 설정하세요.")
    records = extract_records(payload)
    if not records:
        raise ValueError(f"{name}: 실제 지역 데이터 레코드를 찾지 못했습니다.")
    keys = list(records[0].keys())
    if any(mapping[field] not in records[0] for field in required):
        raise ValueError(f"{name}: 필드명이 응답과 다릅니다. 첫 레코드의 필드: {keys}")
    df = pd.DataFrame([
        {
            "region": record.get(mapping["region"]),
            "period": record.get(mapping["period"]),
            "value": record.get(mapping["value"]),
        }
        for record in records
    ])
    df["value"] = pd.to_numeric(
        df["value"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    if df.empty or df[["region", "period", "value"]].isna().any().any():
        raise ValueError(f"{name}: 지역/시점/강도 필드 변환이 실패했습니다.")
    if df.duplicated(["region", "period"]).any():
        raise ValueError(f"{name}: 지역-기간이 중복되었습니다. 단위·집계 기준을 확인하세요.")
    return df


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """시점의 단위가 확인되지 않은 상태에서는 문자열 정렬만 시행한다."""
    periods = df["period"].astype(str)
    return df[periods == periods.max()].copy()


def plot_tourism_top10(df: pd.DataFrame, output: Path, title: str) -> None:
    top = latest_snapshot(df).nlargest(10, "value").sort_values("value")
    if top.empty:
        raise ValueError(f"{title}: 최신 기간 데이터가 없습니다.")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(top["region"].astype(str), top["value"])
    ax.set(title=title, xlabel="해당 API가 정의한 강도 지표")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    naver_path = PROCESSED / "naver_trend.csv"
    naver = pd.read_csv(naver_path, dtype={"keyword": str})
    naver["period"] = pd.to_datetime(naver["period"], errors="coerce")
    naver["ratio"] = pd.to_numeric(naver["ratio"], errors="coerce")
    if naver.empty or naver[["period", "keyword", "ratio"]].isna().any().any():
        raise ValueError("NAVER 분석용 CSV가 비었거나 자료형 검증에 실패했습니다.")
    if not naver["ratio"].between(0, 100).all():
        raise ValueError("NAVER ratio 범위가 0~100이 아닙니다.")

    plt.rcParams["font.family"] = "Malgun Gothic" if Path("C:/Windows/Fonts/malgun.ttf").exists() else "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for keyword, group in naver.groupby("keyword"):
        group = group.sort_values("period")
        ax.plot(group["period"], group["ratio"], marker="o", label=keyword)
    ax.set(title="NAVER 월별 검색 관심도(상대지수)", xlabel="기간", ylabel="ratio (0~100)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(REPORTS / "naver_trend.png", dpi=160)
    plt.close(fig)

    rows = []
    for keyword, group in naver.groupby("keyword"):
        latest = group.sort_values("period").iloc[-1]
        rows.append({
            "source": "NAVER Search Trend", "metric": "검색 상대 관심도",
            "period": latest["period"].date().isoformat(),
            "label": keyword, "value": float(latest["ratio"]),
            "unit": "ratio(0~100)", "note": "실제 검색 건수가 아님",
        })

    config = json.loads((BASE / "config/tourism_params.json").read_text(encoding="utf-8"))
    for name, label in [("stay", "관광 체류 강도"), ("consumption", "관광 소비 강도")]:
        snapshots = sorted(RAW.glob(f"tourism_{name}_*.json"))
        if not snapshots:
            raise FileNotFoundError(f"{name} 관광 API Raw JSON이 없습니다.")
        payload = json.loads(snapshots[-1].read_text(encoding="utf-8"))
        frame = tourism_frame(payload, config[name]["fields"], name)
        top10 = latest_snapshot(frame).nlargest(10, "value")
        plot_tourism_top10(
            frame, REPORTS / f"tourism_{name}_top10.png",
            f"지역별 {label} 상위 10개 (최신 기간)",
        )
        for _, item in top10.iterrows():
            rows.append({
                "source": f"Tourism API {name}", "metric": label,
                "period": str(item["period"]), "label": str(item["region"]),
                "value": float(item["value"]), "unit": "API 정의 강도",
                "note": "지역·시점별 지표; NAVER ratio와 직접 비교 금지",
            })
    summary = pd.DataFrame(rows)
    if summary.empty or summary["value"].isna().any():
        raise ValueError("분석 요약 검증 실패")
    path = REPORTS / "analysis_summary.csv"
    summary.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[PASS] 분석 요약 {len(summary)}건: {path}")
    print("NAVER 전국 검색 관심도와 관광 지역별 강도는 행 단위로 merge하지 않았습니다.")


if __name__ == "__main__":
    main()
