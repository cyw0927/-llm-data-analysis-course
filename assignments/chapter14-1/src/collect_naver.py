"""NAVER Search Trend 월별 상대 관심도: 수집, Raw 보존, 정규화 검증."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
KEYWORDS = ("여행", "축제", "캠핑", "맛집")


def parse_naver_response(data: dict) -> pd.DataFrame:
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("NAVER 응답에 results 배열이 없습니다.")
    rows = [
        {"period": p.get("period"), "keyword": group.get("title"), "ratio": p.get("ratio")}
        for group in data["results"]
        for p in group.get("data", [])
    ]
    df = pd.DataFrame(rows, columns=["period", "keyword", "ratio"])
    if df.empty:
        raise ValueError("NAVER 결과가 비어 있습니다.")
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
    if df[["period", "keyword", "ratio"]].isna().any().any():
        raise ValueError("NAVER 날짜/키워드/ratio에 결측 또는 변환 오류가 있습니다.")
    if not df["ratio"].between(0, 100).all():
        raise ValueError("NAVER ratio 값이 0~100 범위를 벗어났습니다.")
    if set(df["keyword"].unique()) != set(KEYWORDS):
        raise ValueError("NAVER 응답의 키워드 그룹이 요청한 4개와 다릅니다.")
    if df.duplicated(["period", "keyword"]).any():
        raise ValueError("NAVER 기간-키워드 중복 데이터가 있습니다.")
    return df.sort_values(["keyword", "period"]).reset_index(drop=True)


def main() -> None:
    load_dotenv(BASE / ".env")
    client_id = os.getenv("NAVER_CLIENT_ID")
    secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not secret:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET을 .env에 설정하세요.")
    end = date.today()
    start = end - timedelta(days=365)
    payload = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "timeUnit": "month",
        "keywordGroups": [{"groupName": word, "keywords": [word]} for word in KEYWORDS],
    }
    response = requests.post(
        URL,
        headers={
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": secret,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    df = parse_naver_response(data)  # 검증 전 성공이라고 보고하지 않음
    raw = BASE / "data/raw"
    processed = BASE / "data/processed"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    (raw / f"naver_trend_{stamp}.json").write_text(
        json.dumps({"request": payload, "response": data, "collected_at_utc": stamp},
                   ensure_ascii=False, indent=2), encoding="utf-8"
    )
    df.to_csv(processed / "naver_trend.csv", index=False, encoding="utf-8-sig")
    print(f"[PASS] NAVER: rows={len(df)}, keywords={df['keyword'].nunique()}, "
          f"period={df['period'].min().date()}~{df['period'].max().date()}")
    print("주의: ratio는 실제 검색 건수가 아닌 조회 기간 내 상대 관심도입니다.")


if __name__ == "__main__":
    main()
