"""NAVER 검색 관심도와 관광공사 지역 강도 데이터를 '별개 분석'한 뒤 단일 보고서용 요약으로 정리."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data/raw"
PROCESSED = BASE / "data/processed"
REPORTS = BASE / "reports"

FONT_CANDIDATES = ("Malgun Gothic", "NanumGothic", "Noto Sans CJK KR", "AppleGothic")


def setup_korean_font() -> str:
    """설치된 한글 글꼴을 찾아 Matplotlib에 적용. 없으면 글자가 깨지므로 즉시 실패."""
    for path in (Path("C:/Windows/Fonts/malgun.ttf"),):
        if path.is_file():
            font_manager.fontManager.addfont(str(path))
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in FONT_CANDIDATES:
        if name in installed:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("한글 글꼴(맑은 고딕 등)을 찾지 못했습니다. 그래프 한글이 깨집니다.")


def extract_records(node: object) -> list[dict]:
    """중첩 JSON에서 객체 행 목록 발견. 실제 필드명은 config에서 별도로 확인."""
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
    """관광 JSON -> region/period/value (+ scope). signguNm='_' 행은 시도 전체 집계로 분리."""
    required = ("region", "period", "value")
    if not all(mapping.get(field) for field in required):
        raise ValueError(f"{name}: config/tourism_params.json의 fields(region/period/value)를 "
                         "실제 Swagger 응답에 맞춰 설정하세요.")
    records = extract_records(payload)
    if not records:
        raise ValueError(f"{name}: 실제 지역 데이터 레코드를 찾지 못했습니다.")
    keys = list(records[0].keys())
    if any(mapping[field] not in records[0] for field in required):
        raise ValueError(f"{name}: 필드명이 응답과 다릅니다. 첫 레코드의 필드: {keys}")
    area_key = mapping.get("area")
    rows = []
    for record in records:
        region = record.get(mapping["region"])
        area = record.get(area_key) if area_key else None
        is_total = str(region).strip() in ("_", "")
        if is_total and area:
            label, scope = f"{area} 전체", "시도 전체"
        else:
            label, scope = region, "시군구"
        rows.append({
            "region": label, "period": record.get(mapping["period"]),
            "value": record.get(mapping["value"]), "scope": scope,
        })
    df = pd.DataFrame(rows)
    df["value"] = pd.to_numeric(
        df["value"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    if df.empty or df[["region", "period", "value"]].isna().any().any():
        raise ValueError(f"{name}: 지역/시점/강도 필드 변환에 실패했습니다.")
    if df.duplicated(["region", "period"]).any():
        raise ValueError(f"{name}: 지역·기간이 중복되었습니다. 단위·집계 기준을 확인하세요.")
    return df


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    periods = df["period"].astype(str)
    return df[periods == periods.max()].copy()


def plot_tourism_top10(df: pd.DataFrame, output: Path, title: str) -> None:
    districts = latest_snapshot(df)
    districts = districts[districts["scope"] == "시군구"]
    top = districts.nlargest(10, "value").sort_values("value")
    if top.empty:
        raise ValueError(f"{title}: 최신 기간 시군구 데이터가 없습니다.")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(top["region"].astype(str), top["value"])
    ax.bar_label(bars, fmt="%.1f", padding=3)
    ax.set(title=title, xlabel="해당 API가 정의한 강도 지수")
    ax.margins(x=0.1)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def analyze_naver(naver: pd.DataFrame) -> list[dict]:
    """키워드별 월별 추이 그래프와 최신/직전월 비교 요약."""
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
        group = group.sort_values("period")
        latest = group.iloc[-1]
        prev = group.iloc[-2] if len(group) > 1 else None
        common = {"source": "NAVER Search Trend", "label": keyword,
                  "unit": "ratio(0~100)"}
        rows.append({**common, "metric": "검색 상대 관심도(최신 월)",
                     "period": latest["period"].date().isoformat(),
                     "value": float(latest["ratio"]),
                     "note": "실제 검색 건수가 아님. 최신 월은 집계 중인 부분 월일 수 있음"})
        if prev is not None:
            diff = float(latest["ratio"] - prev["ratio"])
            trend = "상승" if diff > 0 else "하락" if diff < 0 else "보합"
            rows.append({**common, "metric": f"직전 월 대비 변화({trend})",
                         "period": f"{prev['period'].date()}→{latest['period'].date()}",
                         "value": round(diff, 2),
                         "note": "ratio 포인트 차이, 상대지수 간 비교"})
    return rows


def analyze_tourism(name: str, label: str, config: dict) -> list[dict]:
    snapshots = sorted(RAW.glob(f"tourism_{name}_*.json"))
    if not snapshots:
        raise FileNotFoundError(f"{name} 관광 API Raw JSON이 없습니다.")
    payload = json.loads(snapshots[-1].read_text(encoding="utf-8"))
    frame = tourism_frame(payload, config[name]["fields"], name)
    latest = latest_snapshot(frame)
    districts = latest[latest["scope"] == "시군구"]
    totals = latest[latest["scope"] == "시도 전체"]
    print(f"[CHECK] {name}: 파일={snapshots[-1].name} 행={len(frame)} "
          f"기준월={sorted(frame['period'].astype(str).unique())} "
          f"시군구={len(districts)} 시도전체={len(totals)} 결측=0 중복=0")
    plot_tourism_top10(frame, REPORTS / f"tourism_{name}_top10.png",
                       f"지역별 {label} 상위 10개 시군구 ({latest['period'].iloc[0]})")
    note = "지역·시점별 지표. NAVER ratio와 직접 비교 금지"
    rows = []
    for _, item in totals.iterrows():
        rows.append({"source": f"Tourism API {name}", "metric": f"{label}(시도 전체)",
                     "period": str(item["period"]), "label": str(item["region"]),
                     "value": float(item["value"]), "unit": "API 정의 강도", "note": note})
    for _, item in districts.nlargest(10, "value").iterrows():
        rows.append({"source": f"Tourism API {name}", "metric": f"{label}(시군구 상위10)",
                     "period": str(item["period"]), "label": str(item["region"]),
                     "value": float(item["value"]), "unit": "API 정의 강도", "note": note})
    return rows


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    print("[FONT]", setup_korean_font())
    naver = pd.read_csv(PROCESSED / "naver_trend.csv", dtype={"keyword": str})
    naver["period"] = pd.to_datetime(naver["period"], errors="coerce")
    naver["ratio"] = pd.to_numeric(naver["ratio"], errors="coerce")
    if naver.empty or naver[["period", "keyword", "ratio"]].isna().any().any():
        raise ValueError("NAVER 분석용 CSV가 비었거나 자료형 검증에 실패했습니다.")
    if not naver["ratio"].between(0, 100).all():
        raise ValueError("NAVER ratio 범위가 0~100이 아닙니다.")
    if naver.duplicated(["period", "keyword"]).any():
        raise ValueError("NAVER 기간-키워드 중복이 있습니다.")
    print(f"[CHECK] naver: 행={len(naver)} 키워드={naver['keyword'].nunique()} "
          f"기간={naver['period'].min().date()}~{naver['period'].max().date()}")

    rows = analyze_naver(naver)
    config = json.loads((BASE / "config/tourism_params.json").read_text(encoding="utf-8"))
    rows += analyze_tourism("stay", "관광 체류 강도", config)
    rows += analyze_tourism("consumption", "관광 소비 강도", config)
    summary = pd.DataFrame(rows)
    if summary.empty or summary["value"].isna().any():
        raise ValueError("분석 요약 검증 실패")
    path = REPORTS / "analysis_summary.csv"
    summary.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[PASS] 분석 요약 {len(summary)}건: {path}")
    print("NAVER 전국 검색 관심도와 관광 지역별 강도는 한 단위로 merge하지 않았습니다.")


if __name__ == "__main__":
    main()
