import json

import numpy as np
import pytest

from src.ml.food_retriever import FoodRetriever
from src.services.nutrition_service import NutritionService


def test_retriever_returns_unique_food_top_k_and_confirmation_policy(tmp_path):
    path=tmp_path/"index.npz"
    np.savez(path,embeddings=np.array([[1,0],[.99,.01],[0,1]],np.float32),
             food_ids=np.array(["FOOD_RICE","FOOD_RICE","FOOD_SOUP"]))
    retriever=FoodRetriever(str(path))
    confident=retriever.search(np.array([1,0],np.float32))
    assert [row.food_id for row in confident.candidates]==["FOOD_RICE","FOOD_SOUP"]
    assert confident.requires_confirmation is False
    uncertain=retriever.search(np.array([.72,.69],np.float32))
    assert uncertain.requires_confirmation is True


def test_retriever_does_not_auto_confirm_without_second_candidate(tmp_path):
    path=tmp_path/"index.npz"
    np.savez(path,embeddings=np.array([[1,0]],np.float32),
             food_ids=np.array(["FOOD_RICE"]))
    match=FoodRetriever(str(path)).search(np.array([1,0],np.float32))
    assert match.requires_confirmation is True


def test_nutrition_service_joins_by_food_id_and_basis_weight(tmp_path):
    catalog=[{"foodId":"FOOD_RICE","canonicalName":"백미밥","aliases":["쌀밥"],
              "interactionTags":[]}]
    densities=[{"foodId":"FOOD_RICE","densityGCm3":.8,"densityStd":.08,
                "preparation":"cooked","source":"measured calibration"}]
    nutrients=[{"foodId":"FOOD_RICE","basisWeightG":100,"caloriesKcal":130,
                "carbsG":28.6,"proteinG":2.4,"fatG":.3,"sodiumMg":1,
                "sourceFoodCode":"test-code","sourceVersion":"test"}]
    paths=[]
    for name,rows in (("catalog",catalog),("density",densities),("nutrients",nutrients)):
        path=tmp_path/f"{name}.json";path.write_text(json.dumps(rows));paths.append(str(path))
    result=NutritionService(*paths).calculate("FOOD_RICE",180)
    assert result["weightG"]==144
    assert result["caloriesKcal"]==187.2
    assert result["carbsG"]==pytest.approx(41.18,abs=.01)


def test_nutrition_service_rejects_mismatched_food_ids(tmp_path):
    rows=[
        [{"foodId":"A","canonicalName":"A","aliases":[],"interactionTags":[]}],
        [{"foodId":"B","densityGCm3":1,"densityStd":0,"preparation":"cooked","source":"test"}],
        [{"foodId":"A","basisWeightG":100,"caloriesKcal":1,"carbsG":1,
          "proteinG":1,"fatG":1,"sodiumMg":1,"sourceFoodCode":"x","sourceVersion":"test"}],
    ]
    paths=[]
    for index,value in enumerate(rows):
        path=tmp_path/f"{index}.json";path.write_text(json.dumps(value));paths.append(str(path))
    with pytest.raises(ValueError,match="foodId"):
        NutritionService(*paths)
