"""Parse AI-Hub 122 dataset Nutrition DB (44.음식분류 AI 데이터 영양DB.xlsx)

Generates:
1. backend/data/aihub_food_nutrients.json (All 400 food items with serving & 100g basis)
2. Updates backend/data/food_nutrients.json for target Korean dishes using AI-Hub official values
[FR-005, FR-006]
"""

import json
import os
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AIHUB_DATA_DIR = BACKEND_ROOT.parent / "aihub_data"
DEFAULT_OUTPUT_DIR = BACKEND_ROOT / "data"


def extract_if_needed(aihub_dir: Path, target_dir: Path) -> Path:
    """Extracts food_nutrition_db.tar if .xlsx.part0 is not already extracted."""
    # Check if already extracted
    candidates = list(target_dir.glob("**/44.음식분류*영양DB.xlsx*"))
    if candidates and candidates[0].exists():
        return candidates[0]

    tar_path = aihub_dir / "food_nutrition_db.tar"
    if not tar_path.exists():
        raise FileNotFoundError(f"AI Hub nutrition DB tar archive not found at {tar_path}")

    print(f"Extracting {tar_path} to {target_dir}...")
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(path=target_dir)

    candidates = list(target_dir.glob("**/44.음식분류*영양DB.xlsx*"))
    if not candidates:
        raise FileNotFoundError("Failed to locate extracted 44.음식분류 AI 데이터 영양DB.xlsx")
    return candidates[0]


def parse_xlsx_pure_python(xlsx_path: Path) -> list[dict]:
    """Parses Excel .xlsx file without external dependencies (pure python zipfile + xml)."""
    with zipfile.ZipFile(str(xlsx_path), "r") as z:
        # 1. Parse Shared Strings
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                shared_strings.append(t.text if t is not None else "")

        # 2. Parse Sheet 1
        sheet1_xml = z.read("xl/worksheets/sheet1.xml")
        sheet_tree = ET.fromstring(sheet1_xml)
        rows = sheet_tree.findall(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"
        )

        raw_rows = []
        for r in rows:
            row_vals = []
            for c in r.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                t_attr = c.attrib.get("t")
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = v.text if v is not None else ""
                if t_attr == "s" and val.isdigit():
                    val = shared_strings[int(val)]
                row_vals.append(val.strip())
            if row_vals:
                raw_rows.append(row_vals)

    if not raw_rows:
        raise ValueError("Excel file contains no rows.")

    headers = raw_rows[0]
    print(f"Headers found: {headers}")

    col_map = {
        "food_name": 0,
        "serving_weight_g": 1,
        "calories_kcal": 2,
        "carbs_g": 3,
        "sugar_g": 4,
        "fat_g": 5,
        "protein_g": 6,
        "calcium_mg": 7,
        "phosphorus_mg": 8,
        "sodium_mg": 9,
        "potassium_mg": 10,
        "magnesium_mg": 11,
        "iron_mg": 12,
        "zinc_mg": 13,
        "cholesterol_mg": 14,
        "trans_fat_g": 15,
    }

    def safe_float(val: str, default: float = 0.0) -> float:
        val = val.strip()
        if not val or val in ("-", "N/A", "nan", "None", "."):
            return default
        try:
            return float(val)
        except ValueError:
            return default

    results = []
    for r in raw_rows[1:]:
        if not r or not r[0]:
            continue

        name = r[col_map["food_name"]]
        serving_g = safe_float(r[col_map["serving_weight_g"]] if len(r) > 1 else "100.0", default=100.0)
        if serving_g <= 0:
            serving_g = 100.0

        cal = safe_float(r[col_map["calories_kcal"]] if len(r) > 2 else "0.0")
        carbs = safe_float(r[col_map["carbs_g"]] if len(r) > 3 else "0.0")
        sugar = safe_float(r[col_map["sugar_g"]] if len(r) > 4 else "0.0")
        fat = safe_float(r[col_map["fat_g"]] if len(r) > 5 else "0.0")
        protein = safe_float(r[col_map["protein_g"]] if len(r) > 6 else "0.0")
        calcium = safe_float(r[col_map["calcium_mg"]] if len(r) > 7 else "0.0")
        phosphorus = safe_float(r[col_map["phosphorus_mg"]] if len(r) > 8 else "0.0")
        sodium = safe_float(r[col_map["sodium_mg"]] if len(r) > 9 else "0.0")
        potassium = safe_float(r[col_map["potassium_mg"]] if len(r) > 10 else "0.0")
        magnesium = safe_float(r[col_map["magnesium_mg"]] if len(r) > 11 else "0.0")
        iron = safe_float(r[col_map["iron_mg"]] if len(r) > 12 else "0.0")
        zinc = safe_float(r[col_map["zinc_mg"]] if len(r) > 13 else "0.0")
        cholesterol = safe_float(r[col_map["cholesterol_mg"]] if len(r) > 14 else "0.0")
        trans_fat = safe_float(r[col_map["trans_fat_g"]] if len(r) > 15 else "0.0")

        # 100g normalized ratio
        norm_factor = 100.0 / serving_g

        item = {
            "officialFoodName": name,
            "servingWeightG": round(serving_g, 2),
            "nutrientsPerServing": {
                "caloriesKcal": round(cal, 2),
                "carbsG": round(carbs, 2),
                "sugarG": round(sugar, 2),
                "fatG": round(fat, 2),
                "proteinG": round(protein, 2),
                "sodiumMg": round(sodium, 2),
                "calciumMg": round(calcium, 2),
                "phosphorusMg": round(phosphorus, 2),
                "potassiumMg": round(potassium, 2),
                "magnesiumMg": round(magnesium, 2),
                "ironMg": round(iron, 2),
                "zincMg": round(zinc, 2),
                "cholesterolMg": round(cholesterol, 2),
                "transFatG": round(trans_fat, 2),
            },
            "basisWeightG": 100.0,
            "nutrientsPer100g": {
                "caloriesKcal": round(cal * norm_factor, 2),
                "carbsG": round(carbs * norm_factor, 2),
                "sugarG": round(sugar * norm_factor, 2),
                "fatG": round(fat * norm_factor, 2),
                "proteinG": round(protein * norm_factor, 2),
                "sodiumMg": round(sodium * norm_factor, 2),
                "calciumMg": round(calcium * norm_factor, 2),
                "phosphorusMg": round(phosphorus * norm_factor, 2),
                "potassiumMg": round(potassium * norm_factor, 2),
                "magnesiumMg": round(magnesium * norm_factor, 2),
                "ironMg": round(iron * norm_factor, 2),
                "zincMg": round(zinc * norm_factor, 2),
                "cholesterolMg": round(cholesterol * norm_factor, 2),
                "transFatG": round(trans_fat * norm_factor, 2),
            },
            "sourceDatabase": "AI-Hub 음식 이미지 및 영양정보 (122번 칼로리데이터셋)",
            "sourceVersion": "AI-Hub 44.음식분류 AI 데이터 영양DB v1.0",
            "sourceUrl": "https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&aihubDataSe=realm&dataSetSn=122",
            "retrievedAt": "2026-09-18",
        }
        results.append(item)

    return results


