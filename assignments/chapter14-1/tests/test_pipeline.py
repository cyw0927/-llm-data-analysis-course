"""API 키/외부 네트워크 없이 핵심 데이터 유효성 검증 테스트."""
import unittest

from src.collect_naver import parse_naver_response
from src.collect_tourism import validate_tourism_response
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

    def test_llm_prompt_warns_against_false_comparison(self):
        prompt = build_prompt([{"source": "NAVER", "value": 10}])
        self.assertIn("상대지수", prompt)
        self.assertIn("인과", prompt)
        with self.assertRaises(ValueError):
            build_prompt([])


if __name__ == "__main__":
    unittest.main()
