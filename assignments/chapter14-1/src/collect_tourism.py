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
        if code and code not in ("00", "0", "NORMAL_CODE"):
            raise RuntimeError(f"공공데이터 API 응답 오류: code={code}, "
                               f"message={header.get('resultMsg')}")
    if not has_actual_records(data):
        raise ValueError("실제 지역 데이터 배열을 확인하지 못했습니다. Swagger 응답을 확인하세요.")


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
        params["serviceKey"] = service_key
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError(f"{name}: JSON 응답이 아닙니다. Swagger의 응답 형식을 확인하세요.") from exc
        validate_tourism_response(data)
        responses[name] = data
        print(f"[PASS] Tourism {name}: HTTP {response.status_code}, 실제 항목 구조 확인")
    for name, data in responses.items():
        path = raw / f"tourism_{name}_{stamp}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("저장:", path)


if __name__ == "__main__":
    main()