def sync_core_food_nutrients(aihub_items: list[dict], food_nutrients_path: Path):
    """Updates backend/data/food_nutrients.json for core supported foods with AI-Hub values."""
    if not food_nutrients_path.exists():
        raise FileNotFoundError(f"Target file {food_nutrients_path} not found")

    existing_nutrients = json.loads(food_nutrients_path.read_text(encoding="utf-8"))
    aihub_by_name = {item["officialFoodName"]: item for item in aihub_items}

    # Mapping target foodIds to AI-Hub official food names
    target_mapping = {
        "white_rice": "쌀밥",
        "spinach_namul": "시금치나물",
        "kimchi_stew": "돼지고기김치찌개",
        "soybean_paste_stew": "된장찌개",
        "bulgogi": "소불고기",
    }

    updated_count = 0
    for entry in existing_nutrients:
        fid = entry.get("foodId")
        if fid in target_mapping:
            match_name = target_mapping[fid]
            if match_name in aihub_by_name:
                src = aihub_by_name[match_name]
                p100 = src["nutrientsPer100g"]
                entry["basisWeightG"] = 100.0
                entry["caloriesKcal"] = p100["caloriesKcal"]
                entry["carbsG"] = p100["carbsG"]
                entry["proteinG"] = p100["proteinG"]
                entry["fatG"] = p100["fatG"]
                entry["sodiumMg"] = p100["sodiumMg"]
                entry["officialFoodName"] = src["officialFoodName"]
                entry["sourceDatabase"] = src["sourceDatabase"]
                entry["sourceVersion"] = src["sourceVersion"]
                entry["sourceUrl"] = src["sourceUrl"]
                entry["retrievedAt"] = src["retrievedAt"]
                updated_count += 1
                print(f"[SYNC] {fid} -> '{match_name}': {p100['caloriesKcal']} kcal / 100g")

    food_nutrients_path.write_text(json.dumps(existing_nutrients, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Successfully updated {updated_count} core food items in {food_nutrients_path}")


def main():
    aihub_data_dir = DEFAULT_AIHUB_DATA_DIR
    target_extract_dir = BACKEND_ROOT / "data" / "aihub_nutrition"
    target_extract_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = extract_if_needed(aihub_data_dir, target_extract_dir)
    print(f"Found Excel DB at: {xlsx_path}")

    all_foods = parse_xlsx_pure_python(xlsx_path)
    print(f"Parsed {len(all_foods)} food items from AI-Hub DB.")

    # 1. Save all 400 items
    all_output_path = DEFAULT_OUTPUT_DIR / "aihub_food_nutrients.json"
    all_output_path.write_text(json.dumps(all_foods, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved full AI-Hub nutrition DB (400 items) to {all_output_path}")

    # 2. Sync core food items in food_nutrients.json
    core_nutrients_path = DEFAULT_OUTPUT_DIR / "food_nutrients.json"
    sync_core_food_nutrients(all_foods, core_nutrients_path)


if __name__ == "__main__":
    main()
