"""Chapter 14-2: 실제 Raw/CSV를 Supabase Import용 Seed로 전처리 (모의 데이터 생성 없음).

실행: python seed/prepare_seed.py
테스트: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
PROCESSED = BASE / "processed"


def canonical_code(value: object) -> str:
    """CSV/Excel에서 11.0이 된 지역 코드의 .0을 제거하되 앞자리 0은 보존."""
    if pd.isna(value):
        return ""
    code = str(value).strip()
    if re.fullmatch(r"\d+\.0", code):
        code = code[:-2]
    return code


def reference_date(value: object) -> str:
    """관광공사 월별 '202509' -> '2025-09-01'. 수집일이 아닌 기준월."""
    text = str(value).strip()
    if re.fullmatch(r"\d{6}", text):
        text = text[:4] + "-" + text[4:] + "-01"
    elif re.fullmatch(r"\d{4}-\d{2}", text):
        text += "-01"
    try:
        result = pd.to_datetime(text, errors="raise")
    except (ValueError, TypeError) as error:
        raise ValueError(f"기준일/월 파싱 실패: {value}") from error
    if pd.isna(result):
        raise ValueError(f"기준일/월 누락: {value}")
    return result.date().isoformat()


def numeric(value: object) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        result = float(str(value).replace(",", "").strip())
    except ValueError as error:
        raise ValueError(f"숫자 변환 실패: {value}") from error
    if not pd.notna(result) or not -1e100 < result < 1e100:
        raise ValueError(f"숫자가 유한하지 않거나 범위 초과: {value}")
    return result


def check_unique(df: pd.DataFrame, columns: list[str], name: str) -> None:
    if df.empty:
        raise ValueError(f"{name} 데이터가 비었습니다.")
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{name} 필수 컬럼 없음: {missing}")
    if df[columns].isna().any().any():
        raise ValueError(f"{name} 식별자 결측")
    duplicate = df.duplicated(columns, keep=False)
    if duplicate.any():
        example = df.loc[duplicate, columns].head(3).to_dict("records")
        raise ValueError(f"{name} 유일키 중복 {duplicate.sum()}행: {example}")


def tourism_csv_frame(df: pd.DataFrame) -> pd.DataFrame:
    fields = ["reference_date", "region_code", "stay_strength", "consumption_strength"]
    missing = sorted(set(fields) - set(df.columns))
    if missing:
        raise ValueError(f"관광 Seed CSV 필수 컬럼 누락: {missing}")
    out = df[fields].copy()
    out["reference_date"] = out["reference_date"].map(reference_date)
    out["region_code"] = out["region_code"].map(canonical_code)
    if not out["region_code"].astype(bool).all():
        raise ValueError("관광 지역코드 공백")
    for name in ("stay_strength", "consumption_strength"):
        out[name] = out[name].map(numeric)
    if out[["stay_strength", "consumption_strength"]].isna().all(axis=1).any():
        raise ValueError("체류/소비 강도가 모두 비어 있는 관광 행")
    check_unique(out, ["reference_date", "region_code"], "관광 Seed CSV")
    return out.sort_values(["reference_date", "region_code"]).reset_index(drop=True)


def unwrap_tourism_json(payload: object) -> list[dict]:
    if not isinstance(payload, dict) or "response" not in payload:
        raise ValueError("관광 API 응답 형식: response 객체 누락")
    response = payload["response"]
    header = response.get("header", {})
    if str(header.get("resultCode", "")).strip() not in ("0000", "00", "0"):
        raise ValueError(f"관광 API 실패 응답: {header.get('resultCode')}")
    body = response.get("body", {})
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items or any(not isinstance(x, dict) for x in items):
        raise ValueError("관광 API 실제 item 데이터 누락")
    total_count = body.get("totalCount")
    if total_count is not None and int(total_count) > len(items):
        raise ValueError(f"관광 API 페이지 일부만 보유: {len(items)}/{total_count}. 전체 페이지를 수집하세요.")
    return items


def tourism_json_frame(payload: object, mapping: dict, metric: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = ("period", "area_code", "district_code", "value")
    if any(not mapping.get(k) for k in required):
        raise ValueError(f"{metric} 필드 매핑이 비어 있습니다. 실제 Swagger JSON 확인 후 설정")
    records = unwrap_tourism_json(payload)
    rows = []
    names = []
    for item in records:
        if any(k not in item for k in (mapping["period"], mapping["area_code"],
                                      mapping["district_code"], mapping["value"])):
            raise ValueError(f"{metric} 응답 필드 누락. 첫 행 키: {sorted(item)}")
        district = canonical_code(item[mapping["district_code"]])
        area = canonical_code(item[mapping["area_code"]])
        code = district if district not in ("", "0", "_") else area
        if not code:
            raise ValueError(f"{metric} 지역코드를 확인할 수 없습니다.")
        date = reference_date(item[mapping["period"]])
        rows.append({"reference_date": date, "region_code": code, metric: numeric(item[mapping["value"]])})
        area_name = str(item.get("areaNm") or "").strip()
        district_name = str(item.get("signguNm") or item.get("sigunguNm") or "").strip()
        region_name = district_name if district not in ("", "0", "_") and district_name not in ("", "_") else area_name
        if region_name:
            names.append({"region_code": code, "region_name": region_name})
    df = pd.DataFrame(rows, columns=["reference_date", "region_code", metric])
    if df[metric].isna().all():
        raise ValueError(f"{metric} 모든 강도가 누락")
    check_unique(df, ["reference_date", "region_code"], f"관광 {metric}")
    region_df = pd.DataFrame(names, columns=["region_code", "region_name"])
    if not region_df.empty:
        conflicting = region_df.groupby("region_code")["region_name"].nunique()
        if (conflicting > 1).any():
            raise ValueError("동일 지역코드에 지역명 여러 개 매핑")
        region_df = region_df.drop_duplicates("region_code")
    return df, region_df


def combine_tourism(stay: pd.DataFrame, consumption: pd.DataFrame) -> pd.DataFrame:
    keys = ["reference_date", "region_code"]
    check_unique(stay, keys, "stay")
    check_unique(consumption, keys, "consumption")
    merged = stay.merge(consumption, on=keys, how="outer", validate="one_to_one", indicator=True)
    missing = merged["_merge"].value_counts().to_dict()
    if missing.get("left_only", 0) or missing.get("right_only", 0):
        print("[WARN] 체류·소비 미매칭:", missing, "(임의로 0을 채우지 않음)")
    merged = merged.drop(columns="_merge")
    return tourism_csv_frame(merged)


def naver_frame(df: pd.DataFrame) -> pd.DataFrame:
    period = "reference_date" if "reference_date" in df.columns else "period"
    fields = [period, "keyword", "ratio"]
    if not set(fields).issubset(df.columns):
        raise ValueError(f"NAVER 필수 컬럼: {fields}")
    out = df[fields].rename(columns={period: "reference_date"}).copy()
    out["reference_date"] = out["reference_date"].map(reference_date)
    out["keyword"] = out["keyword"].astype("string").str.strip()
    out["ratio"] = out["ratio"].map(numeric)
    if out[["reference_date", "keyword", "ratio"]].isna().any().any():
        raise ValueError("NAVER 결측")
    if not out["ratio"].between(0, 100).all():
        raise ValueError("NAVER ratio는 0~100의 상대지수")
    check_unique(out, ["reference_date", "keyword"], "NAVER")
    return out.sort_values(["reference_date", "keyword"]).reset_index(drop=True)


def clean_place_title(title: object) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", str(title or ""))).strip()


def places_frame(payload: object) -> pd.DataFrame:
    """이미 지역코드·검색카테고리가 명시된 응답만 Seed로 허용."""
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("NAVER Local items 배열 누락")
    rows = []
    for item in items:
        region = canonical_code(item.get("region_code", ""))
        search = str(item.get("search_category", "")).strip()
        name = clean_place_title(item.get("title") or item.get("name"))
        address = str(item.get("roadAddress") or item.get("address") or "").strip()
        if not all((region, search, name, address)):
            raise ValueError("장소별 region_code, search_category, 이름, 주소가 필요합니다.")
        lon = numeric(item.get("mapx", item.get("longitude")))
        lat = numeric(item.get("mapy", item.get("latitude")))
        if lon is not None and not -180 <= lon <= 180:
            raise ValueError(f"NAVER Local 경도 범위 오류: {lon}")
        if lat is not None and not -90 <= lat <= 90:
            raise ValueError(f"NAVER Local 위도 범위 오류: {lat}")
        key = hashlib.sha256("|".join([region, search, name, address]).encode("utf-8")).hexdigest()
        rows.append({
            "place_key": key, "region_code": region, "search_category": search, "name": name,
            "category": item.get("category"), "address": item.get("address"),
            "road_address": item.get("roadAddress"), "longitude": lon, "latitude": lat,
            "source_link": item.get("link"),
        })
    out = pd.DataFrame(rows, columns=[
        "place_key", "region_code", "search_category", "name", "category",
        "address", "road_address", "longitude", "latitude", "source_link"
    ])
    if not out.empty:
        check_unique(out, ["place_key"], "NAVER Local")
    return out


def save(df: pd.DataFrame, filename: str) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[PASS] {filename}: rows={len(df)}, {path}")


def run(mapping_path: Path | None = None) -> None:
    mapping_path = mapping_path or BASE / "config.example.json"
    csv = RAW / "tourism_seed.csv"
    if csv.exists():
        raw = pd.read_csv(csv, dtype={"region_code": str, "reference_date": str})
        save(tourism_csv_frame(raw), "tourism_demand_seed.csv")
    else:
        stay_files = sorted(RAW.glob("tourism_stay_*.json"))
        consumption_files = sorted(RAW.glob("tourism_consumption_*.json"))
        if stay_files and consumption_files:
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            stay, stay_regions = tourism_json_frame(
                json.loads(stay_files[-1].read_text(encoding="utf-8")),
                mapping["stay"], "stay_strength"
            )
            consumption, consumption_regions = tourism_json_frame(
                json.loads(consumption_files[-1].read_text(encoding="utf-8")),
                mapping["consumption"], "consumption_strength"
            )
            save(combine_tourism(stay, consumption), "tourism_demand_seed.csv")
            if not stay_regions.empty or not consumption_regions.empty:
                regions = pd.concat([stay_regions, consumption_regions], ignore_index=True)
                conflicts = regions.groupby("region_code")["region_name"].nunique()
                if (conflicts > 1).any():
                    raise ValueError("체류/소비 간 지역명 충돌")
                save(regions.drop_duplicates("region_code"), "regions_seed.csv")
        else:
            print("[SKIP] 관광 Seed 입력 없음. seed/raw/tourism_seed.csv 또는 양쪽 관광 JSON 필요")

    naver = RAW / "naver_trend.csv"
    if naver.exists():
        save(naver_frame(pd.read_csv(naver)), "naver_trend_seed.csv")
    else:
        print("[SKIP] NAVER Seed 입력 없음: seed/raw/naver_trend.csv")
    local = RAW / "local_places.json"
    if local.exists():
        place_df = places_frame(json.loads(local.read_text(encoding="utf-8")))
        if not place_df.empty:
            save(place_df, "local_places_seed.csv")
        else:
            print("[SKIP] NAVER Local 실제 장소가 0건")
    else:
        print("[SKIP] NAVER Local Seed 입력 없음: seed/raw/local_places.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="실제 수집 데이터만 Supabase import용 CSV로 변환")
    parser.add_argument("--mapping", type=Path, default=BASE / "config.example.json",
                        help="관광 API 실제 응답 필드 매핑 JSON")
    args = parser.parse_args()
    run(args.mapping)
