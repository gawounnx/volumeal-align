"""Food-ID based density, weight and nutrient conversion [FR-004]."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class StrictData(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class FoodCatalogEntry(StrictData):
    foodId: str = Field(min_length=1)
    canonicalName: str = Field(min_length=1)
    aliases: list[str] = []
    interactionTags: list[str] = []


class DensityProfile(StrictData):
    foodId: str = Field(min_length=1)
    densityGCm3: float = Field(gt=0)
    densityStd: float = Field(ge=0)
    preparation: str = Field(min_length=1)
    source: str = Field(min_length=1)
    protocol: str = Field(default="water_displacement_pycnometer_n10")
    sampleCount: int = Field(default=10, ge=1)
    measuredAt: str = Field(default="2026-09-10")


class NutrientProfile(StrictData):
    foodId: str = Field(min_length=1)
    basisWeightG: float = Field(gt=0)
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)
    sourceFoodCode: str = Field(min_length=1)
    sourceVersion: str = Field(min_length=1)
    officialFoodName: str = Field(default="")
    sourceDatabase: str = Field(default="")
    sourceUrl: str = Field(default="")
    retrievedAt: str = Field(default="")


def _load_rows(path: str, schema):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("데이터 파일은 비어 있지 않은 JSON 배열이어야 합니다.")
    parsed = [schema.model_validate(row) for row in rows]
    keyed = {row.foodId: row for row in parsed}
    if len(keyed) != len(parsed):
        raise ValueError("foodId가 중복되었습니다.")
    return keyed


class NutritionService:
    def __init__(self, catalog_path: str, density_path: str, nutrients_path: str):
        self.catalog = _load_rows(catalog_path, FoodCatalogEntry)
        self.densities = _load_rows(density_path, DensityProfile)
        self.nutrients = _load_rows(nutrients_path, NutrientProfile)
        if set(self.catalog) != set(self.densities) or set(self.catalog) != set(self.nutrients):
            raise ValueError("catalog, density, nutrient 데이터의 foodId 집합이 일치해야 합니다.")

    def food_name(self, food_id: str) -> str:
        return self.catalog[food_id].canonicalName

    def calculate(self, food_id: str, volume_cm3: float) -> dict:
        catalog = self.catalog[food_id]
        density = self.densities[food_id]
        nutrient = self.nutrients[food_id]
        weight = volume_cm3 * density.densityGCm3
        ratio = weight / nutrient.basisWeightG
        return {
            "foodId": food_id,
            "foodName": catalog.canonicalName,
            "densityGCm3": density.densityGCm3,
            "densityStd": density.densityStd,
            "weightG": round(weight, 2),
            **{
                key: round(getattr(nutrient, key) * ratio, 2)
                for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
            },
            "interactionTags": [value.lower() for value in catalog.interactionTags],
        }

    def calculate_by_weight(self, food_id: str, weight_g: float) -> dict:
        """[FR-007, BR-VAL-004] 수정 중량 기반 SSOT 정밀 비례 재계산."""
        catalog = self.catalog[food_id]
        density = self.densities[food_id]
        nutrient = self.nutrients[food_id]
        ratio = weight_g / nutrient.basisWeightG
        volume_cm3 = weight_g / density.densityGCm3 if density.densityGCm3 > 0 else 0.0
        return {
            "foodId": food_id,
            "foodName": catalog.canonicalName,
            "densityGCm3": density.densityGCm3,
            "densityStd": density.densityStd,
            "volumeCm3": round(volume_cm3, 2),
            "weightG": round(weight_g, 2),
            **{
                key: round(getattr(nutrient, key) * ratio, 2)
                for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
            },
            "interactionTags": [value.lower() for value in catalog.interactionTags],
        }
