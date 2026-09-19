"""Provider boundary, foodId mapping, and standard external-error translation."""
import json
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Protocol

import httpx
from PIL import Image

from src.core.exceptions import AppException
from src.schemas.food_recognition import FoodRecognition, NormalizedBoundingBox, NormalizedPoint


class FoodRecognitionProvider(Protocol):
    async def recognize(self, image_bytes: bytes) -> list[FoodRecognition]:
        ...


def _normalized_coordinate(value: float, processed_size: int, original_size: int) -> float:
    del original_size
    return max(0.0, min(1.0, value / processed_size))


def parse_logmeal_response(payload: dict, original_width: int, original_height: int) -> list[FoodRecognition]:
    processed_size = payload.get("processed_image_size") or {}
    processed_width = processed_size.get("width")
    processed_height = processed_size.get("height")
    if not isinstance(processed_width, int) or not isinstance(processed_height, int) or processed_width <= 0 or processed_height <= 0:
        raise AppException(502, "ERR_FOOD_PROVIDER_INVALID_RESPONSE", "외부 음식 인식 서비스의 이미지 크기 응답이 올바르지 않습니다.")

    results: list[FoodRecognition] = []
    for item in payload.get("segmentation_results") or []:
        if not isinstance(item, dict):
            continue
        recognitions = item.get("recognition_results") or []
        best = recognitions[0] if recognitions else None
        if not isinstance(best, dict) or not best.get("name"):
            continue

        points = item.get("polygon") or []
        polygons = None
        if len(points) >= 6 and len(points) % 2 == 0:
            polygons = [[
                NormalizedPoint(
                    x=_normalized_coordinate(points[index], processed_width, original_width),
                    y=_normalized_coordinate(points[index + 1], processed_height, original_height),
                )
                for index in range(0, len(points), 2)
            ]]

        box = item.get("contained_bbox") or {}
        bbox = None
        if all(key in box for key in ("x", "y", "w", "h")) and box["w"] > 0 and box["h"] > 0:
            bbox = NormalizedBoundingBox(
                xmin=_normalized_coordinate(box["x"], processed_width, original_width),
                ymin=_normalized_coordinate(box["y"], processed_height, original_height),
                xmax=_normalized_coordinate(box["x"] + box["w"], processed_width, original_width),
                ymax=_normalized_coordinate(box["y"] + box["h"], processed_height, original_height),
            )
        if polygons is None and bbox is None:
            continue
        results.append(FoodRecognition(
            name=str(best["name"]),
            confidence=float(best.get("prob", 0.0)),
            polygons=polygons,
            bbox=bbox,
            processed_width=processed_width,
            processed_height=processed_height,
            provider_item_id=str(best["id"]) if best.get("id") is not None else None,
        ))
    if not results:
        raise AppException(422, "ERR_FOOD_PROVIDER_EMPTY", "외부 음식 인식 서비스가 음식 영역을 찾지 못했습니다.")
    return results


class LogMealProvider:
    def __init__(self, token: str, base_url: str, timeout_seconds: float = 8.0):
        if not token or not base_url.startswith("https://"):
            raise AppException(503, "ERR_FOOD_PROVIDER_CONFIG", "LogMeal HTTPS URL과 인증 정보를 설정해야 합니다.")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    async def recognize(self, image_bytes: bytes) -> list[FoodRecognition]:
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                original_width, original_height = image.size
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v2/image/segmentation/complete",
                    params={"language": "eng"},
                    headers={"Authorization": f"Bearer {self.token}"},
                    files={"image": ("upload", image_bytes, "application/octet-stream")},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, OSError) as exc:
            raise translate_provider_error(exc) from exc
        return parse_logmeal_response(payload, original_width, original_height)


ENGLISH_FOOD_NAME_MAP = {
    "apple": "apple",
    "banana": "banana",
    "boiled egg": "boiled_egg",
    "bulgogi": "bulgogi",
    "grilled salmon": "grilled_salmon",
    "kimchi stew": "kimchi_stew",
    "soybean paste stew": "soybean_paste_stew",
    "spinach namul": "spinach_namul",
    "white rice": "white_rice",
}


def normalize_food_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"[\\s_-]+", " ", normalized)


class FoodNameMapper:
    """Maps only names whose foodId exists in the complete nutrition contract."""

    def __init__(self, catalog_path: str):
        rows = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise ValueError("food catalog must be a non-empty JSON array")
        self._mapping: dict[str, str] = {}
        supported_ids = {row["foodId"] for row in rows}
        for row in rows:
            food_id = row["foodId"]
            names = [food_id, row["canonicalName"], *row.get("aliases", [])]
            for name in names:
                self._register(name, food_id)
        for name, food_id in ENGLISH_FOOD_NAME_MAP.items():
            if food_id in supported_ids:
                self._register(name, food_id)

    def _register(self, name: str, food_id: str) -> None:
        key = normalize_food_name(name)
        existing = self._mapping.get(key)
        if existing is not None and existing != food_id:
            raise ValueError(f"ambiguous food alias: {name}")
        self._mapping[key] = food_id

    def map_name(self, name: str) -> str:
        food_id = self._mapping.get(normalize_food_name(name))
        if food_id is None:
            raise AppException(
                422,
                "ERR_UNSUPPORTED_FOOD",
                "지원하지 않는 음식이 인식되었습니다. 다른 후보를 선택해 주세요.",
                details=[{"field": "name", "issue": "unsupported_food"}],
            )
        return food_id


def translate_provider_error(exc: Exception) -> AppException:
    """Translate failures without leaking provider payloads or secrets."""
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return AppException(504, "ERR_FOOD_PROVIDER_TIMEOUT", "외부 음식 인식 서비스의 응답 시간이 초과되었습니다.")
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 429:
            return AppException(503, "ERR_FOOD_PROVIDER_RATE_LIMIT", "외부 음식 인식 서비스의 호출 한도를 초과했습니다.")
        if 400 <= status_code < 500:
            return AppException(502, "ERR_FOOD_PROVIDER_REJECTED", "외부 음식 인식 서비스가 요청을 처리하지 못했습니다.")
    return AppException(503, "ERR_FOOD_PROVIDER_UNAVAILABLE", "외부 음식 인식 서비스를 사용할 수 없습니다.")


def require_external_provider_configuration(api_key: str, api_url: str) -> None:
    if not api_key or not api_url or not api_url.startswith("https://"):
        raise AppException(
            503,
            "ERR_FOOD_PROVIDER_CONFIG",
            "외부 음식 인식 서비스의 HTTPS URL과 인증 정보를 설정해야 합니다.",
        )
