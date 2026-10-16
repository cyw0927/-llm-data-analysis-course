"""네트워크/DB 연결 없이 Chapter 14-2 데이터 정규화 검증."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seed"))
from prepare_seed import (
    canonical_code, reference_date, numeric, tourism_csv_frame,
    unwrap_tourism_json, tourism_json_frame, combine_tourism,
    naver_frame, places_frame,
)


class TestSeed(unittest.TestCase):
    def test_month_to_date(self):
        self.assertEqual(reference_date("202509"), "2025-09-01")
        self.assertEqual(reference_date("2025-09"), "2025-09-01")
        self.assertEqual(reference_date("2025-09-18"), "2025-09-18")

    def test_region_code(self):
        self.assertEqual(canonical_code(11.0), "11")
        self.assertEqual(canonical_code("01110"), "01110")

    def test_numeric(self):
        self.assertEqual(numeric("1,234.50"), 1234.5)
        self.assertIsNone(numeric(""))
        with self.assertRaises(ValueError):
            numeric("not numeric")

    def test_tourism_csv_no_fake_zero(self):
        df = tourism_csv_frame(pd.DataFrame([
            {"reference_date": "202509", "region_code": "11",
             "stay_strength": 89.81, "consumption_strength": None}
        ]))
        self.assertEqual(len(df), 1)
        self.assertTrue(pd.isna(df.iloc[0]["consumption_strength"]))

    def test_tourism_csv_duplicate_detect(self):
        df = pd.DataFrame([
            {"reference_date": "202509", "region_code": "11",
             "stay_strength": 10, "consumption_strength": 20},
            {"reference_date": "202509", "region_code": "11",
             "stay_strength": 12, "consumption_strength": 22},
        ])
        with self.assertRaises(ValueError):
            tourism_csv_frame(df)

    def test_real_stay_json_fields(self):
        payload = {"response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {"items": {"item": [
                {"baseYm": "202509", "areaCd": "11", "areaNm": "서울특별시",
                 "signguCd": "0", "signguNm": "_", "tarSjrnDsIxVal": "89.81"},
                {"baseYm": "202509", "areaCd": "11", "areaNm": "서울특별시",
                 "signguCd": "11110", "signguNm": "종로구", "tarSjrnDsIxVal": "84.26"},
            ]}, "totalCount": 2}
        }}
        mapping = {"period": "baseYm", "area_code": "areaCd",
                   "district_code": "signguCd", "value": "tarSjrnDsIxVal"}
        out, regions = tourism_json_frame(payload, mapping, "stay_strength")
        self.assertEqual(out["region_code"].tolist(), ["11", "11110"])
        self.assertEqual(regions["region_name"].tolist(), ["서울특별시", "종로구"])

    def test_partial_api_page_rejected(self):
        payload = {"response": {
            "header": {"resultCode": "0000"},
            "body": {"items": {"item": [{"baseYm": "202509"}]}, "totalCount": 26}
        }}
        with self.assertRaises(ValueError):
            unwrap_tourism_json(payload)

    def test_missing_consumption_mapping_rejected(self):
        payload = {"response": {"header": {"resultCode": "0000"},
                                "body": {"items": {"item": [{"baseYm": "202509"}]}, "totalCount": 1}}}
        with self.assertRaises(ValueError):
            tourism_json_frame(payload, {"period": "baseYm", "value": ""},
                               "consumption_strength")

    def test_combine_preserves_unmatched(self):
        a = pd.DataFrame([{"reference_date": "2025-09-01", "region_code": "11",
                           "stay_strength": 89.81}])
        b = pd.DataFrame([{"reference_date": "2025-09-01", "region_code": "11110",
                           "consumption_strength": 119.08}])
        out = combine_tourism(a, b)
        self.assertEqual(len(out), 2)
        self.assertEqual(out["consumption_strength"].isna().sum(), 1)

    def test_naver_ratio_and_unique(self):
        df = naver_frame(pd.DataFrame([{"period": "2025-10-01", "keyword": "여행", "ratio": 88.5}]))
        self.assertEqual(float(df.iloc[0]["ratio"]), 88.5)
        with self.assertRaises(ValueError):
            naver_frame(pd.DataFrame([{"period": "2025-10-01", "keyword": "여행", "ratio": 250}]))

    def test_naver_local_html_and_coords(self):
        out = places_frame([{
            "region_code": "11", "search_category": "카페",
            "title": "<b>서울</b> 카페", "roadAddress": "서울특별시 중구",
            "category": "카페", "mapx": "126.978", "mapy": "37.5665"
        }])
        self.assertEqual(out.iloc[0]["name"], "서울 카페")
        self.assertAlmostEqual(out.iloc[0]["longitude"], 126.978)

    def test_local_without_context_rejected(self):
        with self.assertRaises(ValueError):
            places_frame([{"title": "장소", "mapx": "126", "mapy": "37"}])


if __name__ == "__main__":
    unittest.main()
