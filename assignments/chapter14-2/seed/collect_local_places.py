"""Collect real NAVER Local results, then export validated Supabase import CSV.

Credentials are read from ignored local env files and never printed or exported.
This command does not write to Supabase or activate any schedule.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from prepare_seed import places_frame


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if match:
            values[match[1]] = match[2].strip("\"'")
    return values


def fetch_json(url: str, headers: dict[str, str]) -> object:
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def normalize_coordinates(mapx: object, mapy: object) -> tuple[float, float]:
    lon, lat = float(mapx), float(mapy)
    if abs(lon) > 1_000_000 and abs(lat) > 1_000_000 and lon.is_integer() and lat.is_integer():
        lon, lat = lon / 10_000_000, lat / 10_000_000
    # This collector requests Seoul only. Reject corrupt, reversed or foreign coordinates.
    if not (124 <= lon <= 132 and 33 <= lat <= 39):
        raise ValueError("Place coordinates are outside the requested Korean region")
    return lon, lat


def enrich_items(payload: dict, category: str, regions: list[dict]) -> list[dict]:
    if not isinstance(payload.get("items"), list):
        raise ValueError("NAVER Local items is missing")
    districts = {row["region_name"]: row["region_code"] for row in regions if len(row["region_code"]) == 5}
    result = []
    for item in payload["items"]:
        address = str(item.get("roadAddress") or item.get("address") or "").strip()
        if not address.startswith(("서울특별시 ", "서울 ")):
            raise ValueError("Search result does not belong to Seoul")
        matched = [code for name, code in districts.items() if name in address.split()]
        if len(matched) != 1:
            raise ValueError("Cannot match a unique registered district for the place")
        lon, lat = normalize_coordinates(item.get("mapx"), item.get("mapy"))
        result.append({**item, "region_code": matched[0], "search_category": category, "mapx": lon, "mapy": lat})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", type=Path, required=True, help="Local NAVER credential env file")
    parser.add_argument("--dashboard-env", type=Path, default=Path(__file__).resolve().parents[1] / "dashboard/.env.local")
    args = parser.parse_args()
    source = read_env(args.source_env)
    config = read_env(args.dashboard_env)
    headers = {
        "X-NCP-APIGW-API-KEY-ID": source["NAVER_CLIENT_ID"],
        "X-NCP-APIGW-API-KEY": source["NAVER_CLIENT_SECRET"],
    }
    public_key = config["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]
    if public_key.startswith("sb_secret_"):
        raise ValueError("Dashboard must use a public read key")
    regions = fetch_json(config["NEXT_PUBLIC_SUPABASE_URL"] + "/rest/v1/regions?select=region_code,region_name", {"apikey": public_key})
    items, responses = [], []
    for category in ("관광명소", "맛집", "카페"):
        query = "서울 " + category
        url = "https://naverapihub.apigw.ntruss.com/search/v1/local?" + urlencode({"query": query, "display": 5, "start": 1, "sort": "random", "format": "json"})
        payload = fetch_json(url, headers)
        items.extend(enrich_items(payload, category, regions))
        responses.append({"query": query, "response": payload})
    # Identical businesses in the same search category have one stable key.
    unique = {}
    for item in items:
        identity = (item["region_code"], item["search_category"], item["title"], item.get("roadAddress") or item.get("address"))
        unique[identity] = item
    data = places_frame(list(unique.values()))
    base = Path(__file__).resolve().parent
    (base / "raw").mkdir(exist_ok=True)
    (base / "processed").mkdir(exist_ok=True)
    raw = {"source": "NAVER API HUB Local", "fetched_at": datetime.now(timezone.utc).isoformat(), "queries": responses, "items": list(unique.values())}
    (base / "raw/local_places.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    data.to_csv(base / "processed/local_places_seed.csv", index=False, encoding="utf-8-sig")
    print(f"NAVER Local: {len(responses)} requests, {len(data)} validated places, {data.region_code.nunique()} districts")
    print("Exported seed/processed/local_places_seed.csv; Supabase import is a separate step.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HTTPError as error:
        print(f"NAVER/Supabase HTTP {error.code}. Check API activation and public read permissions; no credentials were logged.", file=sys.stderr)
        raise SystemExit(1)
    except (URLError, ValueError, KeyError, OSError, TypeError) as error:
        print(f"Collection stopped: {type(error).__name__}. Check local configuration and real response fields.", file=sys.stderr)
        raise SystemExit(1)
