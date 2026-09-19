import json
from pathlib import Path
import pytest

from src.services.nutrition_service import NutritionService, NutrientProfile

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def test_aihub_400_nutrition_json_integrity():
    """Verify that aihub_food_nutrients.json was properly generated with valid data."""
    path = BACKEND_ROOT / "data" / "aihub_food_nutrients.json"
    assert path.exists(), f"File {path} does not exist"

    items = json.loads(path.read_text(encoding="utf-8"))
    assert len(items) >= 390, f"Expected ~400 items, got {len(items)}"

    for item in items:
        assert "officialFoodName" in item and len(item["officialFoodName"]) > 0
        assert item["servingWeightG"] > 0
        assert item["basisWeightG"] == 100.0

        p100 = item["nutrientsPer100g"]
        assert p100["caloriesKcal"] >= 0
        assert p100["carbsG"] >= 0
        assert p100["proteinG"] >= 0
        assert p100["fatG"] >= 0
        assert p100["sodiumMg"] >= 0

        # Check for NaN / Inf
        for k, v in p100.items():
            assert not (v != v), f"NaN found in {item['officialFoodName']} {k}"
            assert v != float("inf") and v != float("-inf"), f"Inf found in {item['officialFoodName']} {k}"


def test_food_nutrients_matches_aihub_synced_values():
    """Verify that core target Korean dishes in food_nutrients.json match AI-Hub values."""
    nutrients_path = BACKEND_ROOT / "data" / "food_nutrients.json"
    aihub_path = BACKEND_ROOT / "data" / "aihub_food_nutrients.json"

    nutrients = json.loads(nutrients_path.read_text(encoding="utf-8"))
    aihub_items = json.loads(aihub_path.read_text(encoding="utf-8"))
    aihub_map = {item["officialFoodName"]: item for item in aihub_items}

    target_checks = {
        "white_rice": "쌀밥",
        "spinach_namul": "시금치나물",
        "kimchi_stew": "돼지고기김치찌개",
        "soybean_paste_stew": "된장찌개",
        "bulgogi": "소불고기",
    }

    nutrients_by_id = {n["foodId"]: n for n in nutrients}

    for fid, aihub_name in target_checks.items():
        assert fid in nutrients_by_id, f"foodId {fid} missing from food_nutrients.json"
        entry = nutrients_by_id[fid]
        aihub_src = aihub_map[aihub_name]

        # Verify calories match 100g normalized value
        assert entry["caloriesKcal"] == aihub_src["nutrientsPer100g"]["caloriesKcal"]
        assert entry["carbsG"] == aihub_src["nutrientsPer100g"]["carbsG"]
        assert entry["proteinG"] == aihub_src["nutrientsPer100g"]["proteinG"]
        assert entry["fatG"] == aihub_src["nutrientsPer100g"]["fatG"]
        assert entry["sodiumMg"] == aihub_src["nutrientsPer100g"]["sodiumMg"]
        assert "AI-Hub" in entry["sourceDatabase"]


def test_nutrition_service_with_updated_data_files():
    """Verify that NutritionService successfully initializes and calculates with updated data."""
    catalog_path = str(BACKEND_ROOT / "data" / "food_catalog.json")
    density_path = str(BACKEND_ROOT / "data" / "food_density_profiles.json")
    nutrients_path = str(BACKEND_ROOT / "data" / "food_nutrients.json")

    service = NutritionService(catalog_path, density_path, nutrients_path)

    # Test calculation for white_rice: density is 1.05 g/cm3, 100cm3 = 105g
    # 105g of rice @ 159.43 kcal/100g = 167.40 kcal
    calc = service.calculate("white_rice", 100.0)
    assert calc["foodName"] == "쌀밥"
    assert calc["weightG"] == pytest.approx(105.0, abs=1.0)
    assert calc["caloriesKcal"] == pytest.approx(167.40, abs=2.0)
    assert calc["carbsG"] > 0
    assert calc["proteinG"] > 0

    # Test calculation by weight for apple: 150g apple
    calc_apple = service.calculate_by_weight("apple", 150.0)
    assert calc_apple["foodName"] == "사과"
    assert calc_apple["weightG"] == 150.0
    assert calc_apple["caloriesKcal"] == pytest.approx(85.5, abs=5.0)
