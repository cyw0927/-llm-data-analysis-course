"""한국관광공사 지역별 관광 체류/소비 강도: 실제 Swagger 파라미터로 수집."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]


def has_actual_records(node: object) -> bool:
    """JSON 오류 응답 {} 혹은 resultMsg만을 성공 데이터로 취급하지 않음."""
    if isinstance(node, list):
        return any(isinstance(x, dict) and x for x in node)
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in ("data", "items", "item", "list", "rows") and has_actual_records(value):
                return True
            if isinstance(value, (dict, list)) and has_actual_records(value):
                return True
    return False


def validate_tourism_response(data: object) -> None:
    if not isinstance(data, (dict, list)) or not data:
        raise ValueError("공공데이터 응답이 비었거나 JSON 객체/배열이 아닙니다.")
    if isinstance(data, dict):
        response = data.get("response", data)
        header = response.get("header", {}) if isinstance(response, dict) else {}
        code = str(header.get("resultCode", "")).strip()
        if code and code not in ("0000", "00", "0", "NORMAL_CODE"):
            raise RuntimeError(f"공공데이터 API 응답 오류: code={code}, "
                               f"message={header.get('resultMsg')}")
    if not has_actual_records(data):
        raise ValueError("실제 지역 데이터 배열을 확인하지 못했습니다. Swagger 응답을 확인하세요.")


def extract_items(data: dict) -> list[dict]:
    items = data.get("response", {}).get("body", {}).get("items") or {}
    item = items.get("item", []) if isinstance(items, dict) else []
    return [item] if isinstance(item, dict) else list(item)


def fetch_all_pages(url: str, service_key: str, params: dict, name: str) -> dict:
    """totalCount까지 페이지네이션 후 하나의 응답으로 합치고 건수를 검증한다."""
    page_size = int(params.get("numOfRows", 100))
    page = int(params.get("pageNo", 1))
    if page_size < 1 or page != 1:
        raise ValueError(f"{name}: 전체 수집은 pageNo=1, numOfRows>0이어야 합니다.")
    merged: dict | None = None
    items: list[dict] = []
    total = None
    while True:
        query = {**params, "pageNo": page, "serviceKey": service_key}
        try:
            response = requests.get(url, params=query, timeout=30)
        except requests.RequestException:
            # requests 예외에는 serviceKey가 들어간 전체 URL이 포함될 수 있다.
            raise RuntimeError(f"{name}: 관광 API 네트워크 요청 실패 (인증정보 생략)") from None
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"{name}: 관광 API HTTP {response.status_code} (인증정보 생략)")
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError(f"{name}: JSON 응답이 아닙니다. Swagger의 응답 형식을 확인하세요.") from exc
        validate_tourism_response(data)
        body = data["response"]["body"]
        total = int(body.get("totalCount", 0))
        page_items = extract_items(data)
        if not page_items:
            raise RuntimeError(f"{name}: totalCount 도달 전 빈 페이지입니다.")
        if merged is not None and total != int(merged["response"]["body"]["totalCount"]):
            raise RuntimeError(f"{name}: 페이지 사이 totalCount가 변경되었습니다.")
        items.extend(page_items)
        if merged is None:
            merged = data
        if len(items) >= total or page > 1000:
            break
        page += 1
    if len(items) != total:
        raise RuntimeError(f"{name}: 수집 건수({len(items)})가 totalCount({total})와 다릅니다.")
    merged["response"]["body"]["items"] = {"item": items}
    merged["response"]["body"]["numOfRows"] = len(items)
    merged["response"]["body"]["pageNo"] = 1
    merged["response"]["body"]["totalCount"] = total
    return merged


def main() -> None:
    load_dotenv(BASE / ".env")
    service_key = os.getenv("TOURISM_SERVICE_KEY")
    endpoints = {
        "stay": os.getenv("TOURISM_STAY_URL"),
        "consumption": os.getenv("TOURISM_CONSUMPTION_URL"),
    }
    if not service_key or any(not u for u in endpoints.values()):
        raise RuntimeError("TOURISM_SERVICE_KEY, TOURISM_STAY_URL, "
                           "TOURISM_CONSUMPTION_URL을 .env에 설정하세요.")
    config_path = BASE / "config/tourism_params.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    raw = BASE / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # 두 API가 모두 유효할 때만 Raw 스냅샷 저장
    responses = {}
    for name, url in endpoints.items():
        params = dict(config[name]["params"])
        data = fetch_all_pages(url, service_key, params, name)
        responses[name] = data
        print(f"[PASS] Tourism {name}: {len(extract_items(data))}건 수집, "
              f"totalCount={data['response']['body']['totalCount']}")
    for name, data in responses.items():
        path = raw / f"tourism_{name}_{stamp}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("저장:", path)


if __name__ == "__main__":
    main()
