import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seed"))
from collect_local_places import enrich_items, normalize_coordinates


class TestLocalCollection(unittest.TestCase):
    def test_decimal_and_scaled_coordinates(self):
        self.assertEqual(normalize_coordinates("126.978", "37.5665"), (126.978, 37.5665))
        self.assertEqual(normalize_coordinates("1269780000", "375665000"), (126.978, 37.5665))

    def test_reversed_or_corrupt_coordinate_pair_rejected(self):
        for lon, lat in [(37.5, 127), (1000, 1000), (float("nan"), 37.5)]:
            with self.assertRaises(ValueError):
                normalize_coordinates(lon, lat)

    def test_district_code_comes_from_real_address(self):
        regions = [{"region_name": "서울특별시", "region_code": "11"}, {"region_name": "중구", "region_code": "11140"}]
        result = enrich_items({"items": [{"title": "검증용 장소", "roadAddress": "서울특별시 중구 세종대로 1", "mapx": "126.978", "mapy": "37.5665"}]}, "관광명소", regions)
        self.assertEqual(result[0]["region_code"], "11140")
        self.assertEqual(result[0]["search_category"], "관광명소")

    def test_unknown_or_other_city_is_not_assigned_to_seoul(self):
        for address in ("부산광역시 중구", "서울특별시 알수없는구"):
            with self.assertRaises(ValueError):
                enrich_items({"items": [{"roadAddress": address}]}, "카페", [{"region_name": "중구", "region_code": "11140"}])


if __name__ == "__main__":
    unittest.main()
