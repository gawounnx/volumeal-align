"""Cosine retrieval over labeled food reference-image embeddings [FR-004]."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class FoodCandidate:
    food_id: str
    score: float


@dataclass(frozen=True)
class FoodMatch:
    food_id: str
    score: float
    candidates: list[FoodCandidate]
    requires_confirmation: bool


class FoodRetriever:
    def __init__(
        self,
        index_path: str,
        auto_confirm_score: float = 0.80,
        auto_confirm_margin: float = 0.10,
    ):
        if not Path(index_path).is_file():
            raise FileNotFoundError(index_path)
        with np.load(index_path, allow_pickle=False, mmap_mode="r") as index:
            embeddings = np.asarray(index["embeddings"], dtype=np.float32)
            food_ids = np.asarray(index["food_ids"]).astype(str)
        if embeddings.ndim != 2 or len(embeddings) == 0 or len(embeddings) != len(food_ids):
            raise ValueError("음식 임베딩 인덱스의 배열 크기가 올바르지 않습니다.")
        if not np.isfinite(embeddings).all() or any(not value.strip() for value in food_ids):
            raise ValueError("음식 임베딩 인덱스에 유효하지 않은 값이 있습니다.")
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        if np.any(norms <= 0):
            raise ValueError("0 벡터는 음식 임베딩 인덱스에 사용할 수 없습니다.")
        self.embeddings = embeddings / norms
        self.food_ids = food_ids
        self.auto_confirm_score = auto_confirm_score
        self.auto_confirm_margin = auto_confirm_margin

    def search(self, embedding: np.ndarray, top_k: int = 3) -> FoodMatch:
        query = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if len(query) != self.embeddings.shape[1] or not np.isfinite(query).all():
            raise ValueError("검색 임베딩의 차원 또는 값이 올바르지 않습니다.")
        norm = float(np.linalg.norm(query))
        if norm <= 0:
            raise ValueError("0 벡터는 검색할 수 없습니다.")
        similarities = self.embeddings @ (query / norm)
        best_by_food: dict[str, float] = {}
        for food_id, score in zip(self.food_ids, similarities):
            best_by_food[food_id] = max(best_by_food.get(food_id, -1.0), float(score))
        ranked = sorted(best_by_food.items(), key=lambda item: (-item[1], item[0]))
        candidates = [
            FoodCandidate(food_id=food_id, score=round(score, 4))
            for food_id, score in ranked[:max(1, top_k)]
        ]
        first = candidates[0]
        second_score = candidates[1].score if len(candidates) > 1 else -1.0
        requires_confirmation = len(candidates) < 2 or not (
            first.score >= self.auto_confirm_score
            and first.score - second_score >= self.auto_confirm_margin
        )
        return FoodMatch(first.food_id, first.score, candidates, requires_confirmation)
