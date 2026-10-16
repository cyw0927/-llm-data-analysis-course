"""API 키/외부 네트워크 없이 핵심 데이터 유효성 검증 테스트."""
import unittest
import traceback
from unittest.mock import Mock, patch
import requests

from src.collect_naver import parse_naver_response
from src.collect_tourism import validate_tourism_response, extract_items, fetch_all_pages
from src.analyze import extract_records, tourism_frame
from src.generate_llm_report import build_prompt


class Chapter141Tests(unittest.TestCase):
    def test_naver_valid_four_keywords(self):
        data = {"results": [
            {"title": x, "data": [{"period": "2026-09-01", "ratio": 42.5}]}
            for x in ("여행", "축제", "캠핑", "맛집")
        ]}
        frame = parse_naver_response(data)
        self.assertEqual(len(frame), 4)
        self.assertAlmostEqual(frame["ratio"].max(), 42.5)

    def test_naver_missing_keyword_rejected(self):
        data = {"results": [{"title": "여행", "data": [{"period": "2026-09-01", "ratio": 42}]}]}
        with self.assertRaises(ValueError):
            parse_naver_response(data)

    def test_naver_ratio_out_of_range(self):
        data = {"results": [
            {"title": x, "data": [{"period": "2026-09-01", "ratio": 120}]}
            for x in ("여행", "축제", "캠핑", "맛집")
        ]}
        with self.assertRaises(ValueError):
            parse_naver_response(data)

    def test_tourism_actual_success_code_0000(self):
        # 실제 관광공사 Swagger 응답 형태: resultCode='0000', items.item 배열
        payload = {"response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {"items": {"item": [
                {"baseYm": "202509", "areaCd": "11", "areaNm": "서울특별시",
                 "tarSjrnDsIxCd": "21", "tarSjrnDsIxVal": "89.81"}
            ]}, "numOfRows": 10, "pageNo": 1, "totalCount": 26},
        }}
        validate_tourism_response(payload)

    def test_tourism_api_error_rejected(self):
        payload = {"response": {"header": {"resultCode": "SERVICE_KEY_IS_NULL"},
                                "body": {"items": {"item": [{"area": "서울"}]}}}}
        with self.assertRaises(RuntimeError):
            validate_tourism_response(payload)

    def test_tourism_no_records_rejected(self):
        with self.assertRaises(ValueError):
            validate_tourism_response({"response": {"header": {"resultCode": "00"}, "body": {}}})

    def test_tourism_records_and_numeric_conversion(self):
        payload = {"response": {"body": {"items": {"item": [
            {"area": "서울", "ym": "202609", "index": "1,200"},
            {"area": "부산", "ym": "202609", "index": "950"}
        ]}}}}
        validate_tourism_response(payload)
        records = extract_records(payload)
        self.assertEqual(len(records), 2)
        df = tourism_frame(payload, {"region": "area", "period": "ym", "value": "index"}, "stay")
        self.assertEqual(df["value"].max(), 1200)

    def test_tourism_field_mapping_must_be_confirmed(self):
        with self.assertRaises(ValueError):
            tourism_frame([{"area": "서울", "ym": "202609", "score": 1}], {
                "region": "", "period": "", "value": ""}, "stay")

    def test_tourism_duplicate_rejected(self):
        rows = [{"area": "서울", "ym": "202609", "score": 1},
                {"area": "서울", "ym": "202609", "score": 2}]
        with self.assertRaises(ValueError):
            tourism_frame(rows, {"region": "area", "period": "ym", "value": "score"}, "stay")

    def test_tourism_aggregate_row_separated(self):
        rows = [
            {"areaNm": "서울특별시", "signguNm": "_", "baseYm": "202509", "v": "89.81"},
            {"areaNm": "서울특별시", "signguNm": "종로구", "baseYm": "202509", "v": "84.26"},
        ]
        mapping = {"region": "signguNm", "period": "baseYm", "value": "v", "area": "areaNm"}
        df = tourism_frame(rows, mapping, "stay")
        self.assertEqual(sorted(df["scope"]), ["시군구", "시도 전체"])
        self.assertIn("서울특별시 전체", set(df["region"]))

    def test_extract_items_single_dict(self):
        data = {"response": {"body": {"items": {"item": {"a": 1}}}}}
        self.assertEqual(extract_items(data), [{"a": 1}])

    def test_tourism_pagination_collects_every_page(self):
        def response(rows):
            return Mock(status_code=200, json=Mock(return_value={"response": {
                "header": {"resultCode": "0000"},
                "body": {"totalCount": 3, "items": {"item": rows}}
            }}))
        with patch("src.collect_tourism.requests.get", side_effect=[
                response([{"id": 1}, {"id": 2}]), response([{"id": 3}])]) as get:
            data = fetch_all_pages("https://example.invalid", "test-key", {"numOfRows": 2}, "stay")
        self.assertEqual(len(extract_items(data)), 3)
        self.assertEqual([c.kwargs["params"]["pageNo"] for c in get.call_args_list], [1, 2])

    def test_tourism_http_error_does_not_reveal_service_key(self):
        secret = "unit-test-secret"
        with patch("src.collect_tourism.requests.get", return_value=Mock(status_code=403)):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403") as caught:
                fetch_all_pages("https://example.invalid", secret, {}, "stay")
        self.assertNotIn(secret, str(caught.exception))

    def test_tourism_network_error_suppresses_sensitive_traceback(self):
        secret = "unit-test-secret"
        with patch("src.collect_tourism.requests.get", side_effect=requests.ConnectionError(
                "https://example.invalid?serviceKey=" + secret)):
            try:
                fetch_all_pages("https://example.invalid", secret, {}, "stay")
            except RuntimeError:
                rendered = traceback.format_exc()
            else:
                self.fail("Network failure was accepted")
        self.assertNotIn(secret, rendered)

    def test_tourism_nonfirst_page_rejected_before_request(self):
        with patch("src.collect_tourism.requests.get") as get:
            with self.assertRaises(ValueError):
                fetch_all_pages("https://example.invalid", "test", {"pageNo": 2}, "stay")
        get.assert_not_called()

    def test_llm_prompt_warns_against_false_comparison(self):
        prompt = build_prompt([{"source": "NAVER", "value": 10}])
        self.assertIn("상대지수", prompt)
        self.assertIn("인과", prompt)
        with self.assertRaises(ValueError):
            build_prompt([])


if __name__ == "__main__":
    unittest.main()
