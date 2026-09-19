# FR-008 적용 코드

기존 파일은 작업 시작 시점 원문을 SEARCH로, 적용한 전체 파일을 REPLACE로 제공합니다. 이미 적용된 변경이므로 다시 적용할 필요는 없습니다.

## backend/src/schemas/vision.py

```text
파일 경로: backend/src/schemas/vision.py
<<<<<<< SEARCH
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, AliasChoices


class StrictModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class BoundingBox2D(StrictModel):
    ymin: float = Field(..., ge=0.0, le=1.0)
    xmin: float = Field(..., ge=0.0, le=1.0)
    ymax: float = Field(..., ge=0.0, le=1.0)
    xmax: float = Field(..., ge=0.0, le=1.0)


    @model_validator(mode="after")
    def ordered(self):
        if self.xmin > self.xmax or self.ymin > self.ymax:
            raise ValueError("Bounding box coordinates must be ordered")
        return self


class Point3D(StrictModel):
    x: float
    y: float
    z: float


class BoundingBox3D(StrictModel):
    center: Point3D
    dimensions: Point3D
    rotations: Point3D
    vertices: List[Point3D]

class FoodCandidate(StrictModel):
    foodId: str
    foodName: str
    score: float = Field(..., ge=-1.0, le=1.0)
    densityGCm3: Optional[float] = Field(default=None, gt=0)
    weightG: Optional[float] = Field(default=None, gt=0)
    caloriesKcal: Optional[float] = Field(default=None, ge=0)
    carbsG: Optional[float] = Field(default=None, ge=0)
    proteinG: Optional[float] = Field(default=None, ge=0)
    fatG: Optional[float] = Field(default=None, ge=0)
    sodiumMg: Optional[float] = Field(default=None, ge=0)


class PlaneEquation(StrictModel):
    a: float
    b: float
    c: float
    d: float


class FoodItemEstimation(StrictModel):
    id: str
    foodId: str
    foodName: str
    confidenceScore: float = Field(..., ge=0.0, le=1.0)
    classificationConfidence: float = Field(..., ge=-1.0, le=1.0)
    geometryConfidence: float = Field(..., ge=0.0, le=1.0)
    requiresConfirmation: bool
    topCandidates: List[FoodCandidate] = Field(..., min_length=1, max_length=3)
    volumeCm3: float = Field(ge=5, le=5000)
    densityGCm3: float = Field(gt=0)
    weightG: float = Field(gt=0)
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)
    bbox2d: BoundingBox2D
    bbox3d: BoundingBox3D


class DrugInteractionWarning(StrictModel):
    id: str
    drugBrandName: str
    drugIngredient: str
    triggerNutrientOrFood: str
    riskLevel: str
    detectedVia: str
    warningTitle: str
    warningMessage: str
    actionGuide: str


class SparsePointCloudPayload(StrictModel):
    count: int = Field(ge=0, le=5000)
    positions: List[float]
    colors: List[float]


    @model_validator(mode="after")
    def lengths_match(self):
        if len(self.positions) != 3*self.count or len(self.colors) != 3*self.count:
            raise ValueError("Point count must match positions and colors")
        if any(v < 0 or v > 1 for v in self.colors):
            raise ValueError("Point colors must be normalized")
        return self


class Visualization3D(StrictModel):
    pointCloud: SparsePointCloudPayload


class NutritionSummary(StrictModel):
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)


class MealEstimateResponse(StrictModel):
    mealId: str
    isPersisted: bool
    requiresConfirmation: bool
    imageUrl: str
    isCalibrated: bool
    focalLengthMm: float = Field(gt=0)
    groundPlane: PlaneEquation
    totalNutrition: NutritionSummary
    foodItems: List[FoodItemEstimation]
    drugWarnings: List[DrugInteractionWarning]
    visualization3d: Visualization3D
    processedAt: str
    inferenceLatencyMs: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)

class VisionEstimateEnvelope(StrictModel):
    success: Literal[True] = True
    data: MealEstimateResponse


class ConfirmedFoodSelection(StrictModel):
    itemId: str = Field(..., description="확정 대상 음식 항목 식별자 (UUID)")
    foodId: str = Field(..., description="사용자가 선택한 식품 ID")
    volumeCm3: Optional[float] = Field(default=None, ge=5, le=5000, description="기측정된 부피 (cm³)")
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class FoodItemVolumeData(StrictModel):
    itemId: Optional[str] = None
    id: Optional[str] = None
    foodId: Optional[str] = None
    volumeCm3: float = Field(ge=5, le=5000)
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class DetectedPillInput(StrictModel):
    class_name: str
    class_id: Optional[int] = None
    confidence: Optional[float] = None
    box: Optional[List[float]] = None


class VisionConfirmRequest(StrictModel):
    mealId: Optional[str] = Field(default=None, description="임시 분석 식별자 (UUID)")
    imageUrl: Optional[str] = Field(default="", description="식단 이미지 URL")
    focalLengthMm: float = Field(default=26.0, gt=0, le=1000, description="35mm 환산 초점거리")
    isCalibrated: bool = Field(default=False, description="깊이 스케일 보정 여부")
    confirmedItems: List[ConfirmedFoodSelection] = Field(
        default=[],
        validation_alias=AliasChoices("confirmedItems", "confirmedFoods", "selectedFoods", "selections", "confirmed_items"),
        description="사용자가 확정한 [{ itemId, foodId }] 리스트"
    )
    volumeData: Optional[List[FoodItemVolumeData]] = Field(
        default=None,
        validation_alias=AliasChoices("volumeData", "foodItems", "volume_data"),
        description="부피 데이터 목록"
    )
    detectedPills: Optional[List[DetectedPillInput]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("detectedPills", "detected_pills"),
        description="감지된 알약 목록"
    )

    @model_validator(mode="after")
    def validate_confirmed_items(self):
        if not self.confirmedItems:
            raise ValueError("확정할 음식 항목(confirmedItems)이 최소 1개 이상 필요합니다.")
        return self


class ConfirmedFoodItemDetail(StrictModel):
    id: str
    foodId: str
    foodName: str
    confidenceScore: float = Field(ge=0.0, le=1.0)
    volumeCm3: float = Field(ge=5, le=5000)
    densityGCm3: float = Field(gt=0)
    weightG: float = Field(gt=0)
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)
    bbox2d: BoundingBox2D
    bbox3d: BoundingBox3D


class MealConfirmData(StrictModel):
    mealId: str
    isPersisted: Literal[True] = True
    totalNutrition: NutritionSummary
    foodItems: List[ConfirmedFoodItemDetail]
    drugWarnings: List[DrugInteractionWarning]
    processedAt: str


class VisionConfirmResponse(StrictModel):
    success: Literal[True] = True
    mealId: str
    totalNutrition: NutritionSummary
    drugWarnings: List[DrugInteractionWarning]
    data: MealConfirmData

    model_config = ConfigDict(from_attributes=True)
=======
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, AliasChoices


class StrictModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class BoundingBox2D(StrictModel):
    ymin: float = Field(..., ge=0.0, le=1.0)
    xmin: float = Field(..., ge=0.0, le=1.0)
    ymax: float = Field(..., ge=0.0, le=1.0)
    xmax: float = Field(..., ge=0.0, le=1.0)


    @model_validator(mode="after")
    def ordered(self):
        if self.xmin > self.xmax or self.ymin > self.ymax:
            raise ValueError("Bounding box coordinates must be ordered")
        return self


class Point3D(StrictModel):
    x: float
    y: float
    z: float


class BoundingBox3D(StrictModel):
    center: Point3D
    dimensions: Point3D
    rotations: Point3D
    vertices: List[Point3D]

class FoodCandidate(StrictModel):
    foodId: str
    foodName: str
    score: float = Field(..., ge=-1.0, le=1.0)
    densityGCm3: Optional[float] = Field(default=None, gt=0)
    weightG: Optional[float] = Field(default=None, gt=0)
    caloriesKcal: Optional[float] = Field(default=None, ge=0)
    carbsG: Optional[float] = Field(default=None, ge=0)
    proteinG: Optional[float] = Field(default=None, ge=0)
    fatG: Optional[float] = Field(default=None, ge=0)
    sodiumMg: Optional[float] = Field(default=None, ge=0)


class PlaneEquation(StrictModel):
    a: float
    b: float
    c: float
    d: float


class FoodItemEstimation(StrictModel):
    id: str
    foodId: str
    foodName: str
    confidenceScore: float = Field(..., ge=0.0, le=1.0)
    classificationConfidence: float = Field(..., ge=-1.0, le=1.0)
    geometryConfidence: float = Field(..., ge=0.0, le=1.0)
    requiresConfirmation: bool
    topCandidates: List[FoodCandidate] = Field(..., min_length=1, max_length=3)
    volumeCm3: float = Field(ge=5, le=5000)
    densityGCm3: float = Field(gt=0)
    weightG: float = Field(gt=0)
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)
    bbox2d: BoundingBox2D
    bbox3d: BoundingBox3D


class DrugInteractionWarning(StrictModel):
    id: str
    drugBrandName: str
    drugIngredient: str
    triggerNutrientOrFood: str
    riskLevel: str
    detectedVia: str
    warningTitle: str
    warningMessage: str
    actionGuide: str


class SparsePointCloudPayload(StrictModel):
    count: int = Field(ge=0, le=5000)
    positions: List[float]
    colors: List[float]


    @model_validator(mode="after")
    def lengths_match(self):
        if len(self.positions) != 3*self.count or len(self.colors) != 3*self.count:
            raise ValueError("Point count must match positions and colors")
        if any(v < 0 or v > 1 for v in self.colors):
            raise ValueError("Point colors must be normalized")
        return self


class Visualization3D(StrictModel):
    pointCloud: SparsePointCloudPayload


class NutritionSummary(StrictModel):
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)


class DetectedPillInput(StrictModel):
    class_name: str
    class_id: Optional[int] = None
    confidence: Optional[float] = None
    box: Optional[List[float]] = None


class MealEstimateResponse(StrictModel):
    mealId: str
    isPersisted: bool
    requiresConfirmation: bool
    imageUrl: str
    isCalibrated: bool
    focalLengthMm: float = Field(gt=0)
    groundPlane: PlaneEquation
    totalNutrition: NutritionSummary
    foodItems: List[FoodItemEstimation]
    drugWarnings: List[DrugInteractionWarning]
    detectedPills: List[DetectedPillInput] = Field(default_factory=list)
    visualization3d: Visualization3D
    processedAt: str
    inferenceLatencyMs: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)

class VisionEstimateEnvelope(StrictModel):
    success: Literal[True] = True
    data: MealEstimateResponse


class ConfirmedFoodSelection(StrictModel):
    itemId: str = Field(..., description="확정 대상 음식 항목 식별자 (UUID)")
    foodId: str = Field(..., description="사용자가 선택한 식품 ID")
    weightG: Optional[float] = Field(default=None, gt=0, description="사용자 보정 중량(g) [FR-008]")
    volumeCm3: Optional[float] = Field(default=None, ge=5, le=5000, description="기측정된 부피 (cm³)")
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class FoodItemVolumeData(StrictModel):
    itemId: Optional[str] = None
    id: Optional[str] = None
    foodId: Optional[str] = None
    volumeCm3: float = Field(ge=5, le=5000)
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class VisionConfirmRequest(StrictModel):
    mealId: Optional[str] = Field(default=None, description="임시 분석 식별자 (UUID)")
    imageUrl: Optional[str] = Field(default="", description="식단 이미지 URL")
    focalLengthMm: float = Field(default=26.0, gt=0, le=1000, description="35mm 환산 초점거리")
    isCalibrated: bool = Field(default=False, description="깊이 스케일 보정 여부")
    confirmedItems: List[ConfirmedFoodSelection] = Field(
        default=[],
        validation_alias=AliasChoices("confirmedItems", "confirmedFoods", "selectedFoods", "selections", "confirmed_items"),
        description="사용자가 확정한 [{ itemId, foodId }] 리스트"
    )
    volumeData: Optional[List[FoodItemVolumeData]] = Field(
        default=None,
        validation_alias=AliasChoices("volumeData", "foodItems", "volume_data"),
        description="부피 데이터 목록"
    )
    detectedPills: Optional[List[DetectedPillInput]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("detectedPills", "detected_pills"),
        description="감지된 알약 목록"
    )

    @model_validator(mode="after")
    def validate_confirmed_items(self):
        if not self.confirmedItems:
            raise ValueError("확정할 음식 항목(confirmedItems)이 최소 1개 이상 필요합니다.")
        return self


class ConfirmedFoodItemDetail(StrictModel):
    id: str
    foodId: str
    foodName: str
    confidenceScore: float = Field(ge=0.0, le=1.0)
    volumeCm3: float = Field(ge=5, le=5000)
    densityGCm3: float = Field(gt=0)
    weightG: float = Field(gt=0)
    caloriesKcal: float = Field(ge=0)
    carbsG: float = Field(ge=0)
    proteinG: float = Field(ge=0)
    fatG: float = Field(ge=0)
    sodiumMg: float = Field(ge=0)
    bbox2d: BoundingBox2D
    bbox3d: BoundingBox3D


class MealConfirmData(StrictModel):
    mealId: str
    isPersisted: Literal[True] = True
    totalNutrition: NutritionSummary
    foodItems: List[ConfirmedFoodItemDetail]
    drugWarnings: List[DrugInteractionWarning]
    processedAt: str


class VisionConfirmResponse(StrictModel):
    success: Literal[True] = True
    mealId: str
    totalNutrition: NutritionSummary
    drugWarnings: List[DrugInteractionWarning]
    data: MealConfirmData

    model_config = ConfigDict(from_attributes=True)
>>>>>>> REPLACE
```

## backend/src/api/v1/endpoints/vision.py

```text
파일 경로: backend/src/api/v1/endpoints/vision.py
<<<<<<< SEARCH
import asyncio
import io
import time
import uuid
import warnings
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_current_user
from src.core.config import settings
from src.core.database import get_db_session
from src.core.exceptions import AppException
from src.ml.onnx_segmentor import YoloV8Segmentor
from src.ml.onnx_depth_estimator import DepthAnythingV2Estimator
from src.ml.patch_embedder import PatchEmbedder
from src.ml.food_retriever import FoodRetriever
from src.models.entities import Drug, User, UserMedication, DrugFoodContraindication, Meal, MealFoodItem, MealDrugWarning
from src.schemas.vision import (
    VisionEstimateEnvelope,
    VisionConfirmRequest,
    VisionConfirmResponse,
    BoundingBox2D,
    BoundingBox3D,
    Point3D,
)
from src.services.vision_pipeline import VisionPipelineOrchestrator
from src.services.nutrition_service import NutritionService
from src.services.drug_interaction_service import DrugInteractionService

router = APIRouter(tags=["vision"])
inference_semaphore = asyncio.Semaphore(5)

@lru_cache(maxsize=1)
def get_nutrition_service() -> NutritionService:
    try:
        return NutritionService(
            settings.FOOD_CATALOG_PATH, settings.FOOD_DENSITY_PATH, settings.FOOD_NUTRIENTS_PATH
        )
    except Exception as exc:
        raise AppException(503, "ERR_NUTRITION_DATA_UNAVAILABLE", "식품별 밀도·영양 데이터를 불러올 수 없습니다.") from exc

@lru_cache(maxsize=1)
def get_pipeline():
    try:
        return VisionPipelineOrchestrator(
            YoloV8Segmentor(settings.ONNX_SEG_MODEL_PATH, use_cuda=settings.ONNX_USE_CUDA),
            DepthAnythingV2Estimator(settings.ONNX_DEPTH_MODEL_PATH),
            patch_embedder=PatchEmbedder(settings.FOOD_EMBEDDING_MODEL_PATH),
            food_retriever=FoodRetriever(settings.FOOD_EMBEDDING_INDEX_PATH),
            nutrition_service=get_nutrition_service(),
            metric=settings.DEPTH_MODEL_IS_METRIC,
        )
    except AppException:
        raise
    except Exception as exc:
        raise AppException(503, "ERR_MODEL_UNAVAILABLE", "분석 모델을 불러올 수 없습니다.") from exc

def decode_image(contents):
    if not contents:
        raise AppException(422,"ERR_INVALID_IMAGE","빈 이미지 파일입니다.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                if image.width * image.height > settings.MAX_IMAGE_PIXELS:
                    raise AppException(413,"ERR_IMAGE_TOO_LARGE","이미지 해상도가 허용 범위를 초과했습니다.")
                if image.format not in {"JPEG","PNG","WEBP"}:
                    raise AppException(415,"ERR_IMAGE_FORMAT","JPEG, PNG, WebP 이미지를 사용해 주세요.")
                image.verify()
        decoded = cv2.imdecode(np.frombuffer(contents,np.uint8),cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError()
        return decoded
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, cv2.error, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppException(422,"ERR_INVALID_IMAGE","이미지 파일을 읽을 수 없습니다.")

def extract_exif_focal_length_mm(contents):
    try:
        with Image.open(io.BytesIO(contents)) as image:
            value = image.getexif().get(41989)
        if value is None:
            return None
        focal_length_mm = float(value)
        if not np.isfinite(focal_length_mm) or not 0 < focal_length_mm <= 1000:
            return None
        return focal_length_mm
    except (OSError, TypeError, ValueError, ZeroDivisionError):
        return None

async def analyze_upload(file, focal_length_mm=None, conf_threshold=0.25, calibration=None, is_calibrated: bool = False):
    # Ref: NFR 3.3, bound image decoding and inference together per worker.
    async with inference_semaphore:
        try:
            contents = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            if len(contents) > settings.MAX_UPLOAD_BYTES:
                raise AppException(413, "ERR_FILE_TOO_LARGE", "이미지 파일은 10MB 이하로 업로드해 주세요.")
            image = await run_in_threadpool(decode_image, contents)
            resolved_focal_length_mm = focal_length_mm
            resolved_is_calibrated = is_calibrated

            # EXIF 메타데이터 검사 (EXIF 존재 시 우선 적용)
            exif_focal = extract_exif_focal_length_mm(contents)
            if exif_focal is not None:
                resolved_focal_length_mm = exif_focal
                resolved_is_calibrated = True
            elif resolved_focal_length_mm is None:
                resolved_focal_length_mm = 26.0

            if calibration is not None:
                calibration.update({
                    "focal_length_mm": resolved_focal_length_mm,
                    "is_calibrated": resolved_is_calibrated,
                })
            del contents
            pipeline = await run_in_threadpool(get_pipeline)
            return await run_in_threadpool(pipeline.process_image, image, resolved_focal_length_mm, conf_threshold)
        finally:
            await file.close()

PILL_CLASS_MAP = DrugInteractionService.PILL_CLASS_MAP

async def evaluate_drug_warnings(
    db: AsyncSession,
    user_id: uuid.UUID,
    meal_id: uuid.UUID,
    food_items: list[dict],
    triggers: dict[str, set[str]],
    detected_pills: list[dict],
) -> tuple[list[dict], list[MealDrugWarning]]:
    """식약처 금기 DB 연동 및 복약 상호작용 검사 (DrugInteractionService 위임) [FR-005]."""
    return await DrugInteractionService.evaluate_drug_warnings(
        db=db,
        user_id=user_id,
        meal_id=meal_id,
        food_items=food_items,
        triggers=triggers,
        detected_pills=detected_pills,
    )

@router.post("/vision/estimate", response_model=VisionEstimateEnvelope)
async def estimate_meal_vision(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    focal_length_mm: float = Form(26.0, gt=0, le=1000, allow_inf_nan=False, description="35mm 환산 초점거리"),
    is_calibrated: bool = Form(False, description="초점거리 캘리브레이션 여부"),
    conf_threshold: float = Form(.25, ge=0, le=1, allow_inf_nan=False),
):
    start = time.monotonic()
    calibration = {}
    result = await analyze_upload(
        file=file,
        focal_length_mm=focal_length_mm,
        conf_threshold=conf_threshold,
        calibration=calibration,
        is_calibrated=is_calibrated,
    )
    resolved_focal_length_mm = calibration["focal_length_mm"]
    resolved_is_calibrated = calibration["is_calibrated"]

    meal_id = uuid.uuid4()
    drug_warnings, warning_models = await evaluate_drug_warnings(
        db=db,
        user_id=current_user.id,
        meal_id=meal_id,
        food_items=result["foodItems"],
        triggers=result["triggers"],
        detected_pills=result.get("detectedPills", []),
    )

    nutrition = result["totalNutrition"]
    requires_confirmation = any(item["requiresConfirmation"] for item in result["foodItems"])
    meal = Meal(
        id=meal_id,
        user_id=current_user.id,
        image_url="",
        focal_length_mm=resolved_focal_length_mm,
        is_calibrated=resolved_is_calibrated,
        total_calories_kcal=nutrition["caloriesKcal"],
        total_carbs_g=nutrition["carbsG"],
        total_protein_g=nutrition["proteinG"],
        total_fat_g=nutrition["fatG"],
        total_sodium_mg=nutrition["sodiumMg"],
    )
    meal.food_items = [
        MealFoodItem(
            id=uuid.UUID(i["id"]),
            meal_id=meal_id,
            food_name=i["foodName"],
            confidence_score=i["confidenceScore"],
            volume_cm3=i["volumeCm3"],
            density_g_cm3=i["densityGCm3"],
            weight_g=i["weightG"],
            calories_kcal=i["caloriesKcal"],
            carbs_g=i["carbsG"],
            protein_g=i["proteinG"],
            fat_g=i["fatG"],
            sodium_mg=i["sodiumMg"],
            bbox_2d=i["bbox2d"],
            bbox_3d=i["bbox3d"],
        )
        for i in result["foodItems"]
    ]
    payload = VisionEstimateEnvelope.model_validate({
        "success": True,
        "data": {
            "mealId": str(meal_id),
            "imageUrl": "",
            "isCalibrated": resolved_is_calibrated,
            "focalLengthMm": resolved_focal_length_mm,
            "isPersisted": not requires_confirmation,
            "requiresConfirmation": requires_confirmation,
            "foodItems": result["foodItems"],
            "totalNutrition": nutrition,
            "groundPlane": result["groundPlane"],
            "visualization3d": result["visualization3d"],
            "drugWarnings": drug_warnings,
            "processedAt": datetime.now(timezone.utc).isoformat(),
            "inferenceLatencyMs": int((time.monotonic() - start) * 1000),
        }
    })
    if requires_confirmation:
        return payload
    db.add(meal)
    # Insert food rows before warnings that reference them, all in one transaction.
    await db.flush()
    for warning in warning_models:
        warning.meal_id = meal_id
        db.add(warning)
    await db.commit()
    return payload


@router.post(
    "/vision/confirm",
    response_model=VisionConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="수동 확정 식단 영양소 재계산 및 영구 저장 [FR-004]",
)
@router.post(
    "/confirm",
    response_model=VisionConfirmResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def confirm_meal_vision(
    request: VisionConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        meal_id = uuid.UUID(request.mealId) if request.mealId else uuid.uuid4()
    except (ValueError, AttributeError):
        meal_id = uuid.uuid4()

    volume_by_id = {}
    bbox2d_by_id = {}
    bbox3d_by_id = {}
    confidence_by_id = {}

    if request.volumeData:
        for v in request.volumeData:
            v_id = v.itemId or v.id
            if v_id:
                volume_by_id[str(v_id)] = v.volumeCm3
                if v.bbox2d:
                    bbox2d_by_id[str(v_id)] = v.bbox2d
                if v.bbox3d:
                    bbox3d_by_id[str(v_id)] = v.bbox3d
                if v.confidenceScore is not None:
                    confidence_by_id[str(v_id)] = v.confidenceScore

    nutrition_service = get_nutrition_service()
    calculated_items = []
    triggers = {}

    default_bbox2d = BoundingBox2D(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0)
    default_bbox3d = BoundingBox3D(
        center=Point3D(x=0.0, y=0.0, z=0.5),
        dimensions=Point3D(x=0.1, y=0.1, z=0.1),
        rotations=Point3D(x=0.0, y=0.0, z=0.0),
        vertices=[],
    )

    for selection in request.confirmedItems:
        item_id_str = str(selection.itemId)
        try:
            item_uuid = uuid.UUID(item_id_str)
        except (ValueError, AttributeError):
            raise AppException(422, "ERR_INVALID_ITEM_ID", f"유효하지 않은 itemId 형식입니다: {item_id_str}")

        volume_cm3 = selection.volumeCm3
        if volume_cm3 is None:
            volume_cm3 = volume_by_id.get(item_id_str)
        if volume_cm3 is None or volume_cm3 < 5 or volume_cm3 > 5000:
            raise AppException(422, "ERR_INVALID_VOLUME", f"항목 {item_id_str}의 유효한 부피 데이터(5~5000 cm³)가 필요합니다.")

        try:
            nutrition = nutrition_service.calculate(selection.foodId, volume_cm3)
        except KeyError:
            raise AppException(400, "ERR_UNKNOWN_FOOD", f"알 수 없는 foodId입니다: {selection.foodId}")

        confidence = selection.confidenceScore if selection.confidenceScore is not None else confidence_by_id.get(item_id_str, 1.0)
        b2d = selection.bbox2d or bbox2d_by_id.get(item_id_str, default_bbox2d)
        b3d = selection.bbox3d or bbox3d_by_id.get(item_id_str, default_bbox3d)

        calculated_items.append({
            "id": str(item_uuid),
            "foodId": nutrition["foodId"],
            "foodName": nutrition["foodName"],
            "confidenceScore": confidence,
            "volumeCm3": round(volume_cm3, 2),
            "densityGCm3": nutrition["densityGCm3"],
            "weightG": nutrition["weightG"],
            "caloriesKcal": nutrition["caloriesKcal"],
            "carbsG": nutrition["carbsG"],
            "proteinG": nutrition["proteinG"],
            "fatG": nutrition["fatG"],
            "sodiumMg": nutrition["sodiumMg"],
            "bbox2d": b2d,
            "bbox3d": b3d,
        })
        triggers[str(item_uuid)] = {nutrition["foodId"].lower(), *nutrition["interactionTags"]}

    total_nutrition = {
        key: round(sum(i[key] for i in calculated_items), 2)
        for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
    }

    raw_pills = [
        {"class_name": p.class_name, "class_id": p.class_id, "confidence": p.confidence, "box": p.box}
        if hasattr(p, "class_name") else p
        for p in (request.detectedPills or [])
    ]
    drug_warnings, warning_models = await evaluate_drug_warnings(
        db=db,
        user_id=current_user.id,
        meal_id=meal_id,
        food_items=calculated_items,
        triggers=triggers,
        detected_pills=raw_pills,
    )

    meal = Meal(
        id=meal_id,
        user_id=current_user.id,
        image_url=request.imageUrl or "",
        focal_length_mm=request.focalLengthMm,
        is_calibrated=request.isCalibrated,
        total_calories_kcal=total_nutrition["caloriesKcal"],
        total_carbs_g=total_nutrition["carbsG"],
        total_protein_g=total_nutrition["proteinG"],
        total_fat_g=total_nutrition["fatG"],
        total_sodium_mg=total_nutrition["sodiumMg"],
    )
    meal.food_items = [
        MealFoodItem(
            id=uuid.UUID(i["id"]),
            meal_id=meal_id,
            food_name=i["foodName"],
            confidence_score=i["confidenceScore"],
            volume_cm3=i["volumeCm3"],
            density_g_cm3=i["densityGCm3"],
            weight_g=i["weightG"],
            calories_kcal=i["caloriesKcal"],
            carbs_g=i["carbsG"],
            protein_g=i["proteinG"],
            fat_g=i["fatG"],
            sodium_mg=i["sodiumMg"],
            bbox_2d=i["bbox2d"].model_dump() if hasattr(i["bbox2d"], "model_dump") else i["bbox2d"],
            bbox_3d=i["bbox3d"].model_dump() if hasattr(i["bbox3d"], "model_dump") else i["bbox3d"],
        )
        for i in calculated_items
    ]

    db.add(meal)
    await db.flush()
    for warning in warning_models:
        warning.meal_id = meal_id
        db.add(warning)
    await db.commit()

    processed_at = datetime.now(timezone.utc).isoformat()
    confirm_data = {
        "mealId": str(meal_id),
        "isPersisted": True,
        "totalNutrition": total_nutrition,
        "foodItems": calculated_items,
        "drugWarnings": drug_warnings,
        "processedAt": processed_at,
    }
    return VisionConfirmResponse.model_validate({
        "success": True,
        "mealId": str(meal_id),
        "totalNutrition": total_nutrition,
        "drugWarnings": drug_warnings,
        "data": confirm_data,
    })
=======
import asyncio
import io
import time
import uuid
import warnings
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.api.deps import get_current_user
from src.core.config import settings
from src.core.database import get_db_session
from src.core.exceptions import AppException
from src.ml.onnx_segmentor import YoloV8Segmentor
from src.ml.onnx_depth_estimator import DepthAnythingV2Estimator
from src.ml.patch_embedder import PatchEmbedder
from src.ml.food_retriever import FoodRetriever
from src.models.entities import Drug, User, UserMedication, DrugFoodContraindication, Meal, MealFoodItem, MealDrugWarning
from src.schemas.vision import (
    VisionEstimateEnvelope,
    VisionConfirmRequest,
    VisionConfirmResponse,
    BoundingBox2D,
    BoundingBox3D,
    Point3D,
)
from src.services.vision_pipeline import VisionPipelineOrchestrator
from src.services.nutrition_service import NutritionService
from src.services.drug_interaction_service import DrugInteractionService

router = APIRouter(tags=["vision"])
inference_semaphore = asyncio.Semaphore(5)

@lru_cache(maxsize=1)
def get_nutrition_service() -> NutritionService:
    try:
        return NutritionService(
            settings.FOOD_CATALOG_PATH, settings.FOOD_DENSITY_PATH, settings.FOOD_NUTRIENTS_PATH
        )
    except Exception as exc:
        raise AppException(503, "ERR_NUTRITION_DATA_UNAVAILABLE", "식품별 밀도·영양 데이터를 불러올 수 없습니다.") from exc

@lru_cache(maxsize=1)
def get_pipeline():
    try:
        return VisionPipelineOrchestrator(
            YoloV8Segmentor(settings.ONNX_SEG_MODEL_PATH, use_cuda=settings.ONNX_USE_CUDA),
            DepthAnythingV2Estimator(settings.ONNX_DEPTH_MODEL_PATH),
            patch_embedder=PatchEmbedder(settings.FOOD_EMBEDDING_MODEL_PATH),
            food_retriever=FoodRetriever(settings.FOOD_EMBEDDING_INDEX_PATH),
            nutrition_service=get_nutrition_service(),
            metric=settings.DEPTH_MODEL_IS_METRIC,
        )
    except AppException:
        raise
    except Exception as exc:
        raise AppException(503, "ERR_MODEL_UNAVAILABLE", "분석 모델을 불러올 수 없습니다.") from exc

def decode_image(contents):
    if not contents:
        raise AppException(422,"ERR_INVALID_IMAGE","빈 이미지 파일입니다.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                if image.width * image.height > settings.MAX_IMAGE_PIXELS:
                    raise AppException(413,"ERR_IMAGE_TOO_LARGE","이미지 해상도가 허용 범위를 초과했습니다.")
                if image.format not in {"JPEG","PNG","WEBP"}:
                    raise AppException(415,"ERR_IMAGE_FORMAT","JPEG, PNG, WebP 이미지를 사용해 주세요.")
                image.verify()
        decoded = cv2.imdecode(np.frombuffer(contents,np.uint8),cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError()
        return decoded
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, cv2.error, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppException(422,"ERR_INVALID_IMAGE","이미지 파일을 읽을 수 없습니다.")

def extract_exif_focal_length_mm(contents):
    try:
        with Image.open(io.BytesIO(contents)) as image:
            value = image.getexif().get(41989)
        if value is None:
            return None
        focal_length_mm = float(value)
        if not np.isfinite(focal_length_mm) or not 0 < focal_length_mm <= 1000:
            return None
        return focal_length_mm
    except (OSError, TypeError, ValueError, ZeroDivisionError):
        return None

async def analyze_upload(file, focal_length_mm=None, conf_threshold=0.25, calibration=None, is_calibrated: bool = False):
    # Ref: NFR 3.3, bound image decoding and inference together per worker.
    async with inference_semaphore:
        try:
            contents = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            if len(contents) > settings.MAX_UPLOAD_BYTES:
                raise AppException(413, "ERR_FILE_TOO_LARGE", "이미지 파일은 10MB 이하로 업로드해 주세요.")
            image = await run_in_threadpool(decode_image, contents)
            resolved_focal_length_mm = focal_length_mm
            resolved_is_calibrated = is_calibrated

            # EXIF 메타데이터 검사 (EXIF 존재 시 우선 적용)
            exif_focal = extract_exif_focal_length_mm(contents)
            if exif_focal is not None:
                resolved_focal_length_mm = exif_focal
                resolved_is_calibrated = True
            elif resolved_focal_length_mm is None:
                resolved_focal_length_mm = 26.0

            if calibration is not None:
                calibration.update({
                    "focal_length_mm": resolved_focal_length_mm,
                    "is_calibrated": resolved_is_calibrated,
                })
            del contents
            pipeline = await run_in_threadpool(get_pipeline)
            return await run_in_threadpool(pipeline.process_image, image, resolved_focal_length_mm, conf_threshold)
        finally:
            await file.close()

PILL_CLASS_MAP = DrugInteractionService.PILL_CLASS_MAP

async def evaluate_drug_warnings(
    db: AsyncSession,
    user_id: uuid.UUID,
    meal_id: uuid.UUID,
    food_items: list[dict],
    triggers: dict[str, set[str]],
    detected_pills: list[dict],
) -> tuple[list[dict], list[MealDrugWarning]]:
    """식약처 금기 DB 연동 및 복약 상호작용 검사 (DrugInteractionService 위임) [FR-005]."""
    return await DrugInteractionService.evaluate_drug_warnings(
        db=db,
        user_id=user_id,
        meal_id=meal_id,
        food_items=food_items,
        triggers=triggers,
        detected_pills=detected_pills,
    )

@router.post("/vision/estimate", response_model=VisionEstimateEnvelope)
async def estimate_meal_vision(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    focal_length_mm: float = Form(26.0, gt=0, le=1000, allow_inf_nan=False, description="35mm 환산 초점거리"),
    is_calibrated: bool = Form(False, description="초점거리 캘리브레이션 여부"),
    conf_threshold: float = Form(.25, ge=0, le=1, allow_inf_nan=False),
):
    start = time.monotonic()
    calibration = {}
    result = await analyze_upload(
        file=file,
        focal_length_mm=focal_length_mm,
        conf_threshold=conf_threshold,
        calibration=calibration,
        is_calibrated=is_calibrated,
    )
    resolved_focal_length_mm = calibration["focal_length_mm"]
    resolved_is_calibrated = calibration["is_calibrated"]

    meal_id = uuid.uuid4()
    drug_warnings, warning_models = await evaluate_drug_warnings(
        db=db,
        user_id=current_user.id,
        meal_id=meal_id,
        food_items=result["foodItems"],
        triggers=result["triggers"],
        detected_pills=result.get("detectedPills", []),
    )

    nutrition = result["totalNutrition"]
    requires_confirmation = any(item["requiresConfirmation"] for item in result["foodItems"])
    meal = Meal(
        id=meal_id,
        user_id=current_user.id,
        image_url="",
        focal_length_mm=resolved_focal_length_mm,
        is_calibrated=resolved_is_calibrated,
        total_calories_kcal=nutrition["caloriesKcal"],
        total_carbs_g=nutrition["carbsG"],
        total_protein_g=nutrition["proteinG"],
        total_fat_g=nutrition["fatG"],
        total_sodium_mg=nutrition["sodiumMg"],
    )
    meal.food_items = [
        MealFoodItem(
            id=uuid.UUID(i["id"]),
            meal_id=meal_id,
            food_name=i["foodName"],
            confidence_score=i["confidenceScore"],
            volume_cm3=i["volumeCm3"],
            density_g_cm3=i["densityGCm3"],
            weight_g=i["weightG"],
            calories_kcal=i["caloriesKcal"],
            carbs_g=i["carbsG"],
            protein_g=i["proteinG"],
            fat_g=i["fatG"],
            sodium_mg=i["sodiumMg"],
            bbox_2d=i["bbox2d"],
            bbox_3d=i["bbox3d"],
        )
        for i in result["foodItems"]
    ]
    payload = VisionEstimateEnvelope.model_validate({
        "success": True,
        "data": {
            "mealId": str(meal_id),
            "imageUrl": "",
            "isCalibrated": resolved_is_calibrated,
            "focalLengthMm": resolved_focal_length_mm,
            "isPersisted": not requires_confirmation,
            "requiresConfirmation": requires_confirmation,
            "foodItems": result["foodItems"],
            "detectedPills": result.get("detectedPills", []),
            "totalNutrition": nutrition,
            "groundPlane": result["groundPlane"],
            "visualization3d": result["visualization3d"],
            "drugWarnings": drug_warnings,
            "processedAt": datetime.now(timezone.utc).isoformat(),
            "inferenceLatencyMs": int((time.monotonic() - start) * 1000),
        }
    })
    if requires_confirmation:
        return payload
    db.add(meal)
    # Insert food rows before warnings that reference them, all in one transaction.
    await db.flush()
    for warning in warning_models:
        warning.meal_id = meal_id
        db.add(warning)
    await db.commit()
    return payload


@router.post(
    "/vision/confirm",
    response_model=VisionConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="수동 확정 식단 영양소 재계산 및 영구 저장 [FR-004]",
)
@router.post(
    "/confirm",
    response_model=VisionConfirmResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def confirm_meal_vision(
    request: VisionConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        meal_id = uuid.UUID(request.mealId) if request.mealId else uuid.uuid4()
    except (ValueError, AttributeError):
        meal_id = uuid.uuid4()

    if len({item.itemId for item in request.confirmedItems}) != len(request.confirmedItems):
        raise AppException(422, "ERR_DUPLICATE_ITEM", "중복된 음식 항목입니다.")

    volume_by_id = {}
    bbox2d_by_id = {}
    bbox3d_by_id = {}
    confidence_by_id = {}

    if request.volumeData:
        for v in request.volumeData:
            v_id = v.itemId or v.id
            if v_id:
                volume_by_id[str(v_id)] = v.volumeCm3
                if v.bbox2d:
                    bbox2d_by_id[str(v_id)] = v.bbox2d
                if v.bbox3d:
                    bbox3d_by_id[str(v_id)] = v.bbox3d
                if v.confidenceScore is not None:
                    confidence_by_id[str(v_id)] = v.confidenceScore

    nutrition_service = get_nutrition_service()
    calculated_items = []
    triggers = {}

    default_bbox2d = BoundingBox2D(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0)
    default_bbox3d = BoundingBox3D(
        center=Point3D(x=0.0, y=0.0, z=0.5),
        dimensions=Point3D(x=0.1, y=0.1, z=0.1),
        rotations=Point3D(x=0.0, y=0.0, z=0.0),
        vertices=[],
    )

    for selection in request.confirmedItems:
        item_id_str = str(selection.itemId)
        try:
            item_uuid = uuid.UUID(item_id_str)
        except (ValueError, AttributeError):
            raise AppException(422, "ERR_INVALID_ITEM_ID", f"유효하지 않은 itemId 형식입니다: {item_id_str}")

        volume_cm3 = selection.volumeCm3
        if volume_cm3 is None:
            volume_cm3 = volume_by_id.get(item_id_str)
        if volume_cm3 is None or volume_cm3 < 5 or volume_cm3 > 5000:
            raise AppException(422, "ERR_INVALID_VOLUME", f"항목 {item_id_str}의 유효한 부피 데이터(5~5000 cm³)가 필요합니다.")

        try:
            nutrition = nutrition_service.calculate(selection.foodId, volume_cm3)
        except KeyError:
            raise AppException(400, "ERR_UNKNOWN_FOOD", f"알 수 없는 foodId입니다: {selection.foodId}")

        # Ref: FR-008, recompute from server profiles without changing measured volume.
        if selection.weightG is not None:
            ratio = selection.weightG / nutrition["weightG"]
            nutrition = {**nutrition, "weightG": selection.weightG, **{
                key: round(nutrition[key] * ratio, 2)
                for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
            }}

        confidence = selection.confidenceScore if selection.confidenceScore is not None else confidence_by_id.get(item_id_str, 1.0)
        b2d = selection.bbox2d or bbox2d_by_id.get(item_id_str, default_bbox2d)
        b3d = selection.bbox3d or bbox3d_by_id.get(item_id_str, default_bbox3d)

        calculated_items.append({
            "id": str(item_uuid),
            "foodId": nutrition["foodId"],
            "foodName": nutrition["foodName"],
            "confidenceScore": confidence,
            "volumeCm3": round(volume_cm3, 2),
            "densityGCm3": nutrition["densityGCm3"],
            "weightG": nutrition["weightG"],
            "caloriesKcal": nutrition["caloriesKcal"],
            "carbsG": nutrition["carbsG"],
            "proteinG": nutrition["proteinG"],
            "fatG": nutrition["fatG"],
            "sodiumMg": nutrition["sodiumMg"],
            "bbox2d": b2d,
            "bbox3d": b3d,
        })
        triggers[str(item_uuid)] = {nutrition["foodId"].lower(), *nutrition["interactionTags"]}

    total_nutrition = {
        key: round(sum(i[key] for i in calculated_items), 2)
        for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
    }

    raw_pills = [
        {"class_name": p.class_name, "class_id": p.class_id, "confidence": p.confidence, "box": p.box}
        if hasattr(p, "class_name") else p
        for p in (request.detectedPills or [])
    ]
    drug_warnings, warning_models = await evaluate_drug_warnings(
        db=db,
        user_id=current_user.id,
        meal_id=meal_id,
        food_items=calculated_items,
        triggers=triggers,
        detected_pills=raw_pills,
    )

    # Ref: FR-007/008, serialize saves for this owner, including first-save retries.
    await db.execute(select(User.id).where(User.id == current_user.id).with_for_update())
    meal = (await db.execute(
        select(Meal).where(Meal.id == meal_id)
        .options(selectinload(Meal.food_items), selectinload(Meal.drug_warnings))
        .with_for_update()
    )).scalar_one_or_none()
    if meal is not None and meal.user_id != current_user.id:
        raise AppException(404, "ERR_MEAL_NOT_FOUND", "식단 기록을 찾을 수 없습니다.")
    item_ids = [uuid.UUID(item["id"]) for item in calculated_items]
    collision = (await db.execute(select(MealFoodItem.id).where(
        MealFoodItem.id.in_(item_ids), MealFoodItem.meal_id != meal_id
    ))).first()
    if collision:
        raise AppException(409, "ERR_ITEM_CONFLICT", "다른 식단에 속한 음식 항목입니다.")
    if meal is None:
        meal = Meal(id=meal_id, user_id=current_user.id)
    else:
        meal.drug_warnings.clear()
        await db.flush()
        meal.food_items.clear()
        await db.flush()
    meal.image_url = request.imageUrl or ""
    meal.focal_length_mm = request.focalLengthMm
    meal.is_calibrated = request.isCalibrated
    for key, value in total_nutrition.items():
        column = {"caloriesKcal": "total_calories_kcal", "carbsG": "total_carbs_g",
                  "proteinG": "total_protein_g", "fatG": "total_fat_g", "sodiumMg": "total_sodium_mg"}[key]
        setattr(meal, column, value)
    meal.food_items = [
        MealFoodItem(
            id=uuid.UUID(i["id"]),
            meal_id=meal_id,
            food_name=i["foodName"],
            confidence_score=i["confidenceScore"],
            volume_cm3=i["volumeCm3"],
            density_g_cm3=i["densityGCm3"],
            weight_g=i["weightG"],
            calories_kcal=i["caloriesKcal"],
            carbs_g=i["carbsG"],
            protein_g=i["proteinG"],
            fat_g=i["fatG"],
            sodium_mg=i["sodiumMg"],
            bbox_2d=i["bbox2d"].model_dump() if hasattr(i["bbox2d"], "model_dump") else i["bbox2d"],
            bbox_3d=i["bbox3d"].model_dump() if hasattr(i["bbox3d"], "model_dump") else i["bbox3d"],
        )
        for i in calculated_items
    ]

    db.add(meal)
    await db.flush()
    for warning in warning_models:
        warning.meal_id = meal_id
        db.add(warning)
    await db.commit()

    processed_at = datetime.now(timezone.utc).isoformat()
    confirm_data = {
        "mealId": str(meal_id),
        "isPersisted": True,
        "totalNutrition": total_nutrition,
        "foodItems": calculated_items,
        "drugWarnings": drug_warnings,
        "processedAt": processed_at,
    }
    return VisionConfirmResponse.model_validate({
        "success": True,
        "mealId": str(meal_id),
        "totalNutrition": total_nutrition,
        "drugWarnings": drug_warnings,
        "data": confirm_data,
    })
>>>>>>> REPLACE
```

## frontend/src/services/api.ts

```text
파일 경로: frontend/src/services/api.ts
<<<<<<< SEARCH
import type { MealEstimateResponse } from '../types/vision';
export interface VisionEstimateResponse { success: true; data: MealEstimateResponse; }
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL
  || (process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1` : '/api/v1')).replace(/\/$/, '');
// Keep credentials in memory rather than browser persistent storage.
let accessToken: string | null = null;
export class AuthenticationError extends Error {}
async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options, signal: AbortSignal.timeout(120000),
    credentials: 'include',
    headers: { ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...options.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) accessToken = null;
    const detail = payload?.error?.message || payload?.detail?.error?.message || payload?.detail;
    const ErrorType = response.status === 401 ? AuthenticationError : Error;
    throw new ErrorType(typeof detail === 'string' ? detail : `요청을 완료할 수 없습니다 (${response.status}).`);
  }
  return payload;
}
export async function login(email: string, password: string): Promise<void> {
  const result = await request('/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  });
  accessToken = result.accessToken;
}
export async function register(email: string, password: string, name: string): Promise<void> {
  await request('/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password, name }),
  });
}
export function logout(): void { accessToken = null; }
export async function getServiceStatus(): Promise<string> {
  const health = await request('/health');
  if (!health.metricDepthConfigured || !health.foodRecognitionConfigured || !health.nutritionConfigured) return '분석 데이터 준비 필요';
  if (!health.modelLoaded) return '모델 대기 중';
  return health.inferenceProviders.includes('CUDAExecutionProvider') ? 'GPU 추론 준비' : 'CPU 추론 준비';
}
export async function estimateMealVision(imageFile: File): Promise<VisionEstimateResponse> {
  if (imageFile.size === 0 || imageFile.size > 10 * 1024 * 1024) throw new Error('0바이트보다 크고 10MB 이하인 이미지를 선택해 주세요.');
  const formData = new FormData();
  formData.append('file', imageFile);
  const payload = await request('/vision/estimate', { method: 'POST', body: formData });
  if (payload?.success !== true || !payload.data) throw new Error('분석 응답 형식이 올바르지 않습니다.');
  return payload;
}

export interface MealListItem {
  id: string; imageUrl: string; totalCaloriesKcal: number; foodItemCount: number; highestRiskLevel: string; createdAt: string;
}
export interface MealDetail {
  id: string; createdAt: string; totalCaloriesKcal: number;
  foodItems: Array<{ id: string; foodName: string; volumeCm3: number; weightG: number; caloriesKcal: number }>;
  drugWarnings: Array<{ id: string; warningTitle: string; warningMessage: string }>;
}
export async function listMeals(): Promise<MealListItem[]> {
  const payload = await request('/meals');
  if (payload?.success !== true || !Array.isArray(payload?.data?.items)) {
    throw new Error('식단 기록 응답 형식이 올바르지 않습니다.');
  }
  return payload.data.items;
}
export async function getMeal(id: string): Promise<MealDetail> { return request(`/meals/${encodeURIComponent(id)}`); }
=======
import type { MealEstimateResponse } from '../types/vision';
export interface VisionEstimateResponse { success: true; data: MealEstimateResponse; }
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL
  || (process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1` : '/api/v1')).replace(/\/$/, '');
// Keep credentials in memory rather than browser persistent storage.
let accessToken: string | null = null;
export class AuthenticationError extends Error {}
async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options, signal: AbortSignal.timeout(120000),
    credentials: 'include',
    headers: { ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...options.headers },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) accessToken = null;
    const code = payload?.error?.code || payload?.detail?.error?.code;
    const guidance: Record<string, string> = {
      ERR_GEOMETRY_PLANE_NOT_FOUND: '테이블 기준 평면을 찾지 못했습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.',
      ERR_ZERO_OBJECT_DETECTED: '음식을 찾지 못했습니다. 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영해 주세요.',
    };
    const detail = guidance[code] || payload?.error?.message || payload?.detail?.error?.message || payload?.detail;
    const ErrorType = response.status === 401 ? AuthenticationError : Error;
    throw new ErrorType(typeof detail === 'string' ? detail : `요청을 완료할 수 없습니다 (${response.status}).`);
  }
  return payload;
}
export async function login(email: string, password: string): Promise<void> {
  const result = await request('/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  });
  accessToken = result.accessToken;
}
export async function register(email: string, password: string, name: string): Promise<void> {
  await request('/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password, name }),
  });
}
export function logout(): void { accessToken = null; }
export async function getServiceStatus(): Promise<string> {
  const health = await request('/health');
  if (!health.metricDepthConfigured || !health.foodRecognitionConfigured || !health.nutritionConfigured) return '분석 데이터 준비 필요';
  if (!health.modelLoaded) return '모델 대기 중';
  return health.inferenceProviders.includes('CUDAExecutionProvider') ? 'GPU 추론 준비' : 'CPU 추론 준비';
}
export async function estimateMealVision(imageFile: File): Promise<VisionEstimateResponse> {
  if (imageFile.size === 0 || imageFile.size > 10 * 1024 * 1024) throw new Error('0바이트보다 크고 10MB 이하인 이미지를 선택해 주세요.');
  const formData = new FormData();
  formData.append('file', imageFile);
  const payload = await request('/vision/estimate', { method: 'POST', body: formData });
  if (payload?.success !== true || !payload.data) throw new Error('분석 응답 형식이 올바르지 않습니다.');
  return payload;
}

export interface MealListItem {
  id: string; imageUrl: string; totalCaloriesKcal: number; foodItemCount: number; highestRiskLevel: string; createdAt: string;
}
export interface MealDetail {
  id: string; createdAt: string; totalCaloriesKcal: number;
  foodItems: Array<{ id: string; foodName: string; volumeCm3: number; weightG: number; caloriesKcal: number }>;
  drugWarnings: Array<{ id: string; warningTitle: string; warningMessage: string }>;
}
export async function listMeals(): Promise<MealListItem[]> {
  const payload = await request('/meals');
  if (payload?.success !== true || !Array.isArray(payload?.data?.items)) {
    throw new Error('식단 기록 응답 형식이 올바르지 않습니다.');
  }
  return payload.data.items;
}
export async function getMeal(id: string): Promise<MealDetail> { return request(`/meals/${encodeURIComponent(id)}`); }

// Ref: FR-008, send identity and measurements; the server calculates nutrition.
export async function confirmMealVision(result: MealEstimateResponse): Promise<MealEstimateResponse> {
  if (result.foodItems.length === 0 || result.foodItems.some(item => item.requiresConfirmation)) {
    throw new Error('모든 음식 후보를 먼저 선택해 주세요.');
  }
  const payload = await request('/vision/confirm', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mealId: result.mealId, imageUrl: result.imageUrl,
      focalLengthMm: result.focalLengthMm, isCalibrated: result.isCalibrated,
      detectedPills: result.detectedPills || [],
      confirmedItems: result.foodItems.map(item => ({
        itemId: item.id, foodId: item.foodId, weightG: item.weightG,
        volumeCm3: item.volumeCm3, confidenceScore: item.confidenceScore,
        bbox2d: item.bbox2d, bbox3d: item.bbox3d,
      })),
    }),
  });
  if (payload?.success !== true || payload?.data?.isPersisted !== true ||
      payload.data.mealId !== result.mealId || !Array.isArray(payload.data.foodItems) ||
      payload.data.foodItems.length !== result.foodItems.length ||
      result.foodItems.some(item => !payload.data.foodItems.some((saved: { id: string }) => saved.id === item.id))) {
    throw new Error('확정 저장 응답 형식이 올바르지 않습니다.');
  }
  return {
    ...result, ...payload.data, requiresConfirmation: false,
    foodItems: result.foodItems.map(item => ({
      ...item, ...payload.data.foodItems.find((saved: { id: string }) => saved.id === item.id),
      requiresConfirmation: false,
    })),
  };
}
>>>>>>> REPLACE
```

## frontend/src/app/page.tsx

```text
파일 경로: frontend/src/app/page.tsx
<<<<<<< SEARCH
'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import MealHistory from '../components/MealHistory';
import { estimateMealVision, login, register, logout, getServiceStatus, AuthenticationError } from '../services/api';
import type { FoodCandidate, FoodItemEstimation, MealEstimateResponse } from '../types/vision';

const EMPTY_ITEMS: MealEstimateResponse['foodItems'] = [];
const NUTRIENT_KEYS = ['caloriesKcal', 'carbsG', 'proteinG', 'fatG', 'sodiumMg'] as const;

function updateTotals(items: FoodItemEstimation[]): MealEstimateResponse['totalNutrition'] {
  return NUTRIENT_KEYS.reduce((totals, key) => {
    totals[key] = Number(items.reduce((sum, item) => sum + item[key], 0).toFixed(2));
    return totals;
  }, { caloriesKcal: 0, carbsG: 0, proteinG: 0, fatG: 0, sodiumMg: 0 });
}

function applyCandidate(item: FoodItemEstimation, candidate: FoodCandidate): FoodItemEstimation {
  if (candidate.weightG == null || candidate.densityGCm3 == null) return item;
  return {
    ...item,
    foodId: candidate.foodId,
    foodName: candidate.foodName,
    densityGCm3: candidate.densityGCm3,
    weightG: candidate.weightG,
    caloriesKcal: candidate.caloriesKcal ?? item.caloriesKcal,
    carbsG: candidate.carbsG ?? item.carbsG,
    proteinG: candidate.proteinG ?? item.proteinG,
    fatG: candidate.fatG ?? item.fatG,
    sodiumMg: candidate.sodiumMg ?? item.sodiumMg,
    requiresConfirmation: false,
  };
}

function applyWeight(item: FoodItemEstimation, weightG: number): FoodItemEstimation {
  if (!Number.isFinite(weightG) || weightG <= 0 || item.weightG <= 0) return item;
  const ratio = weightG / item.weightG;
  return {
    ...item,
    weightG: Number(weightG.toFixed(2)),
    caloriesKcal: Number((item.caloriesKcal * ratio).toFixed(2)),
    carbsG: Number((item.carbsG * ratio).toFixed(2)),
    proteinG: Number((item.proteinG * ratio).toFixed(2)),
    fatG: Number((item.fatG * ratio).toFixed(2)),
    sodiumMg: Number((item.sodiumMg * ratio).toFixed(2)),
  };
}

const ThreeViewer = dynamic(() => import('../components/ThreeViewer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[420px] rounded-xl border border-slate-800 bg-slate-900 flex items-center justify-center text-slate-500 font-mono text-sm">
      3D 뷰어 엔진 초기화 중...
    </div>
  ),
});

export default function MealAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<MealEstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [signedIn, setSignedIn] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState('서버 상태 확인 중');
  useEffect(() => {
    let active = true;
    getServiceStatus().then(status => { if (active) setServiceStatus(status); })
      .catch(() => { if (active) setServiceStatus('서버 연결 확인 필요'); });
    return () => { active = false; };
  }, []);
  const handleSessionExpired = useCallback(() => { logout(); setSignedIn(false); setResult(null); setError('로그인이 만료되었습니다. 다시 로그인해 주세요.'); }, []);
  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try { await login(email, password); setSignedIn(true); setPassword(''); }
    catch (err) { setError(err instanceof Error ? err.message : '로그인 실패'); }
    finally { setAuthLoading(false); }
  };
  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try {
      await register(email, password, name);
      await login(email, password);
      setSignedIn(true); setPassword(''); setName('');
    } catch (err) { setError(err instanceof Error ? err.message : '회원가입 실패'); }
    finally { setAuthLoading(false); }
  };

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) || selected.size === 0 || selected.size > 10 * 1024 * 1024) {
        setFile(null); setPreviewUrl(null); setResult(null);
        e.target.value = '';
        setError('JPEG, PNG, WebP 형식의 10MB 이하 이미지를 선택해 주세요.');
        return;
      }
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await estimateMealVision(file);
      setResult(data.data);
      getServiceStatus().then(setServiceStatus).catch(() => setServiceStatus('서버 연결 확인 필요'));
    } catch (err: unknown) {
      if (err instanceof AuthenticationError) handleSessionExpired();
      const message = err instanceof Error ? err.message : '';
      setError(message.includes('유효한 음식 또는 약제가 검출되지 않았습니다')
        ? '음식을 찾지 못했습니다. 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영해 주세요.'
        : message || '분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleCandidateSelect = (itemId: string, candidate: FoodCandidate) => {
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyCandidate(item, candidate) : item);
      return { ...current, foodItems, totalNutrition: updateTotals(foodItems), requiresConfirmation: foodItems.some(item => item.requiresConfirmation) };
    });
  };

  const handleWeightChange = (itemId: string, value: string) => {
    const weightG = Number(value);
    if (!Number.isFinite(weightG) || weightG <= 0) return;
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyWeight(item, weightG) : item);
      return { ...current, foodItems, totalNutrition: updateTotals(foodItems) };
    });
  };

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!previewUrl || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      result?.foodItems.forEach((item) => {
        const x1 = item.bbox2d.xmin * canvas.width;
        const y1 = item.bbox2d.ymin * canvas.height;
        const x2 = item.bbox2d.xmax * canvas.width;
        const y2 = item.bbox2d.ymax * canvas.height;
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 4;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        ctx.fillStyle = 'rgba(56, 189, 248, 0.85)';
        ctx.fillRect(x1, Math.max(0, y1 - 28), 190, 28);
        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 16px sans-serif';
        ctx.fillText(
          `${item.foodName} (${(item.confidenceScore * 100).toFixed(1)}%)`,
          x1 + 6,
          Math.max(0, y1 - 8)
        );
      });
    };
    img.src = previewUrl;
    return () => { img.onload = null; };
  }, [previewUrl, result]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <header className="max-w-7xl mx-auto mb-8 border-b border-slate-800 pb-5 flex flex-wrap gap-3 justify-between items-center">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-300">
            VoluMeal-Align
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            식단 체적·영양 추정 및 등록된 복약 정보 기반 상호작용 확인
          </p>
        </div>
        <span className="bg-emerald-950 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-700 font-mono">
          {serviceStatus}
        </span>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* 좌측: 파일 업로드 및 2D 검출 오버레이 */}
        <section className="lg:col-span-5 min-w-0 flex flex-col gap-5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            {signedIn ? <button disabled={loading} onClick={() => { logout(); setSignedIn(false); setResult(null); }}>로그아웃</button> :
              <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="flex flex-col gap-3">
                {authMode === 'register' && <label>이름<input className="block w-full bg-slate-800 p-2 rounded" type="text" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required /></label>}
                <label>이메일<input className="block w-full bg-slate-800 p-2 rounded" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label>
                <label>비밀번호<input className="block w-full bg-slate-800 p-2 rounded" type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} minLength={authMode === 'register' ? 8 : 1} required /></label>
                <button disabled={authLoading} type="submit" className="rounded bg-cyan-700 p-2">{authLoading ? (authMode === 'login' ? '로그인 중...' : '회원가입 중...') : (authMode === 'login' ? '로그인' : '회원가입')}</button>
                <button type="button" className="text-sm text-cyan-300 underline" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(null); }}>
                  {authMode === 'login' ? '회원가입하기' : '로그인으로 돌아가기'}
                </button>
              </form>}
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              식단 이미지 업로드
            </h2>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={loading}
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
            />

            {previewUrl && (
              <div className="mt-4 rounded-lg overflow-hidden border border-slate-800 bg-slate-950">
                <canvas ref={canvasRef} className="w-full h-auto object-contain block" />
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!file || loading}
              className="mt-4 w-full py-2.5 px-4 rounded-lg font-semibold text-sm bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:from-cyan-400 hover:to-teal-400 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
            >
              {loading ? '이미지 분석 중...' : '식단 분석'}
            </button>
            {error && <p role="alert" className="text-xs text-rose-400 mt-2">{error}</p>}
          </div>

          {/* KFDA 의약품 상호작용 경고창 */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span>등록 복약과 식품 상호작용</span>
                <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
                  {result.drugWarnings.length}건
                </span>
              </h2>

              {result.drugWarnings.length === 0 ? (
                <div className="p-3 bg-emerald-950/40 border border-emerald-800 rounded-lg text-xs text-emerald-300">
                  이번 분석에서 반환된 상호작용 경고가 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {result.drugWarnings.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border text-xs space-y-1.5 ${
                        alert.riskLevel === 'DANGER'
                          ? 'bg-rose-950/50 border-rose-800 text-rose-200'
                          : 'bg-amber-950/50 border-amber-800 text-amber-200'
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span className="text-sm">{alert.warningTitle}</span>
                        <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-black/40 border border-current">
                          {alert.riskLevel}
                        </span>
                      </div>
                      <p className="leading-relaxed opacity-90">{alert.warningMessage}</p>
                      <div className="pt-1.5 border-t border-white/10 text-[11px] text-slate-300">
                        <span className="font-semibold text-white">임상 권고: </span>
                        {alert.actionGuide}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* 우측: Three.js 3D 체적 복원 및 지표 카드 */}
        <section className="lg:col-span-7 min-w-0 flex flex-col gap-5">
          {signedIn && <MealHistory refreshKey={result?.isPersisted ? result.mealId : undefined} onSessionExpired={handleSessionExpired} />}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              3D 점군 및 경계 상자
            </h2>
            <ThreeViewer items={result?.foodItems || EMPTY_ITEMS} pointCloud={result?.visualization3d.pointCloud} height={420} />
            {result && !result.isCalibrated && <p className="mt-2 text-xs text-amber-300">카메라 미보정 추정값입니다. 원본 이미지는 서버에 보관하지 않습니다.</p>}
          </div>

          {result && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {result.foodItems.map((item, idx) => (
                <React.Fragment key={idx}>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">식품명</span>
                    <p className="text-base font-bold text-cyan-400 capitalize mt-0.5">{item.foodName}</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 체적</span>
                    <p className="text-base font-bold text-slate-100 mt-0.5">{item.volumeCm3} cm³</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 질량</span>
                    <label className="block mt-0.5">
                      <span className="sr-only">{item.foodName} 중량</span>
                      <input
                        aria-label={`${item.foodName} 중량`}
                        type="number"
                        min="1"
                        step="1"
                        value={item.weightG}
                        onChange={event => handleWeightChange(item.id, event.target.value)}
                        className="w-24 bg-transparent text-base font-bold text-emerald-400 outline-none"
                      />
                      <span className="text-base font-bold text-emerald-400"> g</span>
                    </label>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 열량</span>
                    <p className="text-base font-bold text-slate-300 mt-0.5 font-mono">
                      {item.caloriesKcal.toLocaleString()} kcal
                    </p>
                  </div>
                  {item.requiresConfirmation && (
                    <div className="col-span-2 sm:col-span-4 border border-amber-700 bg-amber-950/40 p-3.5 rounded-xl">
                      <p className="text-sm font-semibold text-amber-200">음식 확인이 필요합니다. 후보를 선택해 주세요.</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.topCandidates.map(candidate => (
                          <button
                            key={candidate.foodId}
                            type="button"
                            onClick={() => handleCandidateSelect(item.id, candidate)}
                            className="rounded border border-amber-600 bg-amber-900/50 px-3 py-2 text-left text-xs text-amber-100 hover:bg-amber-800"
                          >
                            <span className="block font-semibold">{candidate.foodName}</span>
                            <span className="text-amber-300">유사도 {(candidate.score * 100).toFixed(0)}%</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
=======
'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import MealHistory from '../components/MealHistory';
import { estimateMealVision, confirmMealVision, login, register, logout, getServiceStatus, AuthenticationError } from '../services/api';
import type { FoodCandidate, FoodItemEstimation, MealEstimateResponse } from '../types/vision';

const EMPTY_ITEMS: MealEstimateResponse['foodItems'] = [];
const NUTRIENT_KEYS = ['caloriesKcal', 'carbsG', 'proteinG', 'fatG', 'sodiumMg'] as const;

function updateTotals(items: FoodItemEstimation[]): MealEstimateResponse['totalNutrition'] {
  return NUTRIENT_KEYS.reduce((totals, key) => {
    totals[key] = Number(items.reduce((sum, item) => sum + item[key], 0).toFixed(2));
    return totals;
  }, { caloriesKcal: 0, carbsG: 0, proteinG: 0, fatG: 0, sodiumMg: 0 });
}

function applyCandidate(item: FoodItemEstimation, candidate: FoodCandidate): FoodItemEstimation {
  if (candidate.weightG == null || candidate.densityGCm3 == null) return item;
  return {
    ...item,
    foodId: candidate.foodId,
    foodName: candidate.foodName,
    densityGCm3: candidate.densityGCm3,
    weightG: candidate.weightG,
    caloriesKcal: candidate.caloriesKcal ?? item.caloriesKcal,
    carbsG: candidate.carbsG ?? item.carbsG,
    proteinG: candidate.proteinG ?? item.proteinG,
    fatG: candidate.fatG ?? item.fatG,
    sodiumMg: candidate.sodiumMg ?? item.sodiumMg,
    requiresConfirmation: false,
  };
}

function applyWeight(item: FoodItemEstimation, weightG: number): FoodItemEstimation {
  if (!Number.isFinite(weightG) || weightG <= 0 || item.weightG <= 0) return item;
  const ratio = weightG / item.weightG;
  return {
    ...item,
    weightG,
    caloriesKcal: Number((item.caloriesKcal * ratio).toFixed(2)),
    carbsG: Number((item.carbsG * ratio).toFixed(2)),
    proteinG: Number((item.proteinG * ratio).toFixed(2)),
    fatG: Number((item.fatG * ratio).toFixed(2)),
    sodiumMg: Number((item.sodiumMg * ratio).toFixed(2)),
  };
}

const ThreeViewer = dynamic(() => import('../components/ThreeViewer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[420px] rounded-xl border border-slate-800 bg-slate-900 flex items-center justify-center text-slate-500 font-mono text-sm">
      3D 뷰어 엔진 초기화 중...
    </div>
  ),
});

export default function MealAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<MealEstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [signedIn, setSignedIn] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState('서버 상태 확인 중');
  useEffect(() => {
    let active = true;
    getServiceStatus().then(status => { if (active) setServiceStatus(status); })
      .catch(() => { if (active) setServiceStatus('서버 연결 확인 필요'); });
    return () => { active = false; };
  }, []);
  const handleSessionExpired = useCallback(() => { logout(); setSignedIn(false); setResult(null); setError('로그인이 만료되었습니다. 다시 로그인해 주세요.'); }, []);
  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try { await login(email, password); setSignedIn(true); setPassword(''); }
    catch (err) { setError(err instanceof Error ? err.message : '로그인 실패'); }
    finally { setAuthLoading(false); }
  };
  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthLoading(true); setError(null);
    try {
      await register(email, password, name);
      await login(email, password);
      setSignedIn(true); setPassword(''); setName('');
    } catch (err) { setError(err instanceof Error ? err.message : '회원가입 실패'); }
    finally { setAuthLoading(false); }
  };

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) || selected.size === 0 || selected.size > 10 * 1024 * 1024) {
        setFile(null); setPreviewUrl(null); setResult(null);
        e.target.value = '';
        setError('JPEG, PNG, WebP 형식의 10MB 이하 이미지를 선택해 주세요.');
        return;
      }
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await estimateMealVision(file);
      setResult(data.data);
      getServiceStatus().then(setServiceStatus).catch(() => setServiceStatus('서버 연결 확인 필요'));
    } catch (err: unknown) {
      if (err instanceof AuthenticationError) handleSessionExpired();
      const message = err instanceof Error ? err.message : '';
      setError(message.includes('유효한 음식 또는 약제가 검출되지 않았습니다')
        ? '음식을 찾지 못했습니다. 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영해 주세요.'
        : message || '분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleCandidateSelect = (itemId: string, candidate: FoodCandidate) => {
    if (savingRef.current) return;
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyCandidate(item, candidate) : item);
      return { ...current, isPersisted: false, foodItems, totalNutrition: updateTotals(foodItems), requiresConfirmation: foodItems.some(item => item.requiresConfirmation) };
    });
  };

  const handleWeightChange = (itemId: string, value: string) => {
    if (savingRef.current) return;
    const weightG = Number(value);
    if (!Number.isFinite(weightG) || weightG <= 0) return;
    setResult(current => {
      if (!current) return current;
      const foodItems = current.foodItems.map(item => item.id === itemId ? applyWeight(item, weightG) : item);
      return { ...current, isPersisted: false, foodItems, totalNutrition: updateTotals(foodItems) };
    });
  };

  const handleConfirm = async () => {
    if (!result || result.requiresConfirmation || savingRef.current) return;
    savingRef.current = true;
    setSaving(true); setError(null);
    try {
      const saved = await confirmMealVision(result);
      setResult(current => current === result ? saved : current);
    } catch (err) {
      if (err instanceof AuthenticationError) handleSessionExpired();
      setError(err instanceof Error ? err.message : '저장하지 못했습니다. 다시 시도해 주세요.');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!previewUrl || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      result?.foodItems.forEach((item) => {
        const x1 = item.bbox2d.xmin * canvas.width;
        const y1 = item.bbox2d.ymin * canvas.height;
        const x2 = item.bbox2d.xmax * canvas.width;
        const y2 = item.bbox2d.ymax * canvas.height;
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 4;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        ctx.fillStyle = 'rgba(56, 189, 248, 0.85)';
        ctx.fillRect(x1, Math.max(0, y1 - 28), 190, 28);
        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 16px sans-serif';
        ctx.fillText(
          `${item.foodName} (${(item.confidenceScore * 100).toFixed(1)}%)`,
          x1 + 6,
          Math.max(0, y1 - 8)
        );
      });
    };
    img.src = previewUrl;
    return () => { img.onload = null; };
  }, [previewUrl, result]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <header className="max-w-7xl mx-auto mb-8 border-b border-slate-800 pb-5 flex flex-wrap gap-3 justify-between items-center">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-300">
            VoluMeal-Align
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            식단 체적·영양 추정 및 등록된 복약 정보 기반 상호작용 확인
          </p>
        </div>
        <span className="bg-emerald-950 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-700 font-mono">
          {serviceStatus}
        </span>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* 좌측: 파일 업로드 및 2D 검출 오버레이 */}
        <section className="lg:col-span-5 min-w-0 flex flex-col gap-5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            {signedIn ? <button disabled={loading} onClick={() => { logout(); setSignedIn(false); setResult(null); }}>로그아웃</button> :
              <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="flex flex-col gap-3">
                {authMode === 'register' && <label>이름<input className="block w-full bg-slate-800 p-2 rounded" type="text" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required /></label>}
                <label>이메일<input className="block w-full bg-slate-800 p-2 rounded" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label>
                <label>비밀번호<input className="block w-full bg-slate-800 p-2 rounded" type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} minLength={authMode === 'register' ? 8 : 1} required /></label>
                <button disabled={authLoading} type="submit" className="rounded bg-cyan-700 p-2">{authLoading ? (authMode === 'login' ? '로그인 중...' : '회원가입 중...') : (authMode === 'login' ? '로그인' : '회원가입')}</button>
                <button type="button" className="text-sm text-cyan-300 underline" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(null); }}>
                  {authMode === 'login' ? '회원가입하기' : '로그인으로 돌아가기'}
                </button>
              </form>}
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              식단 이미지 업로드
            </h2>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={loading || saving}
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
            />

            {previewUrl && (
              <div className="mt-4 rounded-lg overflow-hidden border border-slate-800 bg-slate-950">
                <canvas ref={canvasRef} className="w-full h-auto object-contain block" />
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!file || loading || saving}
              className="mt-4 w-full py-2.5 px-4 rounded-lg font-semibold text-sm bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:from-cyan-400 hover:to-teal-400 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
            >
              {loading ? '이미지 분석 중...' : '식단 분석'}
            </button>
            {error && <p role="alert" className="text-xs text-rose-400 mt-2">{error}</p>}
          </div>

          {/* KFDA 의약품 상호작용 경고창 */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span>등록 복약과 식품 상호작용</span>
                <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
                  {result.drugWarnings.length}건
                </span>
              </h2>

              {!result.isPersisted ? (
                <p className="text-xs text-amber-300">후보 선택·중량 보정 후 저장하면 복약 경고를 다시 확인합니다.</p>
              ) : result.drugWarnings.length === 0 ? (
                <div className="p-3 bg-emerald-950/40 border border-emerald-800 rounded-lg text-xs text-emerald-300">
                  이번 분석에서 반환된 상호작용 경고가 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {result.drugWarnings.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border text-xs space-y-1.5 ${
                        alert.riskLevel === 'DANGER'
                          ? 'bg-rose-950/50 border-rose-800 text-rose-200'
                          : 'bg-amber-950/50 border-amber-800 text-amber-200'
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span className="text-sm">{alert.warningTitle}</span>
                        <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-black/40 border border-current">
                          {alert.riskLevel}
                        </span>
                      </div>
                      <p className="leading-relaxed opacity-90">{alert.warningMessage}</p>
                      <div className="pt-1.5 border-t border-white/10 text-[11px] text-slate-300">
                        <span className="font-semibold text-white">임상 권고: </span>
                        {alert.actionGuide}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* 우측: Three.js 3D 체적 복원 및 지표 카드 */}
        <section className="lg:col-span-7 min-w-0 flex flex-col gap-5">
          {signedIn && <MealHistory refreshKey={result?.isPersisted ? result.mealId : undefined} onSessionExpired={handleSessionExpired} />}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              3D 점군 및 경계 상자
            </h2>
            <ThreeViewer items={result?.foodItems || EMPTY_ITEMS} pointCloud={result?.visualization3d.pointCloud} height={420} />
            {result && !result.isCalibrated && <p className="mt-2 text-xs text-amber-300">카메라 미보정 추정값입니다. 원본 이미지는 서버에 보관하지 않습니다.</p>}
          </div>

          {result && (
            <div className="rounded-xl border border-slate-800 p-4">
              <p role="status" className="text-sm text-slate-300">
                {result.isPersisted ? '저장되었습니다.' : result.requiresConfirmation ? '음식 후보를 모두 선택한 후 저장해 주세요.' : '변경 내용이 아직 저장되지 않았습니다.'}
              </p>
              <button type="button" onClick={handleConfirm}
                disabled={saving || result.isPersisted || result.requiresConfirmation || result.foodItems.length === 0}
                className="mt-2 rounded-lg bg-cyan-500 px-4 py-2 text-slate-950 disabled:opacity-50">
                {saving ? '저장 중...' : '확정하고 저장'}
              </button>
            </div>
          )}
          {result && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {result.foodItems.map((item, idx) => (
                <React.Fragment key={idx}>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">식품명</span>
                    <p className="text-base font-bold text-cyan-400 capitalize mt-0.5">{item.foodName}</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 체적</span>
                    <p className="text-base font-bold text-slate-100 mt-0.5">{item.volumeCm3} cm³</p>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 질량</span>
                    <label className="block mt-0.5">
                      <span className="sr-only">{item.foodName} 중량</span>
                      <input
                        aria-label={`${item.foodName} 중량`}
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={item.weightG}
                        onChange={event => handleWeightChange(item.id, event.target.value)}
                        disabled={saving}
                        className="w-24 bg-transparent text-base font-bold text-emerald-400 outline-none"
                      />
                      <span className="text-base font-bold text-emerald-400"> g</span>
                    </label>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                    <span className="text-[11px] text-slate-400 uppercase">추정 열량</span>
                    <p className="text-base font-bold text-slate-300 mt-0.5 font-mono">
                      {item.caloriesKcal.toLocaleString()} kcal
                    </p>
                  </div>
                  {item.requiresConfirmation && (
                    <div className="col-span-2 sm:col-span-4 border border-amber-700 bg-amber-950/40 p-3.5 rounded-xl">
                      <p className="text-sm font-semibold text-amber-200">음식 확인이 필요합니다. 후보를 선택해 주세요.</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.topCandidates.map(candidate => (
                          <button
                            key={candidate.foodId}
                            type="button"
                            onClick={() => handleCandidateSelect(item.id, candidate)}
                            disabled={saving}
                            className="rounded border border-amber-600 bg-amber-900/50 px-3 py-2 text-left text-xs text-amber-100 hover:bg-amber-800"
                          >
                            <span className="block font-semibold">{candidate.foodName}</span>
                            <span className="text-amber-300">유사도 {(candidate.score * 100).toFixed(0)}%</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
>>>>>>> REPLACE
```

## frontend/src/types/vision.ts

```text
파일 경로: frontend/src/types/vision.ts
<<<<<<< SEARCH
// Generated from backend/src/schemas/vision.py. Do not edit manually.

export interface BoundingBox2D {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface BoundingBox3D {
  center: Point3D;
  dimensions: Point3D;
  rotations: Point3D;
  vertices: Array<Point3D>;
}

export interface DrugInteractionWarning {
  id: string;
  drugBrandName: string;
  drugIngredient: string;
  triggerNutrientOrFood: string;
  riskLevel: string;
  detectedVia: string;
  warningTitle: string;
  warningMessage: string;
  actionGuide: string;
}

export interface FoodCandidate {
  foodId: string;
  foodName: string;
  score: number;
  densityGCm3?: number;
  weightG?: number;
  caloriesKcal?: number;
  carbsG?: number;
  proteinG?: number;
  fatG?: number;
  sodiumMg?: number;
}

export interface FoodItemEstimation {
  id: string;
  foodId: string;
  foodName: string;
  confidenceScore: number;
  classificationConfidence: number;
  geometryConfidence: number;
  requiresConfirmation: boolean;
  topCandidates: Array<FoodCandidate>;
  volumeCm3: number;
  densityGCm3: number;
  weightG: number;
  caloriesKcal: number;
  carbsG: number;
  proteinG: number;
  fatG: number;
  sodiumMg: number;
  bbox2d: BoundingBox2D;
  bbox3d: BoundingBox3D;
}

export interface NutritionSummary {
  caloriesKcal: number;
  carbsG: number;
  proteinG: number;
  fatG: number;
  sodiumMg: number;
}

export interface PlaneEquation {
  a: number;
  b: number;
  c: number;
  d: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface SparsePointCloudPayload {
  count: number;
  positions: Array<number>;
  colors: Array<number>;
}

export interface Visualization3D {
  pointCloud: SparsePointCloudPayload;
}

export interface MealEstimateResponse {
  mealId: string;
  isPersisted: boolean;
  requiresConfirmation: boolean;
  imageUrl: string;
  isCalibrated: boolean;
  focalLengthMm: number;
  groundPlane: PlaneEquation;
  totalNutrition: NutritionSummary;
  foodItems: Array<FoodItemEstimation>;
  drugWarnings: Array<DrugInteractionWarning>;
  visualization3d: Visualization3D;
  processedAt: string;
  inferenceLatencyMs: number;
}
=======
// Generated from backend/src/schemas/vision.py. Do not edit manually.

export interface BoundingBox2D {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface BoundingBox3D {
  center: Point3D;
  dimensions: Point3D;
  rotations: Point3D;
  vertices: Array<Point3D>;
}

export interface DetectedPillInput {
  class_name: string;
  class_id?: number | null;
  confidence?: number | null;
  box?: Array<number> | null;
}

export interface DrugInteractionWarning {
  id: string;
  drugBrandName: string;
  drugIngredient: string;
  triggerNutrientOrFood: string;
  riskLevel: string;
  detectedVia: string;
  warningTitle: string;
  warningMessage: string;
  actionGuide: string;
}

export interface FoodCandidate {
  foodId: string;
  foodName: string;
  score: number;
  densityGCm3?: number | null;
  weightG?: number | null;
  caloriesKcal?: number | null;
  carbsG?: number | null;
  proteinG?: number | null;
  fatG?: number | null;
  sodiumMg?: number | null;
}

export interface FoodItemEstimation {
  id: string;
  foodId: string;
  foodName: string;
  confidenceScore: number;
  classificationConfidence: number;
  geometryConfidence: number;
  requiresConfirmation: boolean;
  topCandidates: Array<FoodCandidate>;
  volumeCm3: number;
  densityGCm3: number;
  weightG: number;
  caloriesKcal: number;
  carbsG: number;
  proteinG: number;
  fatG: number;
  sodiumMg: number;
  bbox2d: BoundingBox2D;
  bbox3d: BoundingBox3D;
}

export interface NutritionSummary {
  caloriesKcal: number;
  carbsG: number;
  proteinG: number;
  fatG: number;
  sodiumMg: number;
}

export interface PlaneEquation {
  a: number;
  b: number;
  c: number;
  d: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface SparsePointCloudPayload {
  count: number;
  positions: Array<number>;
  colors: Array<number>;
}

export interface Visualization3D {
  pointCloud: SparsePointCloudPayload;
}

export interface MealEstimateResponse {
  mealId: string;
  isPersisted: boolean;
  requiresConfirmation: boolean;
  imageUrl: string;
  isCalibrated: boolean;
  focalLengthMm: number;
  groundPlane: PlaneEquation;
  totalNutrition: NutritionSummary;
  foodItems: Array<FoodItemEstimation>;
  drugWarnings: Array<DrugInteractionWarning>;
  detectedPills?: Array<DetectedPillInput>;
  visualization3d: Visualization3D;
  processedAt: string;
  inferenceLatencyMs: number;
}
>>>>>>> REPLACE
```

## backend/tests/integration/test_database_flow.py

```text
파일 경로: backend/tests/integration/test_database_flow.py
<<<<<<< SEARCH
"""Opt-in PostgreSQL regression tests. Every test rolls back its outer transaction."""
import copy
import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import bcrypt
import httpx
import pytest
import pytest_asyncio
from PIL import Image
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.main import app
from src.core.config import settings
from src.core.database import get_db_session
from src.models.entities import User,Drug,DrugFoodContraindication,Meal

pytestmark=pytest.mark.skipif(os.getenv('RUN_DB_TESTS')!='1',reason='Set RUN_DB_TESTS=1 to run rolled-back PostgreSQL checks')

@pytest_asyncio.fixture
async def environment():
    engine=create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        transaction=await connection.begin()
        async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as db:
            first=User(id=uuid.uuid4(),email=f'{uuid.uuid4()}@test.invalid',name='test',role='USER',hashed_password=bcrypt.hashpw(b'test-password',bcrypt.gensalt(rounds=4)).decode())
            other=User(id=uuid.uuid4(),email=f'{uuid.uuid4()}@test.invalid',name='other',role='USER',hashed_password=first.hashed_password)
            drug=Drug(id=uuid.uuid4(),kd_code=uuid.uuid4().hex[:9],brand_name='Test drug',ingredient_name='Test ingredient',therapeutic_class='test')
            db.add_all([first,other,drug]);await db.flush()
            db.add(DrugFoodContraindication(id=uuid.uuid4(),drug_id=drug.id,trigger_nutrient='TEST',risk_level='DANGER',mechanism_desc='test only',action_guide='test only',source_authority='test fixture'))
            await db.flush()
            await db.commit()
            async def get_test_db():
                async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as request_db:
                    try: yield request_db
                    except Exception:
                        await request_db.rollback()
                        raise
            app.dependency_overrides[get_db_session]=get_test_db
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                yield client,db,first,other,drug
            app.dependency_overrides.clear()
        await transaction.rollback()
    await engine.dispose()

def auth(user):
    token=jwt.encode({'sub':str(user.id),'exp':datetime.now(timezone.utc)+timedelta(minutes=5)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    return {'Authorization':f'Bearer {token}'}

def analysis_result(requires_confirmation=False, detected_pills=None, trigger='test'):
    item={'id':str(uuid.uuid4()),'foodId':'FOOD_TEST','foodName':'test_food','confidenceScore':.9,
          'classificationConfidence':.91,'geometryConfidence':.86,
          'requiresConfirmation':requires_confirmation,
          'topCandidates':[{'foodId':'FOOD_TEST','foodName':'test_food','score':.91}],
          'volumeCm3':100.,'densityGCm3':1.,'weightG':100.,'caloriesKcal':100.,
          'carbsG':20.,'proteinG':3.,'fatG':1.,'sodiumMg':4.,
          'bbox2d':{'xmin':.1,'ymin':.1,'xmax':.5,'ymax':.5},
          'bbox3d':{'center':{'x':0,'y':0,'z':.55},'dimensions':{'x':.1,'y':.1,'z':.1},
                    'rotations':{'x':0,'y':0,'z':0},'vertices':[]}}
    return {'foodItems':[item],'totalNutrition':{key:item[key] for key in ('caloriesKcal','carbsG','proteinG','fatG','sodiumMg')},'groundPlane':{'a':0,'b':0,'c':1,'d':-.6},'visualization3d':{'pointCloud':{'count':0,'positions':[],'colors':[]}},'triggers':{item['id']:{trigger.lower()}},'detectedPills':detected_pills or []}


@pytest.mark.asyncio
async def test_login_and_medication_ownership(environment):
    client,db,first,other,drug=environment
    response=await client.post('/api/v1/auth/login',json={'email':first.email,'password':'test-password'})
    assert response.status_code==200,response.text
    headers={'Authorization':'Bearer '+response.json()['accessToken']}
    bad=await client.post('/api/v1/auth/login',json={'email':first.email,'password':'wrong'})
    assert bad.status_code==401
    created=await client.post('/api/v1/medications',headers=headers,json={'drugId':str(drug.id),'prescribedDosageMg':5})
    assert created.status_code==201,created.text
    med_id=created.json()['id']
    own=await client.get('/api/v1/medications',headers=headers)
    assert med_id in [m['id'] for m in own.json()]
    assert (await client.get('/api/v1/medications',headers=auth(other))).json()==[]
    assert (await client.delete('/api/v1/medications/'+med_id,headers=auth(other))).status_code==404
    assert (await client.delete('/api/v1/medications/'+med_id,headers=headers)).status_code==204
    assert (await client.get('/api/v1/medications',headers=headers)).json()==[]

@pytest.mark.asyncio
async def test_analysis_persistence_and_profile_specific_warning(environment):
    client,db,first,other,drug=environment
    await client.post('/api/v1/medications',headers=auth(first),json={'drugId':str(drug.id),'prescribedDosageMg':5})
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=SimpleNamespace(process_image=lambda *args:analysis_result())):
        response=await client.post('/api/v1/vision/estimate',headers=auth(first),files={'file':('test.png',image.getvalue(),'image/png')})
        assert response.status_code==200,response.text
        data=response.json()['data']
        assert len(data['drugWarnings'])==1
        assert data['imageUrl']=='' and data['isCalibrated'] is False
        meal_id=data['mealId']
        detail=await client.get('/api/v1/meals/'+meal_id,headers=auth(first))
        assert detail.status_code==200,detail.text
        assert len(detail.json()['foodItems'])==1
        assert len(detail.json()['drugWarnings'])==1
        assert (await client.get('/api/v1/meals/'+meal_id,headers=auth(other))).status_code==404
        other_response=await client.post('/api/v1/vision/estimate',headers=auth(other),files={'file':('test.png',image.getvalue(),'image/png')})
        assert other_response.status_code==200,other_response.text
        assert other_response.json()['data']['drugWarnings']==[]
    res = await client.get('/api/v1/meals', headers=auth(first))
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["success"] is True
    assert res_json["data"]["totalCount"] == 1
    items = res_json["data"]["items"]
    assert [m['id'] for m in items] == [meal_id]
    assert items[0]["highestRiskLevel"] in ("DANGER", "CAUTION")

@pytest.mark.asyncio
async def test_low_confidence_analysis_is_not_persisted(environment):
    client,db,first,other,drug=environment
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    pipeline=SimpleNamespace(process_image=lambda *args:analysis_result(True))
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=pipeline):
        response=await client.post('/api/v1/vision/estimate',headers=auth(first),
                                   files={'file':('test.png',image.getvalue(),'image/png')})
    assert response.status_code==200,response.text
    data=response.json()['data']
    assert data['requiresConfirmation'] is True
    assert data['isPersisted'] is False
    assert (await client.get('/api/v1/meals',headers=auth(first))).json()["data"]["items"]==[]

@pytest.mark.asyncio
async def test_failed_save_rolls_back_food_and_meal(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock
    client,db,first,other,drug=environment
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=SimpleNamespace(process_image=lambda *args:analysis_result())):
        with patch('src.api.v1.endpoints.vision.AsyncSession.commit',new=AsyncMock(side_effect=SQLAlchemyError('test failure'))):
            response=await client.post('/api/v1/vision/estimate',headers=auth(first),files={'file':('test.png',image.getvalue(),'image/png')})
    assert response.status_code==503
    assert (await client.get('/api/v1/meals',headers=auth(first))).json()["data"]["items"]==[]


@pytest.mark.asyncio
async def test_visual_grounding_pill_generates_warning(environment):
    client, db, first, other, drug = environment
    # Use existing coumadin drug with KD code '641800240' if present, otherwise create
    coumadin = (await db.execute(select(Drug).where(Drug.kd_code == "641800240"))).scalar_one_or_none()
    if not coumadin:
        coumadin = Drug(
            id=uuid.uuid4(),
            kd_code="641800240",
            brand_name="쿠마딘정5밀리그람",
            ingredient_name="와파린나트륨 (Warfarin Sodium)",
            therapeutic_class="항응고제",
        )
        db.add(coumadin)
        await db.flush()

    contra = (await db.execute(
        select(DrugFoodContraindication).where(
            DrugFoodContraindication.drug_id == coumadin.id,
            DrugFoodContraindication.trigger_nutrient == "Vitamin_K",
        )
    )).scalar_one_or_none()
    if not contra:
        db.add(
            DrugFoodContraindication(
                id=uuid.uuid4(),
                drug_id=coumadin.id,
                trigger_nutrient="Vitamin_K",
                risk_level="DANGER",
                mechanism_desc="와파린 약효 길항",
                action_guide="비타민 K 섭취 주의",
                source_authority="식품의약품안전처",
            )
        )
        await db.flush()
    await db.commit()

    # User 'first' has NOT registered coumadin in their active medications!
    # A pill is visually detected in the image:
    pills = [{"class_id": 9, "class_name": "coumadin_pill", "confidence": 0.94, "box": [10, 10, 30, 30]}]
    simulated = analysis_result(detected_pills=pills, trigger="Vitamin_K")

    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    with patch("src.api.v1.endpoints.vision.get_pipeline", return_value=SimpleNamespace(process_image=lambda *args: simulated)):
        response = await client.post(
            "/api/v1/vision/estimate",
            headers=auth(first),
            files={"file": ("test.png", image.getvalue(), "image/png")},
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert len(data["drugWarnings"]) == 1
        warning = data["drugWarnings"][0]
        assert warning["detectedVia"] == "VISUAL_GROUNDING"
        assert warning["drugBrandName"] == "쿠마딘정5밀리그람"
        assert warning["riskLevel"] == "DANGER"
        assert "[시각 접지]" in warning["warningTitle"]

        # Verify DB persistence has detected_via == 'VISUAL_GROUNDING'
        meal_id = data["mealId"]
        detail = await client.get("/api/v1/meals/" + meal_id, headers=auth(first))
        assert detail.status_code == 200
        saved_warnings = detail.json()["drugWarnings"]
        assert len(saved_warnings) == 1
        assert saved_warnings[0]["detectedVia"] == "VISUAL_GROUNDING"


@pytest.mark.asyncio
async def test_manual_confirmation_recalculates_and_persists(environment):
    client, db, first, other, drug = environment

    # 1. Ensure coumadin drug exists for interaction checks
    coumadin = (await db.execute(select(Drug).where(Drug.kd_code == "641800240"))).scalar_one_or_none()
    if not coumadin:
        coumadin = Drug(
            id=uuid.uuid4(),
            kd_code="641800240",
            brand_name="쿠마딘정5밀리그람",
            ingredient_name="와파린나트륨 (Warfarin Sodium)",
            therapeutic_class="항응고제",
        )
        db.add(coumadin)
        await db.flush()

    contra = (await db.execute(
        select(DrugFoodContraindication).where(
            DrugFoodContraindication.drug_id == coumadin.id,
            DrugFoodContraindication.trigger_nutrient == "Vitamin_K",
        )
    )).scalar_one_or_none()
    if not contra:
        db.add(
            DrugFoodContraindication(
                id=uuid.uuid4(),
                drug_id=coumadin.id,
                trigger_nutrient="Vitamin_K",
                risk_level="DANGER",
                mechanism_desc="와파린 약효 길항",
                action_guide="비타민 K 섭취 주의",
                source_authority="식품의약품안전처",
            )
        )
        await db.flush()
    await db.commit()

    # User registers coumadin as active medication
    await client.post('/api/v1/medications', headers=auth(first), json={'drugId': str(coumadin.id), 'prescribedDosageMg': 5})

    # 2. Simulate estimate returning requiresConfirmation=true
    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    pipeline = SimpleNamespace(process_image=lambda *args: analysis_result(requires_confirmation=True, detected_pills=[{"class_name": "coumadin_pill"}]))
    with patch("src.api.v1.endpoints.vision.get_pipeline", return_value=pipeline):
        estimate_res = await client.post(
            "/api/v1/vision/estimate",
            headers=auth(first),
            files={"file": ("test.png", image.getvalue(), "image/png")},
        )
    assert estimate_res.status_code == 200
    est_data = estimate_res.json()["data"]
    assert est_data["requiresConfirmation"] is True
    assert est_data["isPersisted"] is False
    temp_meal_id = est_data["mealId"]
    food_item = est_data["foodItems"][0]
    item_id = food_item["id"]

    # At this point, meals list in DB must be empty
    assert (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"] == []

    # 3. User manually confirms selection as 'spinach_namul' (which has 'vitamin_k' tag)
    confirm_payload = {
        "mealId": temp_meal_id,
        "imageUrl": "https://storage.example.com/meals/confirmed.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "spinach_namul",
            }
        ],
        "volumeData": [
            {
                "itemId": item_id,
                "volumeCm3": 150.0,
                "confidenceScore": 0.95,
                "bbox2d": food_item["bbox2d"],
                "bbox3d": food_item["bbox3d"],
            }
        ],
        "detectedPills": [
            {"class_name": "coumadin_pill"}
        ]
    }

    confirm_res = await client.post(
        "/api/v1/vision/confirm",
        headers=auth(first),
        json=confirm_payload,
    )
    assert confirm_res.status_code == 200, confirm_res.text
    confirm_json = confirm_res.json()
    assert confirm_json["success"] is True
    assert confirm_json["mealId"] == temp_meal_id
    assert confirm_json["data"]["isPersisted"] is True

    # 4. Verify nutrition recalculation:
    # spinach_namul density in food_density_profiles.json is 0.55 g/cm3 -> 150 * 0.55 = 82.5g
    nutrition = confirm_json["totalNutrition"]
    assert nutrition["caloriesKcal"] > 0
    assert len(confirm_json["data"]["foodItems"]) == 1
    confirmed_food = confirm_json["data"]["foodItems"][0]
    assert confirmed_food["foodId"] == "spinach_namul"
    assert confirmed_food["foodName"] == "시금치나물"
    assert confirmed_food["volumeCm3"] == 150.0
    assert confirmed_food["weightG"] == round(150.0 * confirmed_food["densityGCm3"], 2)

    # 5. Verify drug warnings generated for spinach_namul + coumadin
    warnings = confirm_json["drugWarnings"]
    assert len(warnings) >= 1
    detected_vias = {w["detectedVia"] for w in warnings}
    assert "VISUAL_GROUNDING" in detected_vias or "USER_PROFILE" in detected_vias

    # 6. Verify DB persistence and detail endpoint
    detail_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(first))
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["id"] == temp_meal_id
    assert detail["imageUrl"] == "https://storage.example.com/meals/confirmed.jpg"
    assert len(detail["foodItems"]) == 1
    assert detail["foodItems"][0]["foodName"] == "시금치나물"
    assert float(detail["foodItems"][0]["volumeCm3"]) == 150.0
    assert len(detail["drugWarnings"]) >= 1

    # 7. Verify ownership isolation (other user cannot access)
    other_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(other))
    assert other_res.status_code == 404


@pytest.mark.asyncio
async def test_manual_confirmation_failure_rolls_back(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock

    client, db, first, other, drug = environment
    item_id = str(uuid.uuid4())
    meal_id = str(uuid.uuid4())

    confirm_payload = {
        "mealId": meal_id,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "white_rice",
                "volumeCm3": 100.0,
            }
        ]
    }

    with patch("src.api.v1.endpoints.vision.AsyncSession.commit", new=AsyncMock(side_effect=SQLAlchemyError("atomic commit failure"))):
        res = await client.post(
            "/api/v1/vision/confirm",
            headers=auth(first),
            json=confirm_payload,
        )
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "ERR_DATABASE_UNAVAILABLE"

    # Verify no partial meal was saved in DB
    meals = (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"]
    assert all(m["id"] != meal_id for m in meals)


@pytest.mark.asyncio
async def test_registration_db_flow(environment):
    client, db, first, other, drug = environment
    new_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    raw_pw = "RegisterTestPassword123!"


    # 1. Successful registration
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": new_email, "password": raw_pw, "name": "신규등록자"},
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert reg_data["email"] == new_email
    assert reg_data["name"] == "신규등록자"
    assert reg_data["role"] == "USER"
    assert "id" in reg_data

    # 2. Login with newly registered user
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": new_email, "password": raw_pw},
    )
    assert login_res.status_code == 200, login_res.text
    assert "accessToken" in login_res.json()
    new_headers = {"Authorization": f"Bearer {login_res.json()['accessToken']}"}

    # 3. Meals list should be empty initially for new user
    meals_res = await client.get("/api/v1/meals", headers=new_headers)
    assert meals_res.status_code == 200
    assert meals_res.json()["data"]["totalCount"] == 0
    assert meals_res.json()["data"]["items"] == []

    # 4. Duplicate registration returns 409 Conflict
    dup_res = await client.post(
        "/api/v1/auth/register",
        json={"email": new_email, "password": raw_pw, "name": "중복등록자"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["detail"] == "이미 등록된 이메일 주소입니다."


@pytest.mark.asyncio
async def test_drug_interactions_db_flow(environment):
    client, db, first, other, drug = environment

    # 1. Unauthenticated request rejected with 401
    unauth_res = await client.get("/api/v1/drugs/interactions")
    assert unauth_res.status_code == 401

    # 2. Authenticated query returns populated interactions
    res = await client.get("/api/v1/drugs/interactions", headers=auth(first))
    assert res.status_code == 200, res.text
    rules = res.json()
    assert isinstance(rules, list)
    assert len(rules) >= 1

    # Verify rule structure
    rule = rules[0]
    assert "id" in rule
    assert "drugId" in rule
    assert "kdCode" in rule
    assert "brandName" in rule
    assert "ingredientName" in rule
    assert "triggerNutrient" in rule
    assert "riskLevel" in rule
    assert "mechanismDesc" in rule
    assert "actionGuide" in rule
    assert "sourceAuthority" in rule

    # 3. Filter by kdCode
    filtered = await client.get(f"/api/v1/drugs/interactions?kdCode={drug.kd_code}", headers=auth(first))
    assert filtered.status_code == 200
    filtered_rules = filtered.json()
    assert len(filtered_rules) >= 1
    assert all(r["kdCode"] == drug.kd_code for r in filtered_rules)


@pytest.mark.asyncio
async def test_analysis_persistence_with_is_calibrated_true(environment):
    client, db, first, other, drug = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=SimpleNamespace(process_image=lambda *args: analysis_result())):
        response = await client.post(
            '/api/v1/vision/estimate',
            headers=auth(first),
            files={'file': ('calibrated.png', image.getvalue(), 'image/png')},
            data={'is_calibrated': 'true', 'focal_length_mm': '35.0'},
        )
        assert response.status_code == 200, response.text
        data = response.json()['data']
        assert data['isCalibrated'] is True
        assert data['focalLengthMm'] == 35.0
        meal_id = data['mealId']

        # DB에 is_calibrated=True가 보존되었는지 검증
        db_meal = (await db.execute(select(Meal).where(Meal.id == uuid.UUID(meal_id)))).scalar_one()
        assert db_meal.is_calibrated is True
        assert db_meal.focal_length_mm == 35.0
=======
"""Opt-in PostgreSQL regression tests. Every test rolls back its outer transaction."""
import copy
import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import bcrypt
import httpx
import pytest
import pytest_asyncio
from PIL import Image
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.main import app
from src.core.config import settings
from src.core.database import get_db_session
from src.models.entities import User,Drug,DrugFoodContraindication,Meal

pytestmark=pytest.mark.skipif(os.getenv('RUN_DB_TESTS')!='1',reason='Set RUN_DB_TESTS=1 to run rolled-back PostgreSQL checks')

@pytest_asyncio.fixture
async def environment():
    engine=create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        transaction=await connection.begin()
        async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as db:
            first=User(id=uuid.uuid4(),email=f'{uuid.uuid4()}@test.invalid',name='test',role='USER',hashed_password=bcrypt.hashpw(b'test-password',bcrypt.gensalt(rounds=4)).decode())
            other=User(id=uuid.uuid4(),email=f'{uuid.uuid4()}@test.invalid',name='other',role='USER',hashed_password=first.hashed_password)
            drug=Drug(id=uuid.uuid4(),kd_code=uuid.uuid4().hex[:9],brand_name='Test drug',ingredient_name='Test ingredient',therapeutic_class='test')
            db.add_all([first,other,drug]);await db.flush()
            db.add(DrugFoodContraindication(id=uuid.uuid4(),drug_id=drug.id,trigger_nutrient='TEST',risk_level='DANGER',mechanism_desc='test only',action_guide='test only',source_authority='test fixture'))
            await db.flush()
            await db.commit()
            async def get_test_db():
                async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as request_db:
                    try: yield request_db
                    except Exception:
                        await request_db.rollback()
                        raise
            app.dependency_overrides[get_db_session]=get_test_db
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                yield client,db,first,other,drug
            app.dependency_overrides.clear()
        await transaction.rollback()
    await engine.dispose()

def auth(user):
    token=jwt.encode({'sub':str(user.id),'exp':datetime.now(timezone.utc)+timedelta(minutes=5)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    return {'Authorization':f'Bearer {token}'}

def analysis_result(requires_confirmation=False, detected_pills=None, trigger='test'):
    item={'id':str(uuid.uuid4()),'foodId':'FOOD_TEST','foodName':'test_food','confidenceScore':.9,
          'classificationConfidence':.91,'geometryConfidence':.86,
          'requiresConfirmation':requires_confirmation,
          'topCandidates':[{'foodId':'FOOD_TEST','foodName':'test_food','score':.91}],
          'volumeCm3':100.,'densityGCm3':1.,'weightG':100.,'caloriesKcal':100.,
          'carbsG':20.,'proteinG':3.,'fatG':1.,'sodiumMg':4.,
          'bbox2d':{'xmin':.1,'ymin':.1,'xmax':.5,'ymax':.5},
          'bbox3d':{'center':{'x':0,'y':0,'z':.55},'dimensions':{'x':.1,'y':.1,'z':.1},
                    'rotations':{'x':0,'y':0,'z':0},'vertices':[]}}
    return {'foodItems':[item],'totalNutrition':{key:item[key] for key in ('caloriesKcal','carbsG','proteinG','fatG','sodiumMg')},'groundPlane':{'a':0,'b':0,'c':1,'d':-.6},'visualization3d':{'pointCloud':{'count':0,'positions':[],'colors':[]}},'triggers':{item['id']:{trigger.lower()}},'detectedPills':detected_pills or []}


@pytest.mark.asyncio
async def test_login_and_medication_ownership(environment):
    client,db,first,other,drug=environment
    response=await client.post('/api/v1/auth/login',json={'email':first.email,'password':'test-password'})
    assert response.status_code==200,response.text
    headers={'Authorization':'Bearer '+response.json()['accessToken']}
    bad=await client.post('/api/v1/auth/login',json={'email':first.email,'password':'wrong'})
    assert bad.status_code==401
    created=await client.post('/api/v1/medications',headers=headers,json={'drugId':str(drug.id),'prescribedDosageMg':5})
    assert created.status_code==201,created.text
    med_id=created.json()['id']
    own=await client.get('/api/v1/medications',headers=headers)
    assert med_id in [m['id'] for m in own.json()]
    assert (await client.get('/api/v1/medications',headers=auth(other))).json()==[]
    assert (await client.delete('/api/v1/medications/'+med_id,headers=auth(other))).status_code==404
    assert (await client.delete('/api/v1/medications/'+med_id,headers=headers)).status_code==204
    assert (await client.get('/api/v1/medications',headers=headers)).json()==[]

@pytest.mark.asyncio
async def test_analysis_persistence_and_profile_specific_warning(environment):
    client,db,first,other,drug=environment
    await client.post('/api/v1/medications',headers=auth(first),json={'drugId':str(drug.id),'prescribedDosageMg':5})
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=SimpleNamespace(process_image=lambda *args:analysis_result())):
        response=await client.post('/api/v1/vision/estimate',headers=auth(first),files={'file':('test.png',image.getvalue(),'image/png')})
        assert response.status_code==200,response.text
        data=response.json()['data']
        assert len(data['drugWarnings'])==1
        assert data['imageUrl']=='' and data['isCalibrated'] is False
        meal_id=data['mealId']
        detail=await client.get('/api/v1/meals/'+meal_id,headers=auth(first))
        assert detail.status_code==200,detail.text
        assert len(detail.json()['foodItems'])==1
        assert len(detail.json()['drugWarnings'])==1
        assert (await client.get('/api/v1/meals/'+meal_id,headers=auth(other))).status_code==404
        other_response=await client.post('/api/v1/vision/estimate',headers=auth(other),files={'file':('test.png',image.getvalue(),'image/png')})
        assert other_response.status_code==200,other_response.text
        assert other_response.json()['data']['drugWarnings']==[]
    res = await client.get('/api/v1/meals', headers=auth(first))
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["success"] is True
    assert res_json["data"]["totalCount"] == 1
    items = res_json["data"]["items"]
    assert [m['id'] for m in items] == [meal_id]
    assert items[0]["highestRiskLevel"] in ("DANGER", "CAUTION")

@pytest.mark.asyncio
async def test_low_confidence_analysis_is_not_persisted(environment):
    client,db,first,other,drug=environment
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    pipeline=SimpleNamespace(process_image=lambda *args:analysis_result(True))
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=pipeline):
        response=await client.post('/api/v1/vision/estimate',headers=auth(first),
                                   files={'file':('test.png',image.getvalue(),'image/png')})
    assert response.status_code==200,response.text
    data=response.json()['data']
    assert data['requiresConfirmation'] is True
    assert data['isPersisted'] is False
    assert (await client.get('/api/v1/meals',headers=auth(first))).json()["data"]["items"]==[]

@pytest.mark.asyncio
async def test_failed_save_rolls_back_food_and_meal(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock
    client,db,first,other,drug=environment
    image=io.BytesIO();Image.new('RGB',(100,100)).save(image,format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline',return_value=SimpleNamespace(process_image=lambda *args:analysis_result())):
        with patch('src.api.v1.endpoints.vision.AsyncSession.commit',new=AsyncMock(side_effect=SQLAlchemyError('test failure'))):
            response=await client.post('/api/v1/vision/estimate',headers=auth(first),files={'file':('test.png',image.getvalue(),'image/png')})
    assert response.status_code==503
    assert (await client.get('/api/v1/meals',headers=auth(first))).json()["data"]["items"]==[]


@pytest.mark.asyncio
async def test_visual_grounding_pill_generates_warning(environment):
    client, db, first, other, drug = environment
    # Use existing coumadin drug with KD code '641800240' if present, otherwise create
    coumadin = (await db.execute(select(Drug).where(Drug.kd_code == "641800240"))).scalar_one_or_none()
    if not coumadin:
        coumadin = Drug(
            id=uuid.uuid4(),
            kd_code="641800240",
            brand_name="쿠마딘정5밀리그람",
            ingredient_name="와파린나트륨 (Warfarin Sodium)",
            therapeutic_class="항응고제",
        )
        db.add(coumadin)
        await db.flush()

    contra = (await db.execute(
        select(DrugFoodContraindication).where(
            DrugFoodContraindication.drug_id == coumadin.id,
            DrugFoodContraindication.trigger_nutrient == "Vitamin_K",
        )
    )).scalar_one_or_none()
    if not contra:
        db.add(
            DrugFoodContraindication(
                id=uuid.uuid4(),
                drug_id=coumadin.id,
                trigger_nutrient="Vitamin_K",
                risk_level="DANGER",
                mechanism_desc="와파린 약효 길항",
                action_guide="비타민 K 섭취 주의",
                source_authority="식품의약품안전처",
            )
        )
        await db.flush()
    await db.commit()

    # User 'first' has NOT registered coumadin in their active medications!
    # A pill is visually detected in the image:
    pills = [{"class_id": 9, "class_name": "coumadin_pill", "confidence": 0.94, "box": [10, 10, 30, 30]}]
    simulated = analysis_result(detected_pills=pills, trigger="Vitamin_K")

    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    with patch("src.api.v1.endpoints.vision.get_pipeline", return_value=SimpleNamespace(process_image=lambda *args: simulated)):
        response = await client.post(
            "/api/v1/vision/estimate",
            headers=auth(first),
            files={"file": ("test.png", image.getvalue(), "image/png")},
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert len(data["drugWarnings"]) == 1
        warning = data["drugWarnings"][0]
        assert warning["detectedVia"] == "VISUAL_GROUNDING"
        assert warning["drugBrandName"] == "쿠마딘정5밀리그람"
        assert warning["riskLevel"] == "DANGER"
        assert "[시각 접지]" in warning["warningTitle"]

        # Verify DB persistence has detected_via == 'VISUAL_GROUNDING'
        meal_id = data["mealId"]
        detail = await client.get("/api/v1/meals/" + meal_id, headers=auth(first))
        assert detail.status_code == 200
        saved_warnings = detail.json()["drugWarnings"]
        assert len(saved_warnings) == 1
        assert saved_warnings[0]["detectedVia"] == "VISUAL_GROUNDING"


@pytest.mark.asyncio
async def test_manual_confirmation_recalculates_and_persists(environment):
    client, db, first, other, drug = environment

    # 1. Ensure coumadin drug exists for interaction checks
    coumadin = (await db.execute(select(Drug).where(Drug.kd_code == "641800240"))).scalar_one_or_none()
    if not coumadin:
        coumadin = Drug(
            id=uuid.uuid4(),
            kd_code="641800240",
            brand_name="쿠마딘정5밀리그람",
            ingredient_name="와파린나트륨 (Warfarin Sodium)",
            therapeutic_class="항응고제",
        )
        db.add(coumadin)
        await db.flush()

    contra = (await db.execute(
        select(DrugFoodContraindication).where(
            DrugFoodContraindication.drug_id == coumadin.id,
            DrugFoodContraindication.trigger_nutrient == "Vitamin_K",
        )
    )).scalar_one_or_none()
    if not contra:
        db.add(
            DrugFoodContraindication(
                id=uuid.uuid4(),
                drug_id=coumadin.id,
                trigger_nutrient="Vitamin_K",
                risk_level="DANGER",
                mechanism_desc="와파린 약효 길항",
                action_guide="비타민 K 섭취 주의",
                source_authority="식품의약품안전처",
            )
        )
        await db.flush()
    await db.commit()

    # User registers coumadin as active medication
    await client.post('/api/v1/medications', headers=auth(first), json={'drugId': str(coumadin.id), 'prescribedDosageMg': 5})

    # 2. Simulate estimate returning requiresConfirmation=true
    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    pipeline = SimpleNamespace(process_image=lambda *args: analysis_result(requires_confirmation=True, detected_pills=[{"class_name": "coumadin_pill"}]))
    with patch("src.api.v1.endpoints.vision.get_pipeline", return_value=pipeline):
        estimate_res = await client.post(
            "/api/v1/vision/estimate",
            headers=auth(first),
            files={"file": ("test.png", image.getvalue(), "image/png")},
        )
    assert estimate_res.status_code == 200
    est_data = estimate_res.json()["data"]
    assert est_data["requiresConfirmation"] is True
    assert est_data["isPersisted"] is False
    temp_meal_id = est_data["mealId"]
    food_item = est_data["foodItems"][0]
    item_id = food_item["id"]

    # At this point, meals list in DB must be empty
    assert (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"] == []

    # 3. User manually confirms selection as 'spinach_namul' (which has 'vitamin_k' tag)
    confirm_payload = {
        "mealId": temp_meal_id,
        "imageUrl": "https://storage.example.com/meals/confirmed.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "spinach_namul",
            }
        ],
        "volumeData": [
            {
                "itemId": item_id,
                "volumeCm3": 150.0,
                "confidenceScore": 0.95,
                "bbox2d": food_item["bbox2d"],
                "bbox3d": food_item["bbox3d"],
            }
        ],
        "detectedPills": [
            {"class_name": "coumadin_pill"}
        ]
    }

    confirm_res = await client.post(
        "/api/v1/vision/confirm",
        headers=auth(first),
        json=confirm_payload,
    )
    assert confirm_res.status_code == 200, confirm_res.text
    confirm_json = confirm_res.json()
    assert confirm_json["success"] is True
    assert confirm_json["mealId"] == temp_meal_id
    assert confirm_json["data"]["isPersisted"] is True

    # 4. Verify nutrition recalculation:
    # spinach_namul density in food_density_profiles.json is 0.55 g/cm3 -> 150 * 0.55 = 82.5g
    nutrition = confirm_json["totalNutrition"]
    assert nutrition["caloriesKcal"] > 0
    assert len(confirm_json["data"]["foodItems"]) == 1
    confirmed_food = confirm_json["data"]["foodItems"][0]
    assert confirmed_food["foodId"] == "spinach_namul"
    assert confirmed_food["foodName"] == "시금치나물"
    assert confirmed_food["volumeCm3"] == 150.0
    assert confirmed_food["weightG"] == round(150.0 * confirmed_food["densityGCm3"], 2)

    # 5. Verify drug warnings generated for spinach_namul + coumadin
    warnings = confirm_json["drugWarnings"]
    assert len(warnings) >= 1
    detected_vias = {w["detectedVia"] for w in warnings}
    assert "VISUAL_GROUNDING" in detected_vias or "USER_PROFILE" in detected_vias

    # 6. Verify DB persistence and detail endpoint
    detail_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(first))
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["id"] == temp_meal_id
    assert detail["imageUrl"] == "https://storage.example.com/meals/confirmed.jpg"
    assert len(detail["foodItems"]) == 1
    assert detail["foodItems"][0]["foodName"] == "시금치나물"
    assert float(detail["foodItems"][0]["volumeCm3"]) == 150.0
    assert len(detail["drugWarnings"]) >= 1

    # 7. Verify ownership isolation (other user cannot access)
    other_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(other))
    assert other_res.status_code == 404


@pytest.mark.asyncio
async def test_manual_confirmation_failure_rolls_back(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock

    client, db, first, other, drug = environment
    item_id = str(uuid.uuid4())
    meal_id = str(uuid.uuid4())

    confirm_payload = {
        "mealId": meal_id,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "white_rice",
                "volumeCm3": 100.0,
            }
        ]
    }

    with patch("src.api.v1.endpoints.vision.AsyncSession.commit", new=AsyncMock(side_effect=SQLAlchemyError("atomic commit failure"))):
        res = await client.post(
            "/api/v1/vision/confirm",
            headers=auth(first),
            json=confirm_payload,
        )
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "ERR_DATABASE_UNAVAILABLE"

    # Verify no partial meal was saved in DB
    meals = (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"]
    assert all(m["id"] != meal_id for m in meals)


@pytest.mark.asyncio
async def test_registration_db_flow(environment):
    client, db, first, other, drug = environment
    new_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    raw_pw = "RegisterTestPassword123!"


    # 1. Successful registration
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": new_email, "password": raw_pw, "name": "신규등록자"},
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert reg_data["email"] == new_email
    assert reg_data["name"] == "신규등록자"
    assert reg_data["role"] == "USER"
    assert "id" in reg_data

    # 2. Login with newly registered user
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": new_email, "password": raw_pw},
    )
    assert login_res.status_code == 200, login_res.text
    assert "accessToken" in login_res.json()
    new_headers = {"Authorization": f"Bearer {login_res.json()['accessToken']}"}

    # 3. Meals list should be empty initially for new user
    meals_res = await client.get("/api/v1/meals", headers=new_headers)
    assert meals_res.status_code == 200
    assert meals_res.json()["data"]["totalCount"] == 0
    assert meals_res.json()["data"]["items"] == []

    # 4. Duplicate registration returns 409 Conflict
    dup_res = await client.post(
        "/api/v1/auth/register",
        json={"email": new_email, "password": raw_pw, "name": "중복등록자"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["detail"] == "이미 등록된 이메일 주소입니다."


@pytest.mark.asyncio
async def test_drug_interactions_db_flow(environment):
    client, db, first, other, drug = environment

    # 1. Unauthenticated request rejected with 401
    unauth_res = await client.get("/api/v1/drugs/interactions")
    assert unauth_res.status_code == 401

    # 2. Authenticated query returns populated interactions
    res = await client.get("/api/v1/drugs/interactions", headers=auth(first))
    assert res.status_code == 200, res.text
    rules = res.json()
    assert isinstance(rules, list)
    assert len(rules) >= 1

    # Verify rule structure
    rule = rules[0]
    assert "id" in rule
    assert "drugId" in rule
    assert "kdCode" in rule
    assert "brandName" in rule
    assert "ingredientName" in rule
    assert "triggerNutrient" in rule
    assert "riskLevel" in rule
    assert "mechanismDesc" in rule
    assert "actionGuide" in rule
    assert "sourceAuthority" in rule

    # 3. Filter by kdCode
    filtered = await client.get(f"/api/v1/drugs/interactions?kdCode={drug.kd_code}", headers=auth(first))
    assert filtered.status_code == 200
    filtered_rules = filtered.json()
    assert len(filtered_rules) >= 1
    assert all(r["kdCode"] == drug.kd_code for r in filtered_rules)


@pytest.mark.asyncio
async def test_analysis_persistence_with_is_calibrated_true(environment):
    client, db, first, other, drug = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=SimpleNamespace(process_image=lambda *args: analysis_result())):
        response = await client.post(
            '/api/v1/vision/estimate',
            headers=auth(first),
            files={'file': ('calibrated.png', image.getvalue(), 'image/png')},
            data={'is_calibrated': 'true', 'focal_length_mm': '35.0'},
        )
        assert response.status_code == 200, response.text
        data = response.json()['data']
        assert data['isCalibrated'] is True
        assert data['focalLengthMm'] == 35.0
        meal_id = data['mealId']

        # DB에 is_calibrated=True가 보존되었는지 검증
        db_meal = (await db.execute(select(Meal).where(Meal.id == uuid.UUID(meal_id)))).scalar_one()
        assert db_meal.is_calibrated is True
        assert db_meal.focal_length_mm == 35.0





@pytest.mark.asyncio
async def test_confirmation_weight_update_retry_ownership_and_rollback(environment):
    from unittest.mock import AsyncMock
    from sqlalchemy.exc import SQLAlchemyError
    client, db, first, other, drug = environment
    source = analysis_result()["foodItems"][0]
    nutrition = {**source, "interactionTags": []}
    service = SimpleNamespace(calculate=lambda food_id, volume: dict(nutrition))
    payload = {"mealId": str(uuid.uuid4()), "confirmedItems": [{
        "itemId": source["id"], "foodId": source["foodId"], "volumeCm3": 100, "weightG": 50,
    }]}
    with patch("src.api.v1.endpoints.vision.get_nutrition_service", return_value=service):
        saved = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()['data']['foodItems'][0]['weightG'] == 50
        assert saved.json()['data']['totalNutrition']['caloriesKcal'] == 50
        assert saved.json()['data']['foodItems'][0]['volumeCm3'] == 100
        payload['confirmedItems'][0]['weightG'] = 200
        updated = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert updated.status_code == 200, updated.text
        assert updated.json()['data']['totalNutrition']['caloriesKcal'] == 200
        retry = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert retry.status_code == 200, retry.text
        meals = (await client.get('/api/v1/meals', headers=auth(first))).json()['data']['items']
        assert len([m for m in meals if m['id'] == payload['mealId']]) == 1
        denied = await client.post('/api/v1/vision/confirm', headers=auth(other), json=payload)
        assert denied.status_code == 404
        payload['confirmedItems'][0]['weightG'] = 300
        with patch('src.api.v1.endpoints.vision.AsyncSession.commit', new=AsyncMock(side_effect=SQLAlchemyError('failure'))):
            failed = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert failed.status_code == 503
        detail = (await client.get('/api/v1/meals/' + payload['mealId'], headers=auth(first))).json()
        assert detail['totalCaloriesKcal'] == 200
        assert len(detail['foodItems']) == 1
        for weight in [0, -1, 'NaN', 'Infinity']:
            payload['confirmedItems'][0]['weightG'] = weight
            invalid = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
            assert invalid.status_code == 422
>>>>>>> REPLACE
```

## frontend/tests/vision-contract.cjs

```text
파일 경로: frontend/tests/vision-contract.cjs
<<<<<<< SEARCH
// Contract smoke test using the specification fixture; WebGL is stubbed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const fixture = require('./fixtures/vision-estimate.json');

function load(relativePath, overrides = {}, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
  }}).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports, require: name => overrides[name] ?? require(name), process,
    ...globals,
  });
  return exports;
}

function renderResult(result) {
  let stateIndex = 0;
  const effects = [];
  const boxes = [];
  const context = { drawImage() {}, fillRect() {}, fillText() {},
    strokeRect: (...args) => boxes.push(args) };
  const canvas = { getContext: () => context };
  const hooks = { ...React,
    useState: initial => [stateIndex++ === 3 ? result : initial, () => {}],
    useRef: () => ({ current: canvas }),
    useEffect: effect => effects.push(effect),
  };
  // Supply a preview URL so the overlay effect also runs.
  const useState = hooks.useState;
  hooks.useState = initial => stateIndex === 1
    ? (stateIndex++, ['blob:test', () => {}]) : useState(initial);
  const Page = load('src/app/page.tsx', {
    react: { ...hooks, useCallback: callback => callback }, 'next/dynamic': () => () => null,
    '../components/MealHistory': () => null,
    '../services/api': { getServiceStatus: async () => '분석 데이터 준비 필요' },
  }, { Image: class {
    naturalWidth = 640; naturalHeight = 480;
    set src(value) { this.onload?.(); }
  }}).default;
  const html = renderToStaticMarkup(React.createElement(Page));
  effects.forEach(effect => effect());
  return { html, boxes };
}

async function main() {
  const { html, boxes } = renderResult(fixture.data);
  assert.ok(html.includes('백미밥'));
  assert.ok(html.includes(fixture.data.drugWarnings[0].warningTitle));
  assert.ok(html.includes('320.5'));
  const bbox = fixture.data.foodItems[0].bbox2d;
  const expected = [bbox.xmin * 640, bbox.ymin * 480,
    (bbox.xmax - bbox.xmin) * 640, (bbox.ymax - bbox.ymin) * 480];
  boxes[0].forEach((value, index) => assert.ok(Math.abs(value - expected[index]) < 1e-8));
  const empty = renderResult({ ...fixture.data, foodItems: [], drugWarnings: [] });
  assert.ok(empty.html.includes('이번 분석에서 반환된 상호작용 경고가 없습니다.'));
  assert.equal(empty.boxes.length, 0);
  assert.ok(renderResult(null).html.includes('식단 이미지 업로드'));

  let request;
  const api = load('src/services/api.ts', {}, {
    FormData, AbortSignal,
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => fixture };
    },
  });
  const response = await api.estimateMealVision(new Blob(['test'], { type: 'image/jpeg' }));
  assert.equal(response.data.foodItems[0].foodName, '백미밥');
  assert.ok(request.url.endsWith('/api/v1/vision/estimate'));
  assert.equal(request.options.method, 'POST');
  assert.ok(request.options.body.has('file'));
  console.log('PASS: specification response, empty/initial states, 2D coordinates, API envelope');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
=======
// Contract smoke test using the specification fixture; WebGL is stubbed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const fixture = require('./fixtures/vision-estimate.json');

function load(relativePath, overrides = {}, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
  }}).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports, require: name => overrides[name] ?? require(name), process,
    ...globals,
  });
  return exports;
}

function renderResult(result) {
  let stateIndex = 0;
  const effects = [];
  const boxes = [];
  const context = { drawImage() {}, fillRect() {}, fillText() {},
    strokeRect: (...args) => boxes.push(args) };
  const canvas = { getContext: () => context };
  const hooks = { ...React,
    useState: initial => [stateIndex++ === 3 ? result : initial, () => {}],
    useRef: () => ({ current: canvas }),
    useEffect: effect => effects.push(effect),
  };
  // Supply a preview URL so the overlay effect also runs.
  const useState = hooks.useState;
  hooks.useState = initial => stateIndex === 1
    ? (stateIndex++, ['blob:test', () => {}]) : useState(initial);
  const Page = load('src/app/page.tsx', {
    react: { ...hooks, useCallback: callback => callback }, 'next/dynamic': () => () => null,
    '../components/MealHistory': () => null,
    '../services/api': { getServiceStatus: async () => '분석 데이터 준비 필요' },
  }, { Image: class {
    naturalWidth = 640; naturalHeight = 480;
    set src(value) { this.onload?.(); }
  }}).default;
  const html = renderToStaticMarkup(React.createElement(Page));
  effects.forEach(effect => effect());
  return { html, boxes };
}

async function main() {
  const { html, boxes } = renderResult(fixture.data);
  assert.ok(html.includes('백미밥'));
  assert.ok(html.includes(fixture.data.drugWarnings[0].warningTitle));
  assert.ok(html.includes('320.5'));
  const bbox = fixture.data.foodItems[0].bbox2d;
  const expected = [bbox.xmin * 640, bbox.ymin * 480,
    (bbox.xmax - bbox.xmin) * 640, (bbox.ymax - bbox.ymin) * 480];
  boxes[0].forEach((value, index) => assert.ok(Math.abs(value - expected[index]) < 1e-8));
  const empty = renderResult({ ...fixture.data, foodItems: [], drugWarnings: [] });
  assert.ok(empty.html.includes('이번 분석에서 반환된 상호작용 경고가 없습니다.'));
  assert.equal(empty.boxes.length, 0);
  assert.ok(renderResult(null).html.includes('식단 이미지 업로드'));

  let request;
  const api = load('src/services/api.ts', {}, {
    FormData, AbortSignal,
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => fixture };
    },
  });
  const response = await api.estimateMealVision(new Blob(['test'], { type: 'image/jpeg' }));
  assert.equal(response.data.foodItems[0].foodName, '백미밥');
  assert.ok(request.url.endsWith('/api/v1/vision/estimate'));
  assert.equal(request.options.method, 'POST');
  assert.ok(request.options.body.has('file'));
  const saved = await api.confirmMealVision({ ...fixture.data, foodItems: fixture.data.foodItems.map(item => ({ ...item, requiresConfirmation: false })) });
  assert.ok(request.url.endsWith('/vision/confirm'));
  assert.equal(JSON.parse(request.options.body).confirmedItems[0].weightG, fixture.data.foodItems[0].weightG);
  assert.equal(saved.isPersisted, true);
  assert.equal(saved.requiresConfirmation, false);
  for (const code of ['ERR_GEOMETRY_PLANE_NOT_FOUND', 'ERR_ZERO_OBJECT_DETECTED']) {
    const failing = load('src/services/api.ts', {}, { FormData, AbortSignal,
      fetch: async () => ({ ok: false, status: 422, json: async () => ({ error: { code, message: 'original' } }) }),
    });
    await assert.rejects(() => failing.estimateMealVision(new Blob(['test'])), /다시 촬영/);
  }
  console.log('PASS: specification response, empty/initial states, 2D coordinates, API envelope');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
>>>>>>> REPLACE
```

## backend/scripts/generate_frontend_types.py

```text
파일 경로: backend/scripts/generate_frontend_types.py
<<<<<<< SEARCH
"""Generate frontend vision DTOs from the backend Pydantic schema.

Run from backend: python scripts/generate_frontend_types.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.schemas.vision import MealEstimateResponse


def ts_type(field):
    if "$ref" in field:
        return field["$ref"].rsplit("/", 1)[-1]
    if field.get("type") == "array":
        return f"Array<{ts_type(field['items'])}>"
    return {"string": "string", "number": "number", "integer": "number", "boolean": "boolean"}[field["type"]]


def interface(name, schema):
    required = set(schema.get("required", []))
    fields = [f"  {key}{'' if key in required else '?'}: {ts_type(value)};" for key, value in schema["properties"].items()]
    return f"export interface {name} {{\n" + "\n".join(fields) + "\n}"


schema = MealEstimateResponse.model_json_schema()
blocks = ["// Generated from backend/src/schemas/vision.py. Do not edit manually."]
blocks.extend(interface(name, definition) for name, definition in schema.get("$defs", {}).items())
blocks.append(interface("MealEstimateResponse", schema))
target = Path(__file__).resolve().parents[2] / "frontend/src/types/vision.ts"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n\n".join(blocks) + "\n")
=======
"""Generate frontend vision DTOs from the backend Pydantic schema.

Run from backend: python scripts/generate_frontend_types.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.schemas.vision import MealEstimateResponse


def ts_type(field):
    if "anyOf" in field:
        return " | ".join(ts_type(option) for option in field["anyOf"])
    if field.get("type") == "null":
        return "null"
    if "$ref" in field:
        return field["$ref"].rsplit("/", 1)[-1]
    if field.get("type") == "array":
        return f"Array<{ts_type(field['items'])}>"
    return {"string": "string", "number": "number", "integer": "number", "boolean": "boolean"}[field["type"]]


def interface(name, schema):
    required = set(schema.get("required", []))
    fields = [f"  {key}{'' if key in required else '?'}: {ts_type(value)};" for key, value in schema["properties"].items()]
    return f"export interface {name} {{\n" + "\n".join(fields) + "\n}"


schema = MealEstimateResponse.model_json_schema()
blocks = ["// Generated from backend/src/schemas/vision.py. Do not edit manually."]
blocks.extend(interface(name, definition) for name, definition in schema.get("$defs", {}).items())
blocks.append(interface("MealEstimateResponse", schema))
target = Path(__file__).resolve().parents[2] / "frontend/src/types/vision.ts"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n\n".join(blocks) + "\n")
>>>>>>> REPLACE
```

## volumeal-align요구사항명세서/Volumeal Requirement.md

```text
파일 경로: volumeal-align요구사항명세서/Volumeal Requirement.md
<<<<<<< SEARCH
## **해커톤(AI Championship)**

# **Technical Specification: VoluMeal-Align \- Turn 1**

## **1\. System Overview**

### **1.1 프로젝트 목적 및 해결 과제**

* **수기 무게/인분수 입력 병목 및 2D 영양 오차 해결**: 2D 사진의 평면적 한계(깊이 정보 부재로 인한 30\~50%의 칼로리 오차)를 단안 메트릭 깊이 추정(Metric Depth Estimation)과 RANSAC 기반 3차원 기하학적 수치 적분으로 해결합니다.  
* **실시간 식단-복약 상호작용 충돌 방지**: 식탁 위에 놓인 처방약(알약, PTP 포장, 약봉투)과 음식 간의 대사 간섭 위험(와파린-비타민K, 스타틴-자몽, 갑상선 호르몬제-고칼슘)을 비전 임베딩과 식약처 금기 DB 기반 룰 엔진으로 감지하여 즉각적인 경고를 발출합니다.

### **1.2 핵심 기능 요약**

* **FR-001**: 단안 RGB 이미지 입력 시 Zero-shot Metric Depth 추정을 통한 절대 깊이 맵 생성  
* **FR-002**: 식판, 음식, 식기 및 복용 약제 인스턴스 세그멘테이션 마스크 추출  
* **FR-003**: 2D-to-3D 역투영 및 RANSAC 바닥면 피팅 기반 부피($V, \\text{cm}^3$) 수치 적분  
* **FR-004**: DINOv2 패치 임베딩 검색 기반 식품 밀도($\\rho$) 매핑 및 최종 무게/영양소(칼로리/탄단지) 산출  
* **FR-005**: 시각 접지(Visual Grounding) 및 식약처 DB 매핑 기반 약제-식품 위험 상호작용 판별  
* **FR-006**: Three.js 캔버스 기반 3D 바운딩 볼륨 및 다운샘플링 포인트 클라우드 실시간 렌더링  
* **FR-007**: 식단 영양소 분석 결과 및 복약 주의사항 리포트 저장 및 이력 조회
* **FR-008**: 식품 인식 불확실성에 대한 사용자 후보 확정 및 중량 보정

### **1.3 아키텍처 패턴 및 선정 이유**

* **선정 패턴**: **Decoupled Training & Inference with Modular Monolith**  
* **선정 이유**:  
  1. **물리적 환경 격리**: 랩실 RTX 5090 환경에서는 모델 학습 및 ONNX/TensorRT 파일 추출만 수행하고 즉시 세션을 종료하여, 학내 전산망 보안 이슈(외부 터널링 차단) 및 다른 연구원과의 자원 충돌을 방지합니다.  
  2. **독립 배포 경량화**: 추출된 가중치 모델을 ONNX Runtime CPU 멀티스레딩 최적화로 서빙하여, 고가의 상시 GPU 인프라 비용 없이 개인 노트북이나 저비용 클라우드에서도 400ms 내외의 준실시간 추론 속도를 확보합니다.

### **1.4 주요 시스템 구성요소 관계도 (Mermaid Component Diagram)**

코드 스니펫

graph TB

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Offline\_Training \[랩실 환경: Offline Training Machine \- RTX 5090\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TrainDataset\[(Nutrition5k & KFDA DB)\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Trainer\[Model Fine-tuner: Depth Anything v2 \+ DINOv2\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Exporter\[ONNX / TensorRT Exporter\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TrainDataset \--\> Trainer

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Trainer \--\> Exporter

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Exporter \--\>|가중치 파일 반출: model.onnx| ArtifactStorage\[Local / Cloud Model Storage\]

&nbsp;&nbsp;&nbsp;&nbsp;end


&nbsp;&nbsp;&nbsp;&nbsp;subgraph Client\_App \[프론트엔드: Next.js 14 App Router\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Viewfinder\[Camera Viewfinder & EXIF Parser\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ThreeViewer\[Three.js PointCloud & BBox Canvas\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ZustandStore\[Client State Store\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Serving\_Server \[독립 서빙 환경: FastAPI Backend \- CPU / Local / Cloud\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;APIRouter\[Async REST API Router\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator\[Vision Pipeline Orchestrator\]

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;subgraph Inference\_Engine \[ONNX Runtime CPU Engine\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DepthWorker\[Depth Anything v2 ONNX INT8/FP32\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SegWorker\[YOLOv8-Seg ONNX\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PatchWorker\[DINOv2 Feature Extractor\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;subgraph Geometry\_Core \[C++ / Python Vectorized Core\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BackProjector\[Camera Back-projection\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;RANSACPlane\[Open3D RANSAC Surface Fitter\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Integrator\[NumPy Double Numerical Integrator\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;RuleEngine\[KFDA Drug-Food Interaction Evaluator\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Data\_Persistence \[데이터베이스: PostgreSQL 15\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Postgres\[(PostgreSQL: Users, Meals, Drugs, Warnings)\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;ArtifactStorage \-.-\>|배포 시 가중치 로드| Inference\_Engine

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Viewfinder \--\>|1. Image Binary \+ EXIF| APIRouter

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\> PipelineOrchestrator

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> DepthWorker

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> SegWorker

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> PatchWorker

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;DepthWorker \--\> BackProjector

&nbsp;&nbsp;&nbsp;&nbsp;SegWorker \--\> BackProjector

&nbsp;&nbsp;&nbsp;&nbsp;BackProjector \--\> RANSACPlane

&nbsp;&nbsp;&nbsp;&nbsp;RANSACPlane \--\> Integrator

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;PatchWorker \--\> RuleEngine

&nbsp;&nbsp;&nbsp;&nbsp;Integrator \--\> RuleEngine

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;RuleEngine \--\> APIRouter

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\> Postgres

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\>|JSON \+ Downsampled PointCloud| ThreeViewer

&nbsp;

## **2\. Functional Requirements**

| ID | 기능명 | 설명 | 주요 동작 | 입력값 | 출력값 | 연관 API | 우선순위 |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **FR-001** | 단안 메트릭 깊이 맵 생성 | RGB 이미지 1장으로부터 픽셀별 물리적 절대 거리(m) 산출 | ONNX Runtime 기반 Depth Anything v2 Metric 추론 및 정규화 | `image/jpeg` 파일, 초점거리($f$) 메타데이터 | `Float32` Depth Matrix ($H \\times W$) | `POST /api/v1/vision/estimate` | P0 |
| **FR-002** | 인스턴스 세그멘테이션 | 음식, 식기, 약제(알약/약봉투) 영역 분할 마스크 추출 | YOLOv8-Seg ONNX 추론을 통한 바운딩 박스 및 픽셀 바이너리 마스크 생성 | 정규화된 이미지 텐서 ($1 \\times 3 \\times H \\times W$) | 인스턴스별 마스크, 클래스 라벨, 신뢰도 스코어 | `POST /api/v1/vision/estimate` | P0 |
| **FR-003** | RANSAC 기준면 분리 및 부피 적분 | 바닥 평면을 추정하고 음식 영역에 대한 높이 차분 수치 적분 수행 | 1\) 2D 픽셀을 3D 점군으로 역투영 |  |  |  |  |

2.   
   RANSAC 평면 피팅 ($ax+by+cz+d=0$)

3. 체적 수치 적분 ($V \= \\iint \\Delta z \\,dx\\,dy$) | Depth 맵, 인스턴스 마스크, 카메라 내부 매트릭스 $K$ | 객체별 체적 부피 ($V, \\text{cm}^3$), 오차 경계값 | `POST /api/v1/vision/estimate` | P0 |  
   &nbsp;| **FR-004** | 식품 매크로 영양소 및 중량 산출 | 라벨된 기준 음식 이미지 검색과 `foodId` 조인을 통한 최종 무게/영양소 계산 | 음식 크롭의 DINOv2 패치 벡터를 기준 이미지 임베딩과 코사인 비교 $\\to$ `foodId` 식별 $\\to$ 별도 밀도/영양 프로필 조회 $\\to$ $W \= V \\times \\rho$ 및 칼로리/탄단지 도출 | 음식 크롭 패치, 계산된 체적($V$) | `foodId`, Top-3 후보, 식품 표준명, 중량(g), 열량(kcal), 탄/단/지/나트륨 | `POST /api/v1/vision/estimate` | P0 |  
   &nbsp;| **FR-005** | 복약 시각 접지 및 간섭 위험 판정 | 식탁 위 감지된 약제 또는 등록 처방약과 식단 영양소 간의 대사 충돌 평가 | 1\) 약제 검출 및 식약처 EDI 코드 매칭

4. 상호작용 금기 룰 조회

5. 위험 등급 산출 | 식별된 약제명, 식단 영양소/원재료 리스트 | 위험 등급(DANGER/CAUTION/SAFE), 유발 성분, 권고문 | `POST /api/v1/vision/estimate`, `GET /api/v1/drugs/interactions` | P0 |  
   &nbsp;| **FR-006** | 3D 시각화 페이로드 전송 | 클라이언트 WebGL 렌더링용 경량 포인트 클라우드 및 와이어프레임 생성 | 마스크 내부 점군 Voxel Grid 다운샘플링 (최대 5,000점) 및 바운딩 박스 정점 8개 연산 | 3D 포인트 클라우드 원본 데이터 | `positions` (Float32Array), 3D 바운딩 박스 좌표 | `POST /api/v1/vision/estimate` | P1 |  
   &nbsp;| **FR-007** | 식단 리포트 저장 및 이력 조회 | 분석된 식단, 영양소 총합, 복약 위험 로그 저장 및 기간별 통계 조회 | PostgreSQL 트랜잭션 적재 및 사용자별 날짜 범위 쿼리 | 사용자 인증 토큰, 분석 DTO, 기간 조회 조건 | 일자별 섭취 칼로리 총합, 복약 충돌 이력 리스트 | `GET /api/v1/meals`, `GET /api/v1/meals/{id}` | P1 |

**FR-008 상세**: 자동 분류가 불확실하거나 새로운 음식일 때 클라이언트는 `requiresConfirmation=true`와 함께 반환된 Top-3 후보를 버튼으로 표시한다. 사용자가 후보를 선택하면 해당 후보의 밀도와 영양값으로 음식 결과와 총합을 갱신한다. 사용자가 중량(g)을 수정하면 `수정 중량 / 기존 중량` 비율로 칼로리·탄수화물·단백질·지방·나트륨을 즉시 재계산한다. 이 보정값은 서버 확정 저장 전까지 클라이언트 임시 상태다.

### **예외 처리 및 유효성 검증 규칙**

1. **\[BR-VAL-001\] 카메라 초점거리(EXIF) 부재 대응**: 클라이언트 이미지에 EXIF 초점거리 메타데이터가 존재하지 않을 경우, 모바일 표준 광각 기준값($f \= 26.0\\text{mm}$)을 기본값으로 강제 주입하며 `is_calibrated: false` 플래그를 응답에 기록합니다.  
2. **\[BR-VAL-002\] 바닥 평면 추정 실패 (RANSAC Outlier 초과)**: 그릇의 테두리 및 테이블 면의 RANSAC 인라이어(Inlier) 비율이 전체의 40% 미만일 경우 `ERR_GEOMETRY_PLANE_NOT_FOUND` 예외를 발생시키고, 클라이언트는 표준 1인분으로 임의 대체하지 않고 재촬영 안내를 제공합니다.  
3. **\[BR-VAL-003\] 최소 체적 유효 범위 제한**: 수치 적분된 부피가 $V \\le 5\\,\\text{cm}^3$ 미만이거나 $V \\ge 5000\\,\\text{cm}^3$ 초과일 경우 노이즈로 판정하고 `ERR_VOLUME_OUT_OF_BOUNDS`를 반환합니다.

4. **[BR-VAL-004] 음식 미검출 대응**: `ERR_ZERO_OBJECT_DETECTED`가 발생하면 클라이언트는 일반 서버 오류 대신 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영하라는 안내를 표시합니다.
5. **[BR-VAL-005] 사용자 중량 보정**: 사용자가 중량을 수정하면 0보다 큰 유한값만 허용하고, 선택된 음식의 기존 영양값에 `수정 중량 / 기존 중량`을 곱해 화면의 음식 영양값과 총합을 즉시 갱신합니다. 이 보정값은 서버 확정 저장 전까지 임시 클라이언트 상태입니다.

## **3\. Non-Functional Requirements**

### **3.1 성능 (Performance)**

* **학습 파이프라인 (랩실 RTX 5090\)**: Depth Anything v2 `vits` 모델의 경량 어댑터 파인튜닝은 32GB VRAM 및 BF16 Tensor Core 가속을 통해 **1.5시간 이내 완료**.  
* **추론 지연 시간 (배포 서빙 환경)**: 4코어 CPU ONNX Runtime 환경 기준, 이미지 수신부터 3D 기하 연산 및 JSON 응답 반환까지 **단일 이미지 450ms 이내 완결** (로컬 노트북 구동 시 350ms).  
* **클라이언트 3D 렌더링**: Next.js Three.js 캔버스에서 Voxel 다운샘플링된 포인트 클라우드(3,000\~5,000점) 렌더링 시 **60 FPS** 유지.

### **3.2 보안 (Security)**

* **랩실 전산망 완전 격리**: 서빙 서버는 랩실 GPU와 완전히 분리되어 작동하며, 학내 네트워크 외부 터널링(ngrok, cloudflared)을 일절 수행하지 않음.  
* **이미지 메모리 생명주기**: 업로드된 바이너리는 디스크에 영구 적재하지 않고 메모리 버퍼(`io.BytesIO`)에서 NumPy 배열 변환 후 즉시 메모리 할당을 해제.  
* **데이터 무결성 및 암호화**: 사용자 복약 데이터는 AES-256-GCM 컬럼 암호화 적용, JWT 토큰은 `HttpOnly`, `SameSite=Strict` 쿠키로 전송.

### **3.3 안정성 및 가용성 (Reliability & Availability)**

* **추론 동시성 제어**: 배포 서버의 CPU/메모리 고갈 방지를 위해 백엔드에 세마포어(`asyncio.Semaphore(5)`)를 설정하여 동시 처리 요청 수를 5건으로 제한.  
* **트랜잭션 격리 수준**: 식단 분석 결과 및 복약 경고 로그 저장은 PostgreSQL `READ COMMITTED` 수준에서 원자적 처리.

### **3.4 반응형 규격 및 웹 접근성 (Usability & Accessibility)**

* **모바일 뷰포트 최적화**: 360px \~ 430px 폭의 모바일 화면(스마트폰 촬영 뷰파인더) 완전 반응형 지원.  
* **WebGL Graceful Fallback**: 하드웨어 가속이 불가능한 기기 접속 시 3D Canvas 대신 2D 정적 바운딩 박스 오버레이로 자동 전환.

## **4\. Tech Stack & Dependencies**

| 영역 | 기술 스택 | 버전 | 목적 | 선택 근거 |
| ----- | ----- | ----- | ----- | ----- |
| **Model Training** | PyTorch / CUDA | 2.3+ / 12.8+ | 랩실 RTX 5090 기반 모델 파인튜닝 | Blackwell 아키텍처 지원, 32GB VRAM을 통한 초고속 BF16 학습 |
| **Model Export** | ONNX / ONNX Runtime | 1.16+ / 1.18+ | 딥러닝 모델 직렬화 및 CPU 최적화 추론 | GPU 의존성을 제거하고 노트북/서버 CPU에서 400ms대 추론 달성 |
| **3D & Geometry** | Open3D / NumPy / SciPy | 0.18+ / 1.26+ | 점군 처리, RANSAC 평면 피팅, 수치 적분 | C++ 바인딩을 통한 고속 벡터화 체적 계산 파이프라인 구축 |
| **Backend Core** | FastAPI / Uvicorn | 0.111+ / 0.30+ | 비동기 고성능 REST API 서빙 | Async IO 네이티브 지원, Pydantic v2 고속 직렬화 |
| **Database & ORM** | PostgreSQL / SQLAlchemy | 15-alpine / 2.0+ (Async) | 영속 데이터 저장 및 비동기 ORM | 정형 데이터 무결성 보장, JSONB를 통한 점군/BBox 유연성 확보 |
| **DB Migration** | Alembic | 1.13+ | 데이터베이스 스키마 버전 관리 | 재현 가능한 데이터베이스 마이그레이션 자동화 |
| **Frontend Core** | Next.js (App Router) | 14.2+ | 클라이언트 웹 앱 및 라우팅 | React Server Components, 카메라 및 대시보드 생산성 극대화 |
| **Language (FE)** | TypeScript | 5.4+ | 정적 타입 계약 보장 | 백엔드 API 계약(Contract)과의 무결성 보장 및 런타임 에러 방지 |
| **3D Rendering** | Three.js / @react-three/fiber | 0.164+ / 8.16+ | 3D 점군, 와이어프레임, 평면 시각화 | WebGL 추상화를 통한 리액트 선언적 3D 뷰어 개발 |
| **State / Fetching** | Zustand / TanStack Query | 4.5+ / 5.35+ | 클라이언트 전역 상태 및 비동기 캐싱 | 가벼운 상태 관리와 API 요청 라이프사이클 분리 |
| **Container & Deploy** | Docker / Docker Compose | 26+ / 2.27+ | 배포 컨테이너라이징 | 로컬 노트북 및 독립 클라우드 어디서든 동일한 실행 환경 보장 |

## **5\. System Architecture**

### **5.1 논리적 컴포넌트 구조**

시스템은 오프라인 학습 영역과 독립 서빙 영역으로 완전히 분리됩니다.

1. **Offline Training & Export Module (랩실 환경)**:  
   * Nutrition5k 데이터셋 기반 Depth Anything v2 Metric 스케일러 파인튜닝  
   * `torch.onnx.export`를 통해 CPU 연산 최적화된 단일 `.onnx` 파일 생성 및 반출  
2. **Serving Application Layer (FastAPI Backend)**:  
   * 파일 유효성 검사 $\\to$ ONNX Runtime CPU 세션 추론 $\\to$ Open3D/NumPy 기하 연산 $\\to$ 식약처 룰 엔진 평가 $\\to$ DB 저장  
3. **Interactive Client Layer (Next.js Frontend)**:  
   * 모바일 카메라 뷰파인더 캡처 $\\to$ EXIF 초점거리 추출 $\\to$ API 통신 $\\to$ Three.js 3D 점군 및 영양 리포트 동시 렌더링

### **5.2 Request-Response 처리 라이프사이클**

\[Client\] 이미지 촬영/업로드 (multipart/form-data)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[FastAPI: POST /api/v1/vision/estimate\]

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;├── 1\. Request Validator: 매직 넘버 검증 (JPEG/PNG), 파일 크기 제한 (10MB)

&nbsp;&nbsp;&nbsp;├── 2\. Image Preprocessing: OpenCV 인메모리 리사이징 (518x518)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[ONNX Runtime CPU Inference Worker\]

&nbsp;&nbsp;&nbsp;├── Task A: Depth Anything v2 ONNX \-\> Float32 Metric Depth Map (m)

&nbsp;&nbsp;&nbsp;└── Task B: YOLOv8-Seg ONNX \-\> Food & Drug Instance Masks

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Geometry Integration Engine (NumPy & Open3D)\]

&nbsp;&nbsp;&nbsp;├── 1\. Back-projection: 2D (u, v, d) \-\> 3D (X, Y, Z) via Camera Matrix K

&nbsp;&nbsp;&nbsp;├── 2\. Plane Segmentation: Table Surface RANSAC (Inliers Distance: 0.01m)

&nbsp;&nbsp;&nbsp;├── 3\. Double Numerical Integration: V \= ∬ (z\_table \- z\_food) dx dy over mask Ω

&nbsp;&nbsp;&nbsp;└── 4\. Downsampling: Voxel Grid Filter (Leaf size: 0.005m)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Nutrient & Drug Matching Service\]

&nbsp;&nbsp;&nbsp;├── 1\. DINOv2 Feature Cosine Search against Labeled Food Images \-\> foodId

&nbsp;&nbsp;&nbsp;├── 2\. foodId \-\> Density/Nutrient Profiles \-\> W \= V \* ρ \-\> Compute Calories, Carbs, Protein, Fat

&nbsp;&nbsp;&nbsp;└── 3\. Drug Interaction Engine: Drug vs Food Nutrients check against KFDA rules

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Response & Storage\]

&nbsp;&nbsp;&nbsp;├── 1\. Asynchronously insert records into PostgreSQL (meals, drug\_warnings)

&nbsp;&nbsp;&nbsp;└── 2\. Return Unified JSON: Bounding Boxes, 3D Points, Nutrition, Drug Warnings

&nbsp;

### **5.3 End-to-End 데이터 흐름도 (Mermaid Sequence Diagram)**

코드 스니펫

sequenceDiagram

&nbsp;&nbsp;&nbsp;&nbsp;autonumber

&nbsp;&nbsp;&nbsp;&nbsp;actor User as 사용자 (모바일 브라우저)

&nbsp;&nbsp;&nbsp;&nbsp;participant Client as Next.js 14 Frontend

&nbsp;&nbsp;&nbsp;&nbsp;participant API as FastAPI Serving Engine

&nbsp;&nbsp;&nbsp;&nbsp;participant ONNX as ONNX Runtime (CPU)

&nbsp;&nbsp;&nbsp;&nbsp;participant Geo as Geometry Integrator

&nbsp;&nbsp;&nbsp;&nbsp;participant Rule as Drug-Food Rule Engine

&nbsp;&nbsp;&nbsp;&nbsp;participant DB as PostgreSQL 15

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over User, Client: \[카메라 촬영 및 메타데이터 파싱\]

&nbsp;&nbsp;&nbsp;&nbsp;User-\>\>Client: 음식 및 약제 사진 촬영

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: EXIF 초점거리 파싱 (focal\_length \= 26mm)

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>API: POST /api/v1/vision/estimate (Multipart File \+ Metadata)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate API

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>API: 이미지 매직 넘버 및 포맷 유효성 검증

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate ONNX

&nbsp;&nbsp;&nbsp;&nbsp;par 모델 추론 (ONNX Runtime CPU)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>ONNX: Run Depth Model (Image Tensor)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ONNX--\>\>API: Metric Depth Map (Float32)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>ONNX: Run YOLOv8-Seg (Image Tensor)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ONNX--\>\>API: Instance Masks & BBoxes

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;&nbsp;&nbsp;&nbsp;deactivate ONNX

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate Geo

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>Geo: 3D 기하 연산 요청 (Depth, Masks, K Matrix)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: 3D 점군 역투영 (Back-projection)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: RANSAC 기반 테이블 바닥 평면 분리

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: 음식 마스크 영역 체적 수치 적분 (V cm³)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: Three.js용 Voxel Grid 다운샘플링 점군 생성

&nbsp;&nbsp;&nbsp;&nbsp;Geo--\>\>API: Volume(cm³), 3D BBox, 다운샘플링 점군

&nbsp;&nbsp;&nbsp;&nbsp;deactivate Geo

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate Rule

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>Rule: 영양소 계산 및 복약 상호작용 검증

&nbsp;&nbsp;&nbsp;&nbsp;Rule-\>\>Rule: 라벨된 기준 이미지 검색으로 foodId 식별 후 밀도(ρ) 및 중량(W=V\*ρ) 도출

&nbsp;&nbsp;&nbsp;&nbsp;Rule-\>\>Rule: 식약처 금기 DB 대조 (와파린-비타민K 등 간섭 판정)

&nbsp;&nbsp;&nbsp;&nbsp;Rule--\>\>API: 영양 프로필 및 위험 경고 리스트

&nbsp;&nbsp;&nbsp;&nbsp;deactivate Rule

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>DB: INSERT meal\_records, meal\_drug\_warnings

&nbsp;&nbsp;&nbsp;&nbsp;API--\>\>Client: 200 OK (MealEstimateResponse JSON)

&nbsp;&nbsp;&nbsp;&nbsp;deactivate API

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: Zustand 스토어 업데이트

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: Three.js 캔버스에 3D 점군 및 와이어프레임 렌더링

&nbsp;&nbsp;&nbsp;&nbsp;Client--\>\>User: 칼로리 수치 및 복약 위험 경고 배너 표출

&nbsp;

## **6\. Directory Structure**

프로젝트는 랩실 오프라인 학습 스크립트(`training/`), 독립 배포용 백엔드(`backend/`), 프론트엔드(`frontend/`)의 모노레포 구조로 명확히 분리됩니다.

volumeal-align/

├── .cursorrules                               \# AI 에이전트 개발 표준 룰셋

├── docker-compose.yml                         \# 로컬/서버 배포 오케스트레이션 (DB, Backend, Frontend)

├── README.md

│

├── training/                                  \# \[랩실 RTX 5090 전용\] 모델 학습 및 Export

│   ├── requirements\_train.txt                 \# PyTorch, CUDA 12.8+, Transformers

│   ├── train\_depth\_metric.py                  \# Depth Anything v2 Metric 미세조정 스크립트

│   ├── export\_onnx.py                         \# 학습 완료 후 CPU 최적화 ONNX 모델 추출 스크립트

│   └── data/

│       └── download\_nutrition5k.sh            \# 훈련용 공개 데이터셋 다운로더

│

├── backend/                                   \# \[독립 서빙 환경\] FastAPI Backend

│   ├── Dockerfile                             \# CPU ONNX 최적화 런타임 이미지

│   ├── requirements.txt                       \# fastapi, onnxruntime, open3d, sqlalchemy

│   ├── alembic.ini

│   ├── migrations/                            \# Alembic DB 마이그레이션

│   │   └── env.py

│   └── app/

│       ├── main.py                            \# FastAPI 진입점 및 미들웨어

│       ├── core/

│       │   ├── config.py                      \# Pydantic BaseSettings 환경설정

│       │   ├── database.py                    \# 비동기 SQLAlchemy 세션 설정

│       │   └── exceptions.py                  \# 커스텀 비즈니스 예외 클래스

│       ├── models/                            \# SQLAlchemy 2.0 ORM 엔티티

│       │   ├── user.py                        \# 사용자 엔티티

│       │   ├── meal.py                        \# 식단 분석 마스터 \[FR-007\]

│       │   ├── food\_item.py                   \# 개별 음식 분석 상세 (부피, 중량, 영양) \[FR-003, FR-004\]

│       │   ├── drug.py                        \# 식약처 약제 마스터 \[FR-005\]

│       │   └── interaction\_log.py             \# 복약 위험 감지 이력 \[FR-005\]

│       ├── schemas/                           \# Pydantic v2 DTO

│       │   ├── vision.py                      \# 추론 요청/응답 스키마 \[FR-001\~FR-006\]

│       │   ├── meal.py                        \# 식단 이력 조회 스키마 \[FR-007\]

│       │   └── drug.py                        \# 복약 및 상호작용 스키마 \[FR-005\]

│       ├── api/v1/

│       │   ├── router.py                      \# v1 라우터 통합

│       │   ├── deps.py                        \# 인증 및 세션 의존성 주입

│       │   └── endpoints/

│       │       ├── vision.py                  \# POST /vision/estimate \[FR-001\~FR-006\]

│       │       ├── meals.py                   \# GET /meals, GET /meals/{id} \[FR-007\]

│       │       └── drugs.py                   \# GET /drugs/interactions \[FR-005\]

│       ├── services/                          \# 비즈니스 오케스트레이션 레이어

│       │   ├── vision\_pipeline.py             \# 비전 추론 파이프라인 총괄

│       │   ├── meal\_service.py                \# 식단 데이터 저장 및 통계 연산 \[FR-007\]

│       │   └── drug\_interaction\_service.py    \# 식약처 금기 룰 매칭 \[FR-005\]

│       ├── ml/                                \# 런타임 추론 및 기하 알고리즘

│       │   ├── weights/                       \# 랩실에서 반출된 ONNX 가중치 저장 폴더

│       │   │   ├── depth\_anything\_v2\_vits.onnx

│       │   │   └── yolov8s\_seg.onnx

│       │   ├── onnx\_depth\_estimator.py        \# ONNX Runtime CPU 깊이 추론기 \[FR-001\]

│       │   ├── onnx\_segmentor.py              \# ONNX Runtime 세그멘테이션 추론기 \[FR-002\]

│       │   ├── geometry\_integrator.py         \# Open3D RANSAC 및 수치 적분기 \[FR-003\]

│       │   ├── patch\_embedder.py              \# DINOv2 패치 특징 추출기 \[FR-004\]

│       │   └── camera\_utils.py                \# 역투영 및 내부 파라미터 행렬 계산 \[FR-003\]

│       └── data/

│           ├── food\_density\_table.json        \# 식품별 밀도 및 영양성분 DB \[FR-004\]

│           └── drug\_interactions.json         \# 식약처 의약품-음식 상호작용 규칙 \[FR-005\]

│

└── frontend/                                  \# \[웹 클라이언트\] Next.js 14 App Router

&nbsp;&nbsp;&nbsp;&nbsp;├── package.json

&nbsp;&nbsp;&nbsp;&nbsp;├── tsconfig.json

&nbsp;&nbsp;&nbsp;&nbsp;├── tailwind.config.ts

&nbsp;&nbsp;&nbsp;&nbsp;└── src/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── app/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── layout.tsx                     \# 전역 레이아웃

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── page.tsx                       \# 메인 카메라 촬영/업로드 \[FR-001\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── dashboard/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│       └── page.tsx                   \# 일자별 영양/복약 대시보드 \[FR-007\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── components/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── camera/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── Viewfinder.tsx             \# 실시간 웹캠 캡처 및 오버레이

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── ExifExtractor.ts           \# 초점거리 추출 유틸리티 \[FR-001\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── viewer3d/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── CanvasContainer.tsx        \# Three.js Canvas 래퍼 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── PointCloudViewer.tsx       \# 점군 렌더링 컴포넌트 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── BoundingVolumeMesh.tsx     \# 3D 와이어프레임 렌더러 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── report/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── NutritionSummary.tsx       \# 칼로리/매크로 영양소 카드 \[FR-004\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── DrugWarningBanner.tsx      \# 복약 위험 경고 알림 \[FR-005\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── ui/                            \# 공통 UI 컴포넌트 (버튼, 모달)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── hooks/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── useEstimateMeal.ts             \# React Query 기반 분석 요청 훅

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── stores/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── useMealStore.ts                \# 분석 결과 및 3D 뷰포트 상태 관리

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── types/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── api.ts                         \# 백엔드 공유 타입 인터페이스

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── lib/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── apiClient.ts                   \# Axios API 클라이언트 인스턴스

&nbsp;

# **Technical Specification: VoluMeal-Align \- Turn 2**

## **7\. Database Schema & Seed Data**

### **7.1 스키마 정의 테이블**

#### **7.1.1 `users`**

시스템 접근 사용자 계정 및 권한 관리 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 사용자 고유 식별자 |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | None | `BTREE (email)` | 로그인 이메일 계정 |
| `hashed_password` | `VARCHAR(255)` | `NOT NULL` | None | None | Bcrypt 알고리즘 암호화 해시 |
| `name` | `VARCHAR(100)` | `NOT NULL` | None | None | 사용자 성명 또는 식별 닉네임 |
| `role` | `VARCHAR(20)` | `NOT NULL` | `'USER'` | None | RBAC 역할 (`'USER'`, `'ADMIN'`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 계정 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 계정 정보 변경 일시 |

#### **7.1.2 `drugs` \[FR-005\]**

식품의약품안전처 표준 의약품 마스터 데이터 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 의약품 고유 식별자 |
| `kd_code` | `VARCHAR(50)` | `NOT NULL`, `UNIQUE` | None | `BTREE (kd_code)` | 식약처 의약품 표준코드 (EDI) |
| `brand_name` | `VARCHAR(255)` | `NOT NULL` | None | `BTREE (brand_name)` | 공식 제품명 (예: 쿠마딘정 5mg) |
| `ingredient_name` | `VARCHAR(255)` | `NOT NULL` | None | `BTREE (ingredient_name)` | 의약품 주성분명 (예: Warfarin Sodium) |
| `therapeutic_class` | `VARCHAR(100)` | `NOT NULL` | None | None | 약효 분류군 (예: 항응고제) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.3 `user_medications` \[FR-005\]**

사용자가 프로필에 상시 등록하여 복용 중인 처방약 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 복약 등록 고유 식별자 |
| `user_id` | `UUID` | `NOT NULL`, `REFERENCES users(id) ON DELETE CASCADE` | None | `BTREE (user_id)` | 대상 사용자 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE RESTRICT` | None | `BTREE (drug_id)` | 등록 약제 마스터 식별자 |
| `prescribed_dosage_mg` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 1회 처방 복용량 (mg) |
| `is_active` | `BOOLEAN` | `NOT NULL` | `TRUE` | None | 현재 복약 유지 여부 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.4 `drug_food_contraindications` \[FR-005\]**

약제 성분과 식품 영양소/원재료 간의 약리학적 대사 간섭 및 금기 규칙 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 금기 규칙 고유 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE CASCADE` | None | `BTREE (drug_id)` | 연관 약제 식별자 |
| `trigger_nutrient` | `VARCHAR(100)` | `NOT NULL` | None | `BTREE (trigger_nutrient)` | 간섭 유발 성분/식품 (예: `Vitamin_K`, `Grapefruit`) |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | `'CAUTION'` | None | 위험 등급 (`'DANGER'`, `'CAUTION'`, `'INFO'`) |
| `mechanism_desc` | `TEXT` | `NOT NULL` | None | None | 생화학적 대사 간섭 기전 |
| `action_guide` | `TEXT` | `NOT NULL` | None | None | 환자 행동 지침 (예: 섭취 금지, 시간 격차 유지) |
| `source_authority` | `VARCHAR(100)` | `NOT NULL` | `'KFDA'` | None | 근거 데이터 출처 기관 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.5 `meals` \[FR-001, FR-007\]**

단일 식단 촬영 이벤트 및 총 영양소 집계 마스터 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 식단 분석 고유 식별자 |
| `user_id` | `UUID` | `NOT NULL`, `REFERENCES users(id) ON DELETE CASCADE` | None | `BTREE (user_id)` | 분석 소유 사용자 식별자 |
| `image_url` | `VARCHAR(1024)` | `NOT NULL` | None | None | 분석 대상 이미지 스토리지 경로 |
| `focal_length_mm` | `NUMERIC(6,2)` | `NOT NULL` | `26.00` | None | 역투영에 사용된 카메라 초점거리 |
| `is_calibrated` | `BOOLEAN` | `NOT NULL` | `FALSE` | None | EXIF 메타데이터 기반 캘리브레이션 여부 |
| `total_calories_kcal` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 음식 합산 열량 (kcal) |
| `total_carbs_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 탄수화물 합계 (g) |
| `total_protein_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 단백질 합계 (g) |
| `total_fat_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 지방 합계 (g) |
| `total_sodium_mg` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 나트륨 합계 (mg) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | `BTREE (created_at)` | 식단 촬영 및 분석 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.6 `meal_food_items` \[FR-002, FR-003, FR-004\]**

단일 식단 내 분할 검출된 개별 음식 객체, 산출 체적($V$), 밀도($\\rho$), 영양소 상세 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 개별 음식 객체 식별자 |
| `meal_id` | `UUID` | `NOT NULL`, `REFERENCES meals(id) ON DELETE CASCADE` | None | `BTREE (meal_id)` | 연관 식단 마스터 식별자 |
| `food_name` | `VARCHAR(100)` | `NOT NULL` | None | None | 매핑된 표준 식품명 |
| `confidence_score` | `NUMERIC(4,3)` | `NOT NULL` | None | None | DINOv2 임베딩 검색 신뢰도 |
| `volume_cm3` | `NUMERIC(8,2)` | `NOT NULL` | None | None | RANSAC 수치 적분 부피 ($V$) |
| `density_g_cm3` | `NUMERIC(5,4)` | `NOT NULL` | None | None | 적용된 부피 밀도 ($\\rho$) |
| `weight_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 최종 연산 무게 ($W \= V \\times \\rho$) |
| `calories_kcal` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 열량 (kcal) |
| `carbs_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 탄수화물 (g) |
| `protein_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 단백질 (g) |
| `fat_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 지방 (g) |
| `sodium_mg` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 나트륨 (mg) |
| `bbox_2d` | `JSONB` | `NOT NULL` | None | None | 2D 경계 박스 좌표 `[ymin, xmin, ymax, xmax]` |
| `bbox_3d` | `JSONB` | `NOT NULL` | None | None | 3D 바운딩 볼륨 중심, 치수, 8개 정점 좌표 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.7 `meal_drug_warnings` \[FR-005\]**

식단 분석 중 도출된 약제-식품 간섭 위험 경고 발출 로그 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 경고 로그 식별자 |
| `meal_id` | `UUID` | `NOT NULL`, `REFERENCES meals(id) ON DELETE CASCADE` | None | `BTREE (meal_id)` | 연관 식단 마스터 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE CASCADE` | None | None | 충돌 발생 약제 식별자 |
| `food_item_id` | `UUID` | `NULLABLE`, `REFERENCES meal_food_items(id) ON DELETE SET NULL` | None | None | 원인 제공 음식 객체 식별자 |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | None | None | 위험 등급 (`'DANGER'`, `'CAUTION'`, `'INFO'`) |
| `detected_via` | `VARCHAR(30)` | `NOT NULL` | `'VISUAL_GROUNDING'` | None | 식별 경로 (`VISUAL_GROUNDING`, `USER_PROFILE`) |
| `warning_title` | `VARCHAR(255)` | `NOT NULL` | None | None | UI 렌더링용 경고 요약 제목 |
| `warning_message` | `TEXT` | `NOT NULL` | None | None | 의학적 간섭 설명 및 조치 가이드 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

### **7.2 Entity-Relationship Diagram (Mermaid ERD)**

코드 스니펫

erDiagram

&nbsp;&nbsp;&nbsp;&nbsp;users ||--o{ user\_medications : "registers"

&nbsp;&nbsp;&nbsp;&nbsp;users ||--o{ meals : "records"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ user\_medications : "defined\_in"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ drug\_food\_contraindications : "has\_rules"

&nbsp;&nbsp;&nbsp;&nbsp;meals ||--|{ meal\_food\_items : "contains"

&nbsp;&nbsp;&nbsp;&nbsp;meals ||--o{ meal\_drug\_warnings : "triggers"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ meal\_drug\_warnings : "involved\_in"

&nbsp;&nbsp;&nbsp;&nbsp;meal\_food\_items ||--o{ meal\_drug\_warnings : "causes"

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;users {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR email UK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR hashed\_password

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR role

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;drugs {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR kd\_code UK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR brand\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR ingredient\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR therapeutic\_class

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;user\_medications {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID user\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC prescribed\_dosage\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BOOLEAN is\_active

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;drug\_food\_contraindications {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR trigger\_nutrient

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR risk\_level

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT mechanism\_desc

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT action\_guide

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR source\_authority

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meals {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID user\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR image\_url

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC focal\_length\_mm

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BOOLEAN is\_calibrated

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_calories\_kcal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_carbs\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_protein\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_fat\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_sodium\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meal\_food\_items {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID meal\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR food\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC confidence\_score

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC volume\_cm3

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC density\_g\_cm3

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC weight\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC calories\_kcal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC carbs\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC protein\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC fat\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC sodium\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JSONB bbox\_2d

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JSONB bbox\_3d

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meal\_drug\_warnings {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID meal\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID food\_item\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR risk\_level

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR detected\_via

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR warning\_title

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT warning\_message

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

### **7.3 Local Verification Seed Data**

로컬 개발 환경 검증 및 테스트 통과를 위한 표준 마스터 데이터셋 SQL 스크립트입니다. (`backend/app/data/seed.sql`)

SQL

\-- 1\. 기본 테스트 계정 생성 (비밀번호: Password123\! \-\> bcrypt 해시)

INSERT INTO users (id, email, hashed\_password, name, role, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('a0000000-0000-0000-0000-000000000001', 'admin@volumeal.io', '$2b$12$e0M2/qj9h2Y4F5tN2qG6h.W91d4e0e5j8r8z6k4s9v2w1x3y4z5a6', '최고관리자', 'ADMIN', NOW(), NOW()),

&nbsp;&nbsp;('a0000000-0000-0000-0000-000000000002', 'tester@volumeal.io', '$2b$12$e0M2/qj9h2Y4F5tN2qG6h.W91d4e0e5j8r8z6k4s9v2w1x3y4z5a6', '일반테스터', 'USER', NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 2\. 표준 약제 마스터 데이터 등록 \[FR-005\]

INSERT INTO drugs (id, kd\_code, brand\_name, ingredient\_name, therapeutic\_class, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000001', '641800240', '쿠마딘정5밀리그람', '와파린나트륨 (Warfarin Sodium)', '항응고제', NOW(), NOW()),

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000002', '644900110', '리피토정20밀리그람', '아토르바스타틴칼슘삼수화물 (Atorvastatin)', '고지혈증치료제', NOW(), NOW()),

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000003', '642102550', '씬지로이드정0.1밀리그람', '레보티록신나트륨 (Levothyroxine)', '갑상선호르몬제', NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 3\. 약제-식품 상호작용 위험 매트릭스 등록 \[FR-005\]

INSERT INTO drug\_food\_contraindications (id, drug\_id, trigger\_nutrient, risk\_level, mechanism\_desc, action\_guide, source\_authority, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000001',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000001',

&nbsp;&nbsp;&nbsp;&nbsp;'Vitamin\_K',

&nbsp;&nbsp;&nbsp;&nbsp;'DANGER',

&nbsp;&nbsp;&nbsp;&nbsp;'비타민 K는 간에서 혈액 응고 인자의 생합성을 촉진하여 와파린의 프로트롬빈 시간 연장 작용을 직접적으로 길항 및 저해합니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'시금치, 케일, 브로콜리 등 비타민 K가 다량 함유된 녹색 채소류의 과다 섭취를 엄격히 제한하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;),

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000002',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000002',

&nbsp;&nbsp;&nbsp;&nbsp;'Grapefruit',

&nbsp;&nbsp;&nbsp;&nbsp;'DANGER',

&nbsp;&nbsp;&nbsp;&nbsp;'자몽의 푸라노쿠마린(Furanocoumarin) 성분이 소장 내 대사 효소 CYP3A4를 비가역적으로 억제하여 스타틴 혈중 농도를 급증시키고 횡문근융해증 유발 위험을 높입니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'아토르바스타틴 복용 기간 동안 자몽 생과 및 자몽 주스의 섭취를 금지하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;),

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000003',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000003',

&nbsp;&nbsp;&nbsp;&nbsp;'Calcium\_High',

&nbsp;&nbsp;&nbsp;&nbsp;'CAUTION',

&nbsp;&nbsp;&nbsp;&nbsp;'고칼슘 유제품 및 칼슘 보충제가 위장관 내에서 레보티록신과 불용성 킬레이트를 형성하여 약물의 생체이용률을 현저히 떨어뜨립니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'우유, 치즈 등 고칼슘 식품은 갑상선 호르몬제 복용 후 최소 2시간에서 4시간의 간격을 두고 섭취하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;)

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 4\. 테스터 사용자의 상시 복약 정보 등록

INSERT INTO user\_medications (id, user\_id, drug\_id, prescribed\_dosage\_mg, is\_active, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('m0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000001', 5.00, TRUE, NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

## **8\. API Specifications & Type Contracts**

### **8.1 엔드포인트 개요**

| Method | Endpoint | Auth Required | HTTP Status | FR-ID 매핑 | 설명 |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `POST` | `/api/v1/auth/register` | No | `201 Created` | FR-007 | 신규 사용자 계정 등록 |
| `POST` | `/api/v1/auth/login` | No | `200 OK` | FR-007 | 이메일/비밀번호 인증 및 HttpOnly 세션 쿠키 발급 |
| `POST` | `/api/v1/auth/refresh` | No | `200 OK` | FR-007 | Refresh Token 검증을 통한 Access Token 재발급 |
| `POST` | `/api/v1/auth/logout` | Yes | `200 OK` | FR-007 | 인증 쿠키 만료 처리 및 로그아웃 |
| `POST` | `/api/v1/vision/estimate` | Yes | `200 OK` | FR-001 \~ FR-006 | 이미지 업로드 기반 단안 3D 부피 추정 및 복약 간섭 분석 |
| `GET` | `/api/v1/meals` | Yes | `200 OK` | FR-007 | 사용자의 과거 식단 기록 페이지네이션 목록 조회 |
| `GET` | `/api/v1/meals/{meal_id}` | Yes | `200 OK` | FR-007 | 특정 식단의 3D 시각화 데이터 및 영양/복약 상세 조회 |
| `GET` | `/api/v1/drugs/interactions` | Yes | `200 OK` | FR-005 | 특정 약제-식품 상호작용 규칙 사전 조회 |

### **8.2 완전한 TypeScript Type Contracts (`frontend/src/types/api.ts`)**

TypeScript

export type UserRole \= 'USER' | 'ADMIN';

export type RiskLevel \= 'DANGER' | 'CAUTION' | 'INFO';

export type DetectionSource \= 'VISUAL\_GROUNDING' | 'USER\_PROFILE';

&nbsp;

export interface BoundingBox2D {

&nbsp;&nbsp;ymin: number;

&nbsp;&nbsp;xmin: number;

&nbsp;&nbsp;ymax: number;

&nbsp;&nbsp;xmax: number;

}

&nbsp;

export interface Point3D {

&nbsp;&nbsp;x: number;

&nbsp;&nbsp;y: number;

&nbsp;&nbsp;z: number;

}

&nbsp;

export interface BoundingBox3D {

&nbsp;&nbsp;center: Point3D;

&nbsp;&nbsp;dimensions: Point3D;

&nbsp;&nbsp;rotations: Point3D;

&nbsp;&nbsp;vertices: Point3D\[\];

}

&nbsp;

export interface PlaneEquation {

&nbsp;&nbsp;a: number;

&nbsp;&nbsp;b: number;

&nbsp;&nbsp;c: number;

&nbsp;&nbsp;d: number;

}

&nbsp;

export interface FoodItemEstimation {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;foodName: string;

&nbsp;&nbsp;confidenceScore: number;

&nbsp;&nbsp;volumeCm3: number;

&nbsp;&nbsp;densityGCm3: number;

&nbsp;&nbsp;weightG: number;

&nbsp;&nbsp;caloriesKcal: number;

&nbsp;&nbsp;carbsG: number;

&nbsp;&nbsp;proteinG: number;

&nbsp;&nbsp;fatG: number;

&nbsp;&nbsp;sodiumMg: number;

&nbsp;&nbsp;bbox2d: BoundingBox2D;

&nbsp;&nbsp;bbox3d: BoundingBox3D;

}

&nbsp;

export interface DrugInteractionWarning {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;drugBrandName: string;

&nbsp;&nbsp;drugIngredient: string;

&nbsp;&nbsp;triggerNutrientOrFood: string;

&nbsp;&nbsp;riskLevel: RiskLevel;

&nbsp;&nbsp;detectedVia: DetectionSource;

&nbsp;&nbsp;warningTitle: string;

&nbsp;&nbsp;warningMessage: string;

&nbsp;&nbsp;actionGuide: string;

}

&nbsp;

export interface SparsePointCloudPayload {

&nbsp;&nbsp;count: number;

&nbsp;&nbsp;positions: number\[\];

&nbsp;&nbsp;colors: number\[\];

}

&nbsp;

export interface NutritionSummary {

&nbsp;&nbsp;caloriesKcal: number;

&nbsp;&nbsp;carbsG: number;

&nbsp;&nbsp;proteinG: number;

&nbsp;&nbsp;fatG: number;

&nbsp;&nbsp;sodiumMg: number;

}

&nbsp;

export interface MealEstimateResponse {

&nbsp;&nbsp;mealId: string;

&nbsp;&nbsp;imageUrl: string;

&nbsp;&nbsp;isCalibrated: boolean;

&nbsp;&nbsp;focalLengthMm: number;

&nbsp;&nbsp;groundPlane: PlaneEquation;

&nbsp;&nbsp;totalNutrition: NutritionSummary;

&nbsp;&nbsp;foodItems: FoodItemEstimation\[\];

&nbsp;&nbsp;drugWarnings: DrugInteractionWarning\[\];

&nbsp;&nbsp;visualization3d: {

&nbsp;&nbsp;&nbsp;&nbsp;pointCloud: SparsePointCloudPayload;

&nbsp;&nbsp;};

&nbsp;&nbsp;processedAt: string;

&nbsp;&nbsp;inferenceLatencyMs: number;

}

&nbsp;

export interface MealSummaryItem {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;imageUrl: string;

&nbsp;&nbsp;totalCaloriesKcal: number;

&nbsp;&nbsp;foodItemCount: number;

&nbsp;&nbsp;highestRiskLevel: RiskLevel | 'NONE';

&nbsp;&nbsp;createdAt: string;

}

&nbsp;

export interface MealHistoryResponse {

&nbsp;&nbsp;totalCount: number;

&nbsp;&nbsp;page: number;

&nbsp;&nbsp;pageSize: number;

&nbsp;&nbsp;items: MealSummaryItem\[\];

}

&nbsp;

export interface DrugInteractionDetail {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;drugId: string;

&nbsp;&nbsp;kdCode: string;

&nbsp;&nbsp;brandName: string;

&nbsp;&nbsp;ingredientName: string;

&nbsp;&nbsp;triggerNutrient: string;

&nbsp;&nbsp;riskLevel: RiskLevel;

&nbsp;&nbsp;mechanismDesc: string;

&nbsp;&nbsp;actionGuide: string;

&nbsp;&nbsp;sourceAuthority: string;

}

&nbsp;

export interface UserProfileResponse {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;email: string;

&nbsp;&nbsp;name: string;

&nbsp;&nbsp;role: UserRole;

&nbsp;&nbsp;createdAt: string;

}

&nbsp;

export interface StandardApiResponse\<T\> {

&nbsp;&nbsp;success: true;

&nbsp;&nbsp;data: T;

}

&nbsp;

export interface StandardApiErrorDetail {

&nbsp;&nbsp;field: string;

&nbsp;&nbsp;issue: string;

}

&nbsp;

export interface StandardErrorResponse {

&nbsp;&nbsp;success: false;

&nbsp;&nbsp;error: {

&nbsp;&nbsp;&nbsp;&nbsp;code: string;

&nbsp;&nbsp;&nbsp;&nbsp;message: string;

&nbsp;&nbsp;&nbsp;&nbsp;timestamp: string;

&nbsp;&nbsp;&nbsp;&nbsp;path: string;

&nbsp;&nbsp;&nbsp;&nbsp;details?: StandardApiErrorDetail\[\];

&nbsp;&nbsp;};

}

&nbsp;

### **8.3 Zod Validation Schemas (`frontend/src/schemas/api.ts`)**

TypeScript

import { z } from 'zod';

&nbsp;

export const RegisterRequestSchema \= z.object({

&nbsp;&nbsp;email: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이메일은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.email('올바른 이메일 형식이 아닙니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(255, '이메일은 최대 255자까지 가능합니다.'),

&nbsp;&nbsp;password: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '비밀번호는 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(8, '비밀번호는 최소 8자 이상이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(128, '비밀번호는 최대 128자까지 가능합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[A-Z\]/, '비밀번호에 최소 1개 이상의 대문자가 포함되어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[0-9\]/, '비밀번호에 최소 1개 이상의 숫자가 포함되어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[^A-Za-z0-9\]/, '비밀번호에 최소 1개 이상의 특수문자가 포함되어야 합니다.'),

&nbsp;&nbsp;name: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이름은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(2, '이름은 최소 2자 이상이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(100, '이름은 최대 100자까지 가능합니다.')

});

&nbsp;

export const LoginRequestSchema \= z.object({

&nbsp;&nbsp;email: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이메일은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.email('올바른 이메일 형식이 아닙니다.'),

&nbsp;&nbsp;password: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '비밀번호는 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(1, '비밀번호를 입력해야 합니다.')

});

&nbsp;

export const VisionEstimateFormSchema \= z.object({

&nbsp;&nbsp;file: z

&nbsp;&nbsp;&nbsp;&nbsp;.instanceof(File, { message: '업로드할 이미지 파일이 필요합니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.refine((file) \=\> file.size \<= 10 \* 1024 \* 1024, '이미지 크기는 최대 10MB까지 가능합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.refine(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(file) \=\> \['image/jpeg', 'image/png', 'image/webp'\].includes(file.type),

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'지원 가능한 이미지 형식은 JPEG, PNG, WEBP입니다.'

&nbsp;&nbsp;&nbsp;&nbsp;),

&nbsp;&nbsp;focal\_length\_mm: z

&nbsp;&nbsp;&nbsp;&nbsp;.number()

&nbsp;&nbsp;&nbsp;&nbsp;.positive('초점거리는 양수여야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional()

&nbsp;&nbsp;&nbsp;&nbsp;.default(26.0)

});

&nbsp;

export const MealHistoryQuerySchema \= z.object({

&nbsp;&nbsp;page: z.coerce.number().int().positive().default(1),

&nbsp;&nbsp;pageSize: z.coerce.number().int().min(1).max(50).default(10),

&nbsp;&nbsp;startDate: z

&nbsp;&nbsp;&nbsp;&nbsp;.string()

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/^\\d{4}-\\d{2}-\\d{2}$/, '시작일은 YYYY-MM-DD 형식이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional(),

&nbsp;&nbsp;endDate: z

&nbsp;&nbsp;&nbsp;&nbsp;.string()

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/^\\d{4}-\\d{2}-\\d{2}$/, '종료일은 YYYY-MM-DD 형식이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional()

});

&nbsp;

export const DrugInteractionQuerySchema \= z.object({

&nbsp;&nbsp;drug\_id: z.string().uuid('유효한 UUID 형식이어야 합니다.').optional(),

&nbsp;&nbsp;kd\_code: z.string().max(50).optional()

});

&nbsp;

export type RegisterRequestDto \= z.infer\<typeof RegisterRequestSchema\>;

export type LoginRequestDto \= z.infer\<typeof LoginRequestSchema\>;

export type VisionEstimateFormDto \= z.infer\<typeof VisionEstimateFormSchema\>;

export type MealHistoryQueryDto \= z.infer\<typeof MealHistoryQuerySchema\>;

export type DrugInteractionQueryDto \= z.infer\<typeof DrugInteractionQuerySchema\>;

&nbsp;

### **8.4 엔드포인트별 상세 입출력 명세**

#### **8.4.1 `POST /api/v1/vision/estimate` \[FR-001 \~ FR-006\]**

* **요청 헤더**: `Authorization: Bearer <AccessToken>` (또는 `access_token` 쿠키), `Content-Type: multipart/form-data`  
* **Request Form Data**:  
  * `file`: 이미지 바이너리 (`image/jpeg`, `image/png`)  
  * `focal_length_mm`: 선택 입력 (부재 시 기본값 `26.0`)  
* **성공 응답 (`200 OK`)**:

JSON

{

&nbsp;&nbsp;"success": true,

&nbsp;&nbsp;"data": {

&nbsp;&nbsp;&nbsp;&nbsp;"mealId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",

&nbsp;&nbsp;&nbsp;&nbsp;"imageUrl": "\<https://storage.volumeal.io/meals/2026/09/09/sample\_meal.jpg\>",

&nbsp;&nbsp;&nbsp;&nbsp;"isCalibrated": true,

&nbsp;&nbsp;&nbsp;&nbsp;"focalLengthMm": 26.0,

&nbsp;&nbsp;&nbsp;&nbsp;"groundPlane": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"a": 0.012,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"b": \-0.998,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"c": 0.054,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"d": 0.452

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"totalNutrition": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"caloriesKcal": 542.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"carbsG": 72.30,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"proteinG": 34.20,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"fatG": 12.80,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"sodiumMg": 640.00

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"foodItems": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "e1a2b3c4-0001-4000-8000-000000000001",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"foodName": "백미밥",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"confidenceScore": 0.942,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"volumeCm3": 210.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"densityGCm3": 1.0500,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"weightG": 221.03,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"caloriesKcal": 320.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"carbsG": 68.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"proteinG": 6.20,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"fatG": 0.80,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"sodiumMg": 4.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox2d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"ymin": 0.45,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"xmin": 0.12,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"ymax": 0.78,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"xmax": 0.45

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox3d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"center": { "x": \-0.15, "y": \-0.05, "z": 0.52 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"dimensions": { "x": 0.12, "y": 0.06, "z": 0.12 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"rotations": { "x": 0.0, "y": 0.0, "z": 0.0 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"vertices": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.08, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.08, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.02, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.02, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.08, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.08, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.02, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.02, "z": 0.58 }

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\],

&nbsp;&nbsp;&nbsp;&nbsp;"drugWarnings": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "w1a2b3c4-0001-4000-8000-000000000001",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"drugBrandName": "쿠마딘정5밀리그람",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"drugIngredient": "와파린나트륨 (Warfarin Sodium)",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"triggerNutrientOrFood": "시금치나물 (Vitamin\_K)",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"riskLevel": "DANGER",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"detectedVia": "VISUAL\_GROUNDING",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"warningTitle": "와파린 약효 저하 위험 성분 감지",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"warningMessage": "식탁에서 식별된 처방약(쿠마딘정)과 고비타민K 반찬(시금치나물) 간의 대사 간섭이 발생합니다.",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"actionGuide": "비타민 K 섭취가 급증하면 혈전 예방 작용이 길항됩니다. 섭취량을 최소화하거나 담당 의료진과 상의하십시오."

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\],

&nbsp;&nbsp;&nbsp;&nbsp;"visualization3d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"pointCloud": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"count": 3,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"positions": \[-0.15, \-0.05, 0.52, \-0.14, \-0.04, 0.51, \-0.16, \-0.05, 0.53\],

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"colors": \[0.85, 0.82, 0.78, 0.86, 0.83, 0.79, 0.84, 0.81, 0.77\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"processedAt": "2026-09-09T11:42:00.123Z",

&nbsp;&nbsp;&nbsp;&nbsp;"inferenceLatencyMs": 284

&nbsp;&nbsp;}

}

&nbsp;

#### **8.4.2 `GET /api/v1/meals` \[FR-007\]**

* **요청 파라미터**: `page=1&pageSize=10`  
* **성공 응답 (`200 OK`)**:

JSON

{

&nbsp;&nbsp;"success": true,

&nbsp;&nbsp;"data": {

&nbsp;&nbsp;&nbsp;&nbsp;"totalCount": 42,

&nbsp;&nbsp;&nbsp;&nbsp;"page": 1,

&nbsp;&nbsp;&nbsp;&nbsp;"pageSize": 10,

&nbsp;&nbsp;&nbsp;&nbsp;"items": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"imageUrl": "\<https://storage.volumeal.io/meals/2026/09/09/sample\_meal.jpg\>",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"totalCaloriesKcal": 542.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"foodItemCount": 3,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"highestRiskLevel": "DANGER",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"createdAt": "2026-09-09T11:42:00.123Z"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;}

}

&nbsp;

## **9\. Authentication & Authorization**

### **9.1 인증 라이프사이클 (JWT Lifecycle)**

코드 스니펫

sequenceDiagram

&nbsp;&nbsp;&nbsp;&nbsp;autonumber

&nbsp;&nbsp;&nbsp;&nbsp;actor Client as 브라우저 (Next.js 14\)

&nbsp;&nbsp;&nbsp;&nbsp;participant AuthAPI as FastAPI Auth Router

&nbsp;&nbsp;&nbsp;&nbsp;participant Guard as JWT Dependency Guard

&nbsp;&nbsp;&nbsp;&nbsp;participant DB as PostgreSQL 15

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, AuthAPI: 1\. 로그인 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/login (email, password)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>DB: SELECT \* FROM users WHERE email \= :email

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: verify\_password(raw\_password, hashed\_password)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: create\_access\_token(sub=user\_id, role, exp=15m)\<br\>create\_refresh\_token(sub=user\_id, jti, exp=7d)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (HttpOnly, Secure, SameSite=Strict, Max-Age=900)\<br\>Set-Cookie: refresh\_token (HttpOnly, Secure, SameSite=Strict, Max-Age=604800)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, Guard: 2\. 인가된 요청 및 만료 갱신 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Guard: POST /api/v1/vision/estimate (Cookie 자동 첨부)

&nbsp;&nbsp;&nbsp;&nbsp;alt Access Token 유효

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard-\>\>Guard: decode\_token(access\_token) & verify\_signature

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard--\>\>AuthAPI: Request Proceed (Current UserContext 주입)

&nbsp;&nbsp;&nbsp;&nbsp;else Access Token 만료 (401 Unauthorized)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard--\>\>Client: 401 Unauthorized (ERR\_TOKEN\_EXPIRED)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/refresh (refresh\_token Cookie 첨부)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: verify\_token(refresh\_token)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (신규 토큰 갱신)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Guard: POST /api/v1/vision/estimate (재요청 성공)

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, AuthAPI: 3\. 로그아웃 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/logout

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (Max-Age=0)\<br\>Set-Cookie: refresh\_token (Max-Age=0)

&nbsp;

### **9.2 토큰 보관 및 전송 보안 메커니즘**

1. **브라우저 스토리지 차단**: `access_token`과 `refresh_token`은 브라우저의 `localStorage`, `sessionStorage`, 일반 JavaScript 런타임 메모리에 저장하지 않으며 서버 응답 헤더의 `Set-Cookie`를 통해서만 설정됩니다.  
2. **쿠키 보안 플래그 강제**:  
   * `HttpOnly`: XSS 공격 스크립트를 통한 토큰 탈취 원천 차단.  
   * `Secure`: HTTPS 전송 구간에서만 쿠키 전송 허용.  
   * `SameSite=Strict`: 타 사이트로부터 유입되는 Cross-Site 요청에 쿠키 첨부를 전면 차단하여 CSRF 무력화.  
3. **토큰 규격**:  
   * `access_token`: 수명 15분, 서명 알고리즘 `HS256`, 클레임(`sub`: User UUID, `role`: UserRole, `exp`: Timestamp).  
   * `refresh_token`: 수명 7일, 클레임(`sub`: User UUID, `jti`: Session UUID, `exp`: Timestamp).

### **9.3 RBAC 권한 매트릭스 테이블**

| 엔드포인트 경로 | HTTP Method | GUEST (미인증) | USER (일반회원) | ADMIN (관리자) |
| ----- | ----- | ----- | ----- | ----- |
| `/api/v1/auth/register` | `POST` | 허용 | 차단 | 차단 |
| `/api/v1/auth/login` | `POST` | 허용 | 차단 | 차단 |
| `/api/v1/auth/refresh` | `POST` | 허용 | 허용 | 허용 |
| `/api/v1/auth/logout` | `POST` | 차단 | 허용 | 허용 |
| `/api/v1/vision/estimate` | `POST` | 차단 | 허용 | 허용 |
| `/api/v1/meals` | `GET` | 차단 | 본인 데이터 한정 허용 | 전체 허용 |
| `/api/v1/meals/{meal_id}` | `GET` | 차단 | 본인 데이터 한정 허용 | 전체 허용 |
| `/api/v1/drugs/interactions` | `GET` | 차단 | 허용 | 허용 |
| `/api/v1/admin/**` | ALL | 차단 | 차단 | 전체 허용 |

### **9.4 FastAPI 인증 의존성 구현 명세 (`backend/app/api/deps.py`)**

Python

from typing import Annotated

import uuid

from fastapi import Depends, HTTPException, Request, status

from jose import JWTError, jwt

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

&nbsp;

from app.core.config import settings

from app.core.database import get\_db\_session

from app.models.user import User

&nbsp;

async def get\_current\_user(

&nbsp;&nbsp;&nbsp;&nbsp;request: Request,

&nbsp;&nbsp;&nbsp;&nbsp;db: Annotated\[AsyncSession, Depends(get\_db\_session)\]) \-\> User:

&nbsp;&nbsp;&nbsp;&nbsp;token \= request.cookies.get("access\_token")

&nbsp;&nbsp;&nbsp;&nbsp;if not token:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;auth\_header \= request.headers.get("Authorization")

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if auth\_header and auth\_header.startswith("Bearer "):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;token \= auth\_header.split(" ")\[1\]

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;if not token:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_AUTHENTICATION\_REQUIRED", "message": "인증 자격 증명이 누락되었습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;try:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;payload \= jwt.decode(token, settings.JWT\_SECRET\_KEY, algorithms=\[settings.JWT\_ALGORITHM\])

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;user\_id\_str: str \= payload.get("sub")

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if not user\_id\_str:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_INVALID\_TOKEN", "message": "유효하지 않은 토큰 페이로드입니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;user\_id \= uuid.UUID(user\_id\_str)

&nbsp;&nbsp;&nbsp;&nbsp;except (JWTError, ValueError):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_TOKEN\_EXPIRED", "message": "인증 토큰이 만료되었거나 서명이 유효하지 않습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;stmt \= select(User).where(User.id \== user\_id)

&nbsp;&nbsp;&nbsp;&nbsp;result \= await db.execute(stmt)

&nbsp;&nbsp;&nbsp;&nbsp;user \= result.scalar\_one\_or\_none()

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;if not user:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_USER\_NOT\_FOUND", "message": "토큰에 해당하는 사용자를 찾을 수 없습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;return user

&nbsp;

def require\_role(required\_role: str):

&nbsp;&nbsp;&nbsp;&nbsp;async def role\_checker(current\_user: Annotated\[User, Depends(get\_current\_user)\]) \-\> User:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if current\_user.role \!= required\_role and current\_user.role \!= "ADMIN":

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_403\_FORBIDDEN,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_ACCESS\_DENIED", "message": "해당 작업에 대한 접근 권한이 없습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return current\_user

&nbsp;&nbsp;&nbsp;&nbsp;return role\_checker

&nbsp;

## **10\. Error Handling**

### **10.1 전역 표준 에러 응답 규격**

모든 시스템 실패 응답은 일관된 JSON 객체 구조를 반환합니다.

JSON

{

&nbsp;&nbsp;"success": false,

&nbsp;&nbsp;"error": {

&nbsp;&nbsp;&nbsp;&nbsp;"code": "ERR\_VALIDATION\_FAILED",

&nbsp;&nbsp;&nbsp;&nbsp;"message": "입력 파라미터 유효성 검증에 실패했습니다.",

&nbsp;&nbsp;&nbsp;&nbsp;"timestamp": "2026-09-09T11:51:26.000Z",

&nbsp;&nbsp;&nbsp;&nbsp;"path": "/api/v1/vision/estimate",

&nbsp;&nbsp;&nbsp;&nbsp;"details": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"field": "file",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"issue": "파일 확장자가 지원되지 않는 포맷입니다."

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;}

}

&nbsp;

TypeScript

export interface StandardErrorResponse {

&nbsp;&nbsp;success: false;

&nbsp;&nbsp;error: {

&nbsp;&nbsp;&nbsp;&nbsp;code: string;

&nbsp;&nbsp;&nbsp;&nbsp;message: string;

&nbsp;&nbsp;&nbsp;&nbsp;timestamp: string;

&nbsp;&nbsp;&nbsp;&nbsp;path: string;

&nbsp;&nbsp;&nbsp;&nbsp;details?: Array\<{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;field: string;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;issue: string;

&nbsp;&nbsp;&nbsp;&nbsp;}\>;

&nbsp;&nbsp;};

}

&nbsp;

### **10.2 시스템 에러 매핑 테이블**

| HTTP Status | Internal Error Code | Error Message | 발생 조건 |
| ----- | ----- | ----- | ----- |
| `400 Bad Request` | `ERR_BAD_REQUEST` | 잘못된 요청 형식입니다. | JSON 역직렬화 실패 또는 필수 파라미터 누락 |
| `400 Bad Request` | `ERR_INVALID_IMAGE_PAYLOAD` | 이미지 매직 넘버 검증에 실패했습니다. | 파일 확장자는 이미지이나 바이너리 헤더 불일치 |
| `400 Bad Request` | `ERR_IMAGE_SIZE_EXCEEDED` | 업로드 파일 크기가 10MB를 초과했습니다. | 업로드 파일 크기 \> 10,485,760 바이트 |
| `401 Unauthorized` | `ERR_AUTHENTICATION_REQUIRED` | 인증 자격 증명이 누락되었습니다. | Auth Cookie 및 Authorization 헤더 미제공 |
| `401 Unauthorized` | `ERR_TOKEN_EXPIRED` | 인증 토큰이 만료되었습니다. | JWT `exp` 타임스탬프 경과 |
| `401 Unauthorized` | `ERR_INVALID_CREDENTIALS` | 이메일 또는 비밀번호가 일치하지 않습니다. | 로그인 시 계정 부재 또는 해시 불일치 |
| `403 Forbidden` | `ERR_ACCESS_DENIED` | 해당 리소스에 접근 권한이 없습니다. | 타 사용자의 Meal ID 상세 조회 시도 |
| `404 Not Found` | `ERR_RESOURCE_NOT_FOUND` | 요청한 리소스를 찾을 수 없습니다. | 조회 대상 `meal_id` 또는 `drug_id` 부재 |
| `422 Unprocessable Entity` | `ERR_GEOMETRY_PLANE_NOT_FOUND` | 테이블 기준 평면 추정에 실패했습니다. | RANSAC 평면 피팅 인라이어 비율 40% 미달 |
| `422 Unprocessable Entity` | `ERR_VOLUME_OUT_OF_BOUNDS` | 연산된 음식 부피가 유효 범위를 벗어났습니다. | 부피 계산치 $V \\le 5\\,\\text{cm}^3$ 또는 $V \\ge 5000\\,\\text{cm}^3$ |
| `422 Unprocessable Entity` | `ERR_ZERO_OBJECT_DETECTED` | 이미지 내 음식 또는 약제가 검출되지 않았습니다. | YOLOv8-Seg 검출 객체 수 \= 0 |
| `429 Too Many Requests` | `ERR_RATE_LIMIT_EXCEEDED` | 단시간 내 너무 많은 요청이 발생했습니다. | API별 할당 Rate Limit 임계치 초과 |
| `500 Internal Server Error` | `ERR_INFERENCE_ENGINE_CRASH` | 비전 추론 런타임 처리 중 장애가 발생했습니다. | ONNX Runtime 프로세스 충돌 또는 모델 연산 에러 |
| `500 Internal Server Error` | `ERR_DATABASE_TRANSACTION` | 데이터베이스 작업 중 오류가 발생했습니다. | SQLAlchemy 비동기 트랜잭션 충돌 및 롤백 |

# **Technical Specification: VoluMeal-Align \- Turn 3**

## **11\. Testing Strategy**

### **11.1 Unit Test (도메인 수치 기하학 및 약리 규칙 검증)**

| Test Suite | 대상 파일 | 검증 시나리오 및 경계 조건 | 기대 결과 | 연관 FR |
| ----- | ----- | ----- | ----- | ----- |
| `test_geometry_plane_ransac` | `app/ml/geometry_integrator.py` | 가상 평면($z \= 0$) 위에 합성 노이즈($\\sigma=0.005\\text{m}$)가 포함된 10,000개 포인트 클라우드 입력 시 RANSAC 표면 방정식($ax+by+cz+d=0$) 추정 | 법선 벡터 각도 오차 $\\le 1.5^\\circ$, 평면 인라이어 비율 $\\ge 90\\%$ | FR-003 |
| `test_volume_numerical_integration` | `app/ml/geometry_integrator.py` | $10\\text{cm} \\times 10\\text{cm} \\times 10\\text{cm}$ 크기의 이상적 직육면체 합성 깊이 맵 ($V \= 1000\\,\\text{cm}^3$) 적분 | 연산 체적 오차율 $\\le 2.5\\%$ ($975 \\le V \\le 1025$) | FR-003 |
| `test_volume_out_of_bounds_rejection` | `app/ml/geometry_integrator.py` | 유효 범위를 벗어난 체적 입력 ($V \= 2.1\\,\\text{cm}^3$ 및 $V \= 6400\\,\\text{cm}^3$) | `VolumeOutOfBoundsException` (HTTP 422 매핑) 발생 | FR-003 |
| `test_drug_interaction_matrix` | `app/services/drug_interaction_service.py` | 1\) 쿠마딘정(와파린) \+ 시금치나물(Vitamin K) |  |  |

2.   
   리피토정(스타틴) \+ 자몽주스(Grapefruit)

3. 씬지로이드(레보티록신) \+ 우유(Calcium)

4. 음성 대조군: 리피토정 \+ 백미밥 | 1\) `DANGER` 등급 경고 반환

5. `DANGER` 등급 경고 반환

6. `CAUTION` 등급 경고 반환

7. `drugWarnings` 빈 배열 반환 | FR-005 |  
   &nbsp;| `test_camera_backprojection` | `app/ml/camera_utils.py` | 초점거리 $f=26\\text{mm}$, 센서 규격 기준 깊이 $Z=0.5\\text{m}$ 지점의 주점 $(c\_x, c\_y)$ 역투영 | $X=0.0, Y=0.0, Z=0.5$ 공간 좌표 정확 도출 | FR-001, FR-003 |

#### **핵심 수치 기하학 및 약리 규칙 단위 테스트 구현 (`backend/tests/unit/test_geometry_and_rules.py`)**

Python

import pytest

import numpy as np

from app.ml.geometry\_integrator import NumericalVolumeIntegrator

from app.services.drug\_interaction\_service import DrugInteractionService

from app.core.exceptions import VolumeOutOfBoundsException

&nbsp;

def test\_ransac\_plane\_fitting\_synthetic():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;np.random.seed(42)

&nbsp;&nbsp;&nbsp;&nbsp;\# z \= 0.5m 평면 상의 5000개 점군 생성

&nbsp;&nbsp;&nbsp;&nbsp;x \= np.random.uniform(-0.3, 0.3, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;y \= np.random.uniform(-0.3, 0.3, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;z \= np.full\_like(x, 0.5) \+ np.random.normal(0, 0.002, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;points \= np.stack(\[x, y, z\], axis=-1)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;plane\_eq, inlier\_ratio \= integrator.fit\_plane\_ransac(points, distance\_threshold=0.01)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert inlier\_ratio \>= 0.90

&nbsp;&nbsp;&nbsp;&nbsp;\# 평면 방정식 ax \+ by \+ cz \+ d \= 0에서 z축 법선 벡터 c는 1에 수렴해야 함

&nbsp;&nbsp;&nbsp;&nbsp;normal \= np.array(\[plane\_eq\["a"\], plane\_eq\["b"\], plane\_eq\["c"\]\])

&nbsp;&nbsp;&nbsp;&nbsp;normal \= normal / np.linalg.norm(normal)

&nbsp;&nbsp;&nbsp;&nbsp;assert abs(abs(normal\[2\]) \- 1.0) \< 0.05

&nbsp;

def test\_exact\_cube\_numerical\_integration():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;\# 10cm x 10cm 바닥에 높이 5cm인 음식 (부피 500 cm3)

&nbsp;&nbsp;&nbsp;&nbsp;grid\_res \= 0.002  \# 2mm 단위 격자

&nbsp;&nbsp;&nbsp;&nbsp;x \= np.arange(-0.05, 0.05, grid\_res)

&nbsp;&nbsp;&nbsp;&nbsp;y \= np.arange(-0.05, 0.05, grid\_res)

&nbsp;&nbsp;&nbsp;&nbsp;xx, yy \= np.meshgrid(x, y)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;z\_table \= np.full\_like(xx, 0.60) \# 바닥면 거리 0.60m

&nbsp;&nbsp;&nbsp;&nbsp;z\_food \= np.full\_like(xx, 0.55)  \# 음식 상단 거리 0.55m (높이 0.05m \= 5cm)

&nbsp;&nbsp;&nbsp;&nbsp;mask \= np.ones\_like(xx, dtype=bool)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;volume\_cm3 \= integrator.integrate\_height\_difference(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;z\_table=z\_table,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;z\_food=z\_food,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask=mask,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pixel\_area\_m2=grid\_res \* grid\_res

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert pytest.approx(volume\_cm3, rel=0.025) \== 500.0

&nbsp;

def test\_volume\_boundary\_exception():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;with pytest.raises(VolumeOutOfBoundsException):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;integrator.validate\_volume\_bounds(3.5) \# 5cm3 미만 차단

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;with pytest.raises(VolumeOutOfBoundsException):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;integrator.validate\_volume\_bounds(5500.0) \# 5000cm3 초과 차단

&nbsp;

def test\_drug\_interaction\_rule\_evaluation():

&nbsp;&nbsp;&nbsp;&nbsp;service \= DrugInteractionService()

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;\# 케이스 1: 와파린 \+ 비타민K 위험 판정

&nbsp;&nbsp;&nbsp;&nbsp;warnings \= service.evaluate\_interactions(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detected\_drug\_codes=\["641800240"\], \# 쿠마딘정

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;food\_nutrients=\["Vitamin\_K", "Carbohydrate"\]

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;assert len(warnings) \== 1

&nbsp;&nbsp;&nbsp;&nbsp;assert warnings\[0\].risk\_level \== "DANGER"

&nbsp;&nbsp;&nbsp;&nbsp;assert "와파린" in warnings\[0\].warning\_title

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;\# 케이스 2: 스타틴 \+ 일반 쌀밥 (정상)

&nbsp;&nbsp;&nbsp;&nbsp;safe\_check \= service.evaluate\_interactions(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detected\_drug\_codes=\["644900110"\], \# 리피토정

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;food\_nutrients=\["Carbohydrate", "Protein"\]

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;assert len(safe\_check) \== 0

&nbsp;

### **11.2 Integration Test (ONNX 서빙 및 DB 트랜잭션 격리 검증)**

* **ONNX 서빙 가상화 및 모델 모킹(Mocking)**:  
  * CI 서버 및 유닛 통합 테스트 환경에서는 대형 모델의 연산 병목을 제거하기 위해 고정된 깊이 맵(Float32 Matrix, 전 영역 0.55m)과 표준 식판 마스크 바이너리 텐서를 반환하는 `MockDepthEstimator`, `MockSegmentor`를 의존성 주입 컨테이너에 바인딩합니다.  
* **DB 세이브포인트 롤백 전략**:  
  * `pytest-asyncio` 환경에서 테스트 세션 시작 시 `AsyncConnection`을 열고 각 테스트 함수마다 중첩 트랜잭션(`begin_nested()`)을 생성하여 테스트가 통과/실패한 직후 무조건 `ROLLBACK` 처리함으로써 DB 격리성을 100% 보장합니다.

#### **통합 테스트 엔드포인트 파이프라인 검증 (`backend/tests/integration/test_vision_endpoint.py`)**

Python

import pytest

from httpx import AsyncClient

import io

from PIL import Image

from app.main import app

from app.api.deps import get\_depth\_estimator, get\_segmentor

&nbsp;

class FakeDepthEstimator:

&nbsp;&nbsp;&nbsp;&nbsp;def infer(self, image\_tensor):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\# 518x518 크기의 0.55m 깊이 맵 반환

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return np.full((518, 518), 0.55, dtype=np.float32)

&nbsp;

class FakeSegmentor:

&nbsp;&nbsp;&nbsp;&nbsp;def infer(self, image\_tensor):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\# 중앙 영역 100x100 픽셀 마스크 1건 반환

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask \= np.zeros((518, 518), dtype=bool)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask\[200:300, 200:300\] \= True

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return \[{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"label": "백미밥",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"confidence": 0.95,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"mask": mask,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox2d": \[0.38, 0.38, 0.58, 0.58\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}\]

&nbsp;

@pytest.fixture

def override\_vision\_models():

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides\[get\_depth\_estimator\] \= lambda: FakeDepthEstimator()

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides\[get\_segmentor\] \= lambda: FakeSegmentor()

&nbsp;&nbsp;&nbsp;&nbsp;yield

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides.clear()

&nbsp;

@pytest.mark.asyncio

async def test\_vision\_estimate\_full\_pipeline(async\_client: AsyncClient, auth\_cookie: dict, override\_vision\_models):

&nbsp;&nbsp;&nbsp;&nbsp;\# 가상 JPEG 이미지 바이너리 생성

&nbsp;&nbsp;&nbsp;&nbsp;img \= Image.new("RGB", (640, 480), color=(200, 200, 200))

&nbsp;&nbsp;&nbsp;&nbsp;buffer \= io.BytesIO()

&nbsp;&nbsp;&nbsp;&nbsp;img.save(buffer, format="JPEG")

&nbsp;&nbsp;&nbsp;&nbsp;buffer.seek(0)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;response \= await async\_client.post(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"/api/v1/vision/estimate",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;files={"file": ("meal.jpg", buffer, "image/jpeg")},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;data={"focal\_length\_mm": 26.0},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cookies=auth\_cookie

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert response.status\_code \== 200

&nbsp;&nbsp;&nbsp;&nbsp;res\_data \= response.json()

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["success"\] is True

&nbsp;&nbsp;&nbsp;&nbsp;assert "mealId" in res\_data\["data"\]

&nbsp;&nbsp;&nbsp;&nbsp;assert len(res\_data\["data"\]\["foodItems"\]) \== 1

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["data"\]\["foodItems"\]\[0\]\["foodName"\] \== "백미밥"

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["data"\]\["foodItems"\]\[0\]\["volumeCm3"\] \> 0

&nbsp;

### **11.3 End-to-End Test (Playwright 기반 시나리오 명세)**

* **E2E-001 (Happy Path \- 식단 촬영부터 3D 렌더링 및 위험 감지 완결)**:  
  1. 테스터 계정(`tester@volumeal.io`)으로 `/login` 페이지 접속 후 로그인 성공 및 `/` 이동.  
  2. 모바일 뷰파인더 캡처 입력폼에 시금치와 쿠마딘정이 포함된 `test_spinach_warfarin.jpg` 파일 입력.  
  3. 로딩 상태 스피너 노출 확인 후 1.5초 이내 결과 화면 렌더링 검증.  
  4. Three.js Canvas 엘리먼트(`canvas[data-engine="three.js"]`) 로드 및 점군 3D 객체 마운트 확인.  
  5. UI 상단 `DrugWarningBanner`에 `와파린 약효 저하 위험 성분 감지` (배경색: Red-600) 노출 확인.  
  6. 하단 아코디언에서 '시금치나물' 부피($\\text{cm}^3$), 중량($g$), 칼로리가 정확히 바인딩되었는지 확인.  
* **E2E-002 (Failure Path \- 파일 위변조 차단 및 유효성 에러 표출)**:  
  1. `.jpg` 확장자로 속인 임의의 텍스트 파일 `malicious.jpg` 업로드 시도.  
  2. 백엔드 매직 넘버 검증 실패로 `400 Bad Request` (`ERR_INVALID_IMAGE_PAYLOAD`) 발생.  
  3. 클라이언트 토스트 컴포넌트에 "유효한 이미지 형식이 아닙니다." 문구 노출 확인 및 업로드 폼 초기화.  
* **E2E-003 (Failure Path \- 바닥 평면 미검출 시 Graceful Fallback)**:  
  1. 테이블 바닥이 전혀 노출되지 않은 극단적 음식 클로즈업 사진 `no_plane_surface.jpg` 업로드.  
  2. 백엔드 수치 적분기에서 `ERR_GEOMETRY_PLANE_NOT_FOUND` (HTTP 422\) 수신.  
  3. 프론트엔드가 크래시되지 않고 "바닥면 인식 실패: 표준 1인분 영양 성분으로 대체 표시합니다" 다이얼로그를 표시하며 정적 2D 영양 정보로 Graceful Fallback 렌더링.

## **12\. Implementation Milestones**

10일 해커톤 일정 동안 "랩실 5090 오프라인 학습 $\\to$ ONNX 추출 $\\to$ 독립 서빙 배포" 구조를 완성하기 위한 단계별 실행 계획입니다.

\[Day 1\~2\] 스캐폴딩 & 인프라 ──\> \[Day 2\~3\] DB 스키마 & 시드 ──\> \[Day 3\~6\] 5090 학습 & ONNX 서빙

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

\[Day 9\~10\] E2E 검증 & 데모 리허설 \<── \[Day 6\~8\] Next.js & Three.js 3D 뷰어 \<──┘

&nbsp;

### **Phase 1: 프로젝트 스캐폴딩 및 기반 환경 구축 (Day 1 \~ Day 2\)**

* **Action Items**:

  * `volumeal-align` 모노레포 구조 세팅 및 `.cursorrules` 주입.  
  * `training/`, `backend/`, `frontend/` 디렉토리 초기화 및 독립 가상환경/패키지 설정.  
  * Docker Compose 로컬 환경(PostgreSQL 15, FastAPI, Next.js) 구성.

**실행 터미널 명령어**:Bash

&nbsp;\# 1\. 모노레포 루트 생성

mkdir \-p volumeal-align/{training,backend,frontend}

cd volumeal-align

&nbsp;

\# 2\. 백엔드 초기화

cd backend

python3 \-m venv .venv && source .venv/bin/activate

pip install fastapi==0.111.0 uvicorn\[standard\]==0.30.1 sqlalchemy\[asyncio\]==2.0.30 asyncpg==0.29.0 pydantic-settings==2.2.1 alembic==1.13.1 onnxruntime==1.18.0 open3d==0.18.0 numpy==1.26.4 pillow==10.3.0 python-jose\[cryptography\]==3.3.0 passlib\[bcrypt\]==1.7.4

pip freeze \> requirements.txt

&nbsp;

\# 3\. 프론트엔드 초기화

cd ../frontend

npx create-next-app@14.2.3 . \--typescript \--tailwind \--app \--src-dir \--import-alias "@/\*" \--use-npm

npm install three @types/three @react-three/fiber @react-three/drei zustand @tanstack/react-query zod axios clsx tailwind-merge lucide-react

* &nbsp;  
* **Definition of Done (DoD)**:

  * `docker compose up -d` 구동 시 PostgreSQL(`5432`), FastAPI Swagger UI(`http://localhost:8000/docs`), Next.js 메인(`http://localhost:3000`)이 정상 200 헬스체크를 반환함.

### **Phase 2: DB 스키마 구축, 마이그레이션 및 시드 데이터 적재 (Day 2 \~ Day 3\)**

* **Action Items**:

  * `backend/app/models/` 내 7개 SQLAlchemy 2.0 ORM 엔티티 정의.  
  * Alembic 비동기 마이그레이션 파이프라인 구성 및 최초 DDL 실행.  
  * `seed.sql` 마스터 데이터(관리자/테스터 계정, 식약처 3종 약제, 상호작용 매트릭스) 적재 스크립트 작성.

**실행 터미널 명령어**:Bash

&nbsp;cd backend

alembic init \-t async migrations

\# migrations/env.py에 app.models Base 등록 후 실행

alembic revision \--autogenerate \-m "create\_initial\_schema"

alembic upgrade head

python \-m app.data.seed\_runner

* &nbsp;  
* **Definition of Done (DoD)**:

  * PostgreSQL 컨테이너 내 7개 테이블이 정상 생성되고 외래키 인덱스가 활성화되며, `psql`을 통해 테스터 계정과 쿠마딘정-비타민K 금기 룰이 정상 쿼리됨.

### **Phase 3: 랩실 5090 학습, ONNX 모델 반출 및 독립 추론 엔진 구축 (Day 3 \~ Day 6\)**

* **Action Items**:

  * **\[랩실 GPU 환경\]**: `training/train_depth_metric.py` 실행하여 Depth Anything v2 Metric 경량 어댑터 학습.  
  * **\[랩실 GPU 환경\]**: `training/export_onnx.py` 실행하여 INT8/FP32 CPU 가속형 `depth_anything_v2_vits.onnx` 추출.  
  * 모델 아티팩트를 개인 배포 환경(`backend/app/ml/weights/`)으로 다운로드 후 랩실 세션 완전 종료.  
  * **\[독립 서빙 환경\]**: `onnx_depth_estimator.py`, `onnx_segmentor.py`, `geometry_integrator.py` 구현 \[FR-001\~FR-004\].  
  * `POST /api/v1/vision/estimate` API 엔드포인트 통합 및 수치 적분 부피 계산 완결 \[FR-006\].

**실행 터미널 명령어**:Bash

&nbsp;\# 랩실 RTX 5090 머신에서 실행 (1\~2시간 소요)

cd training

python train\_depth\_metric.py \--epochs 10 \--batch-size 32 \--device cuda

python export\_onnx.py \--checkpoint weights/best\_metric.pth \--output ../backend/app/ml/weights/depth\_anything\_v2\_vits.onnx

&nbsp;

\# 파일 추출 확인 후 랩실 프로세스 종료

ls \-lh ../backend/app/ml/weights/depth\_anything\_v2\_vits.onnx \# 약 95MB 확인

* &nbsp;  
* **Definition of Done (DoD)**:

  * 로컬/배포 백엔드 환경에서 GPU 없이 CPU ONNX Runtime만으로 테스트 이미지 입력 시 450ms 이내에 $V(\\text{cm}^3)$, $W(g)$, 영양소 및 다운샘플링된 점군 페이로드가 포함된 JSON 응답이 반환됨.

### **Phase 4: 프론트엔드 연동, Three.js 3D 뷰어 및 대시보드 UI (Day 6 \~ Day 8\)**

* **Action Items**:  
  * 모바일 카메라 뷰파인더 캡처 및 EXIF 초점거리 자동 추출기 구현 \[FR-001\].  
  * Three.js 기반 3D 점군(`PointCloudViewer.tsx`) 및 3D Bounding Box(`BoundingVolumeMesh.tsx`) 컴포넌트 개발 \[FR-006\].  
  * 영양소 통계 카드(`NutritionSummary.tsx`) 및 약제 위험 배너(`DrugWarningBanner.tsx`) 구현 \[FR-004, FR-005\].  
  * Zustand 상태 스토어(`useMealStore.ts`) 및 TanStack Query 비동기 연동.  
* **Definition of Done (DoD)**:  
  * 사용자가 모바일 뷰포트에서 식단 사진을 업로드하면 3D 뷰어에 음식 포인트 클라우드가 로드되어 터치 드래그로 회전/확대가 가능하고, 복약 위험 알림이 즉각 렌더링됨.

### **Phase 5: 인증/인가 통합, 전역 에러 핸들링 및 최종 데모 리허설 (Day 9 \~ Day 10\)**

* **Action Items**:  
  * JWT HttpOnly 쿠키 인증 가드 및 RBAC 미들웨어 통합.  
  * 전역 표준 예외 핸들러 및 React Error Boundary 컴포넌트 적용.  
  * Playwright E2E 자동화 스크립트 작성 및 Happy/Failure 3종 시나리오 통과.  
  * 심사용 데모 프리셋 데이터 캐싱 구축 (네트워크 단절 대비).  
* **Definition of Done (DoD)**:  
  * 심사위원 시연 시나리오(쿠마딘정 \+ 시금치 식단 촬영) 실행 시 1초 이내에 3D 와이어프레임과 DANGER 위험 알림이 표출되며 전체 E2E 테스트 통과.

## **13\. Environment & Deployment**

### **13.1 환경변수 명세 테이블**

| Variable Name | Environment | Purpose | Example Format | Required |
| ----- | ----- | ----- | ----- | ----- |
| `ENV` | Common | 런타임 환경 식별 | `development` | `production` |
| `PORT` | Backend | 서버 리스닝 포트 | `8000` | Yes |
| `DATABASE_URL` | Backend | PostgreSQL 비동기 연결 DSN | `postgresql+asyncpg://volu:pass@db:5432/volumeal` | Yes |
| `JWT_SECRET_KEY` | Backend | JWT 토큰 서명 대칭키 (최소 256bit) | `8f4b2c1e7a...64자 Hex` | Yes |
| `JWT_ALGORITHM` | Backend | 서명 알고리즘 | `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Access Token 수명 | `15` | Yes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Refresh Token 수명 | `7` | Yes |
| `ONNX_DEPTH_MODEL_PATH` | Backend | 반출된 Depth ONNX 파일 경로 | `/app/ml/weights/depth_anything_v2_vits.onnx` | Yes |
| `ONNX_SEG_MODEL_PATH` | Backend | 반출된 Segment ONNX 파일 경로 | `/app/ml/weights/yolov8s_seg.onnx` | Yes |
| `CORS_ORIGINS` | Backend | CORS 허용 프론트엔드 도메인 | `http://localhost:3000,<https://volumeal.io`\> | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | 클라이언트 호출 API 게이트웨이 | `http://localhost:8000/api/v1` | Yes |

### **13.2 Dockerfile 사양 (`backend/Dockerfile`)**

랩실 GPU 의존성을 제거하고, 가벼운 컨테이너 환경에서 ONNX Runtime CPU 멀티스레딩 추론을 구동하기 위한 Multi-stage 빌드 명세입니다.

Dockerfile

\# Stage 1: Build & Dependencies installation

FROM python:3.10-slim AS builder

&nbsp;

ENV PYTHONDONTWRITEBYTECODE=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONUNBUFFERED=1

&nbsp;

RUN apt-get update && apt-get install \-y \--no-install-recommends \\

&nbsp;&nbsp;&nbsp;&nbsp;build-essential \\

&nbsp;&nbsp;&nbsp;&nbsp;curl \\

&nbsp;&nbsp;&nbsp;&nbsp;&& rm \-rf /var/lib/apt/lists/\*

&nbsp;

WORKDIR /install

COPY requirements.txt .

RUN pip install \--no-cache-dir \--prefix=/install/deps \-r requirements.txt

&nbsp;

\# Stage 2: Minimal Runtime Environment

FROM python:3.10-slim AS runner

&nbsp;

ENV PYTHONDONTWRITEBYTECODE=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONUNBUFFERED=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PATH="/install/deps/bin:$PATH" \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONPATH="/install/deps/lib/python3.10/site-packages:$PYTHONPATH" \\

&nbsp;&nbsp;&nbsp;&nbsp;OMP\_NUM\_THREADS=4 \\

&nbsp;&nbsp;&nbsp;&nbsp;MKL\_NUM\_THREADS=4

&nbsp;

\# Open3D 및 OpenCV 헤드리스 종속 라이브러리 설치

RUN apt-get update && apt-get install \-y \--no-install-recommends \\

&nbsp;&nbsp;&nbsp;&nbsp;libgl1 \\

&nbsp;&nbsp;&nbsp;&nbsp;libglib2.0-0 \\

&nbsp;&nbsp;&nbsp;&nbsp;libgomp1 \\

&nbsp;&nbsp;&nbsp;&nbsp;&& rm \-rf /var/lib/apt/lists/\*

&nbsp;

WORKDIR /app

&nbsp;

COPY \--from=builder /install/deps /install/deps

COPY . .

&nbsp;

\# 보안 강화를 위한 Non-root 실행 유저 생성

RUN useradd \-u 1001 appuser && chown \-R appuser:appuser /app

USER appuser

&nbsp;

EXPOSE 8000

&nbsp;

CMD \["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--lifespan", "on"\]

&nbsp;

### **13.3 Docker Compose 구성 스펙 (`docker-compose.yml`)**

YAML

version: '3.8'

&nbsp;

services:

&nbsp;&nbsp;db:

&nbsp;&nbsp;&nbsp;&nbsp;image: postgres:15-alpine

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-postgres

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_USER: voluuser

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_PASSWORD: volupassword

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_DB: volumeal

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "5432:5432"

&nbsp;&nbsp;&nbsp;&nbsp;volumes:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- pgdata:/var/lib/postgresql/data

&nbsp;&nbsp;&nbsp;&nbsp;healthcheck:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;test: \["CMD-SHELL", "pg\_isready \-U voluuser \-d volumeal"\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;interval: 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;timeout: 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;retries: 5

&nbsp;

&nbsp;&nbsp;backend:

&nbsp;&nbsp;&nbsp;&nbsp;build:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;context: ./backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dockerfile: Dockerfile

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-backend

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;depends\_on:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;db:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;condition: service\_healthy

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ENV=development

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- PORT=8000

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- DATABASE\_URL=postgresql+asyncpg://voluuser:volupassword@db:5432/volumeal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- JWT\_SECRET\_KEY=e83a9f7a6b2c4d5e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- JWT\_ALGORITHM=HS256

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ONNX\_DEPTH\_MODEL\_PATH=/app/app/ml/weights/depth\_anything\_v2\_vits.onnx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ONNX\_SEG\_MODEL\_PATH=/app/app/ml/weights/yolov8s\_seg.onnx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- CORS\_ORIGINS=http://localhost:3000

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "8000:8000"

&nbsp;&nbsp;&nbsp;&nbsp;volumes:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ./backend/app/ml/weights:/app/app/ml/weights:ro

&nbsp;

&nbsp;&nbsp;frontend:

&nbsp;&nbsp;&nbsp;&nbsp;build:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;context: ./frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dockerfile: Dockerfile

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-frontend

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;depends\_on:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- backend

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- NEXT\_PUBLIC\_API\_BASE\_URL=http://localhost:8000/api/v1

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "3000:3000"

&nbsp;

volumes:

&nbsp;&nbsp;pgdata:

&nbsp;

### **13.4 CI/CD 배포 파이프라인 (.github/workflows/ci-cd.yml)**

YAML

name: VoluMeal-Align CI/CD Pipeline

&nbsp;

on:

&nbsp;&nbsp;push:

&nbsp;&nbsp;&nbsp;&nbsp;branches: \[ main, develop \]

&nbsp;&nbsp;pull\_request:

&nbsp;&nbsp;&nbsp;&nbsp;branches: \[ main \]

&nbsp;

jobs:

&nbsp;&nbsp;backend-lint-and-test:

&nbsp;&nbsp;&nbsp;&nbsp;runs-on: ubuntu-22.04

&nbsp;&nbsp;&nbsp;&nbsp;services:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;postgres:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;image: postgres:15-alpine

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_USER: voluuser

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_PASSWORD: volupassword

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_DB: volumeal\_test

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- 5432:5432

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;options: \>-

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-cmd pg\_isready

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-interval 10s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-timeout 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-retries 5

&nbsp;&nbsp;&nbsp;&nbsp;steps:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- uses: actions/checkout@v4

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Set up Python 3.10

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;uses: actions/setup-python@v5

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;python-version: "3.10"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache: "pip"

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Install Dependencies

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install \--upgrade pip

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install \-r requirements.txt

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install pytest pytest-asyncio flake8 mypy httpx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Run Linting

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;flake8 app/ \--max-line-length=120 \--exclude=migrations/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Run Backend Tests

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DATABASE\_URL: postgresql+asyncpg://voluuser:volupassword@localhost:5432/volumeal\_test

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JWT\_SECRET\_KEY: test\_secret\_key\_1234567890\_test\_secret\_key\_1234567890

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JWT\_ALGORITHM: HS256

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PYTHONPATH=. pytest tests/ \-v

&nbsp;&nbsp;frontend-check:

&nbsp;&nbsp;&nbsp;&nbsp;runs-on: ubuntu-22.04

&nbsp;&nbsp;&nbsp;&nbsp;steps:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- uses: actions/checkout@v4

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Set up Node.js 18

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;uses: actions/setup-node@v4

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;node-version: 18

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache: "npm"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache-dependency-path: frontend/package-lock.json

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Install Frontend Dependencies

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm ci

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Type Check & Build

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm run type-check

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm run build

&nbsp;

## **14\. Security Requirements**

### **14.1 OWASP Top 10 대응 설정치**

\[클라이언트 요청 수신\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

1\. 업로드 검증 (Magic Byte Header Check) ──\> 위조 바이너리 즉시 차단 (400)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

2\. Rate Limiting (SlowAPI / IP 기준 검사) ──\> 무차별 요청 차단 (429)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

3\. SQL Injection 방지 (SQLAlchemy 2.0 ORM) ──\> Parameterized Binding 강제

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

4\. 응답 전송: OWASP 보안 헤더 주입 ──\> CSP, HSTS, X-Content-Type-Options

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

\[브라우저 렌더링: React JSX Auto-Escaping \+ DOMPurify (XSS 차단)\]

&nbsp;

* **SQL Injection 방어**: ORM(`SQLAlchemy 2.0`) 및 명시적 파라미터 바인딩 방식을 100% 강제합니다. 문자열 병합(`f"SELECT ... {input}"`)을 사용한 원시 쿼리 유입을 CI의 정적 분석 린터로 사전 차단합니다.  
* **Cross-Site Scripting (XSS) 방어**: Next.js React JSX의 Contextual Auto-Escaping을 유지하며, 임의의 HTML 삽입(`dangerouslySetInnerHTML`) 사용을 금지합니다. 외부 텍스트(식품 영양 정보, 약제 가이드) 렌더링 시 클라이언트 DOMPurify 정화 처리를 적용합니다.  
* **Cross-Site Request Forgery (CSRF) 방어**: 세션 토큰 쿠키에 `SameSite=Strict`, `Secure`, `HttpOnly` 속성을 강제하여 서드파티 사이트에서의 크로스 사이트 요청 전송을 원천 차단합니다.  
* **CORS 설정**: 프로덕션 배포 시 `allow_origins`에 정밀 허용 도메인(`https://volumeal.io`)만 명시하고 와일드카드() 지정을 엄격히 금지합니다.

### **14.2 Rate Limiting 및 무차별 대입(Brute Force) 방어 규칙**

* **FastAPI SlowAPI 적용**:  
  * `POST /api/v1/auth/login`: 동일 IP 및 사용자 계정 기준 **분당 5회** 초과 시 `429 Too Many Requests`를 반환하고 해당 계정에 대해 15분간 로그인 잠금을 적용합니다.  
  * `POST /api/v1/vision/estimate`: CPU 리소스 고갈 방지를 위해 인증된 사용자 토큰 기준 **분당 20회**로 요청을 제한합니다.  
* **파일 업로드 버퍼 제한**: 멀티파트 파싱 시 메모리 버퍼 한도를 10MB로 설정하여 대용량 파일 전송을 통한 DoS 공격을 차단합니다.

## **15\. Assumptions & Risks**

### **15.1 \[Assumption\] (기술적 가정 및 영향도)**

1. **\[ASM-001\] 모바일 브라우저 EXIF 초점거리 부재 시 표준 화각 대체**:  
   * *가정*: 모바일 OS 보안 정책 또는 압축 전송으로 인해 EXIF 메타데이터가 손실된 경우, 스마트폰 기본 광각 카메라 기준값($f=26\\text{mm}$, 수평 화각 약 $68^\\circ$)을 카메라 내부 행렬 $K$로 기본 적용합니다.  
   * *영향도*: 2배/3배 망원 줌으로 촬영된 사진의 경우 3D 역투영 스케일에서 15\~20%의 수축 오차가 발생할 수 있습니다. 시스템은 응답 객체에 `is_calibrated: false` 플래그를 설정하여 UI에 "표준 화각 기준 추정치" 경고를 노출합니다.  
2. **\[ASM-002\] 3차원 바닥면 밀착 및 닫힌 표면(Closed Surface) 가정**:  
   * *가정*: 단안 카메라 특성상 음식 밑면과 그릇 바닥 사이의 비가시 영역을 관측할 수 없으므로, 음식 객체는 RANSAC으로 추정된 바닥 평면 위에 틈새 없이 놓여 있는 닫힌 체적으로 간주합니다.  
   * *영향도*: 국물에 반쯤 떠 있는 음식이나 공중에 띄워진 식기 구조에서는 체적이 과대 추정될 수 있으며, 이는 국물류 마스크 면적 제외 계수 보정으로 완화합니다.

### **15.2 \[Decision Required\] (개발 착수 전 결정 완료 항목)**

1. **\[DEC-001\] 랩실 GPU와 배포 서빙 환경의 분리 정책 확정**:  
   * *확정 내용*: 랩실 RTX 5090은 모델 학습 및 `model.onnx` 파일 반출용으로만 1\~2시간 한정 구동 후 종료합니다. 배포 및 심사 시연은 개인 노트북 CPU(또는 독립 클라우드)에서 ONNX Runtime CPU로 구동하여 연구실 전산망 보안 위반 및 자원 점유 리스크를 원천 차단합니다.  
2. **\[DEC-002\] 약제 식별 입력 경로 우선순위 정책**:  
   * *확정 내용*: 식탁 위 알약/약봉투의 100% 비전 자동 검출(Visual Grounding) 실패 가능성에 대비하여, '사용자 등록 처방약 프로필'을 1순위 베이스라인으로 삼고 식탁 위 비전 검출 결과를 결합하는 하이브리드 판정 정책을 채택합니다.

### **15.3 식별된 주요 기술 리스크 및 완화 방안 (Risk & Mitigation Plan)**

| Risk ID | 위험 요인 | 발생 확률 | 영향도 | 완화 방안 (Mitigation Strategy) |
| ----- | ----- | ----- | ----- | ----- |
| **RSK-001** | **RANSAC 바닥 평면 추정 실패** |  |  |  |

(식기 테두리 차폐 또는 테이블 패턴 노이즈로 인라이어 40% 미달) | 중 | 상 | 식기 테두리 픽셀의 깊이 최솟값(Min Depth)과 그릇 검출 마스크의 기하학적 형태를 결합한 원통형/타원체 체적 근사 수식($V \\approx \\frac{2}{3} \\pi r^2 h$)으로 즉각 Fallback 수행. |  
&nbsp;| **RSK-002** | **CPU 서빙 환경에서 추론 지연 시간 급증** | 중 | 중 | Depth Anything v2의 인코더 백본을 `vits`(Small, 약 2,500만 파라미터)로 고정하고, ONNX OMP 스레드를 4개로 고정하여 단일 이미지 450ms 이내 처리 보장. |  
&nbsp;| **RSK-003** | **Three.js 모바일 브라우저 WebGL 메모리 누수** | 중 | 상 | 컴포넌트 언마운트(`useEffect` 클린업) 시 캔버스 내 지오메트리(`geometry.dispose()`) 및 재질(`material.dispose()`)을 명시적으로 해제하고 최대 점군 수를 5,000개로 강제 제한. |  
&nbsp;| **RSK-004** | **심사 당일 현장 네트워크 불안정 및 지연** | 중 | 치명 | 발표용 3대 시나리오(와파린-시금치, 스타틴-자몽, 갑상선약-우유)에 대한 분석 결과 JSON 및 3D 점군 데이터를 클라이언트 로컬 캐시(`/demo-presets`)로 탑재하여 오프라인 환경에서도 시연 가능하도록 보장. |

## **16\. Agent Instruction Configuration**

AI 코딩 도구(Cursor, Claude Code, Devin 등)가 프로젝트 루트 컨텍스트에서 직접 로드하여 개발 표준과 아키텍처 원칙을 준수하도록 강제하는 인스트럭션 파일입니다.

### **16.1 `.cursorrules` / `CLAUDE.md`**

Markdown

\# VoluMeal-Align AI Coding Agent Ruleset

&nbsp;

\#\# Core Architecture Principles

\- You are implementing VoluMeal-Align, an enterprise-grade monocular 3D meal volume estimation & drug interaction engine.

\- Always maintain 1:1 traceability to the Functional Requirements (FR-001 to FR-007).

\- Architecture Rule: Model training occurs offline on a lab RTX 5090 GPU, exporting standalone ONNX weights (\`model.onnx\`). The serving backend runs independently on ONNX Runtime CPU. Never write code that assumes an active GPU or lab network connection during serving.

\- No speculative code, no incomplete stubs (\`// TODO\`, \`// ...생략\`), and no unhandled exceptions.

&nbsp;

\#\# Tech Stack & Language Conventions

\- Backend: Python 3.10+, FastAPI 0.111+, SQLAlchemy 2.0 (Async), Pydantic v2, ONNX Runtime 1.18+, Open3D 0.18+.

&nbsp;&nbsp;\- All DB queries must use \`select(...)\` syntax with \`AsyncSession\`. Never use legacy Query API.

&nbsp;&nbsp;\- Pydantic models must use \`model\_config \= ConfigDict(from\_attributes=True)\` for ORM compatibility.

&nbsp;&nbsp;\- Point cloud and numerical arrays must be vectorized using NumPy or Open3D. Never use Python \`for\` loops over image pixels.

&nbsp;&nbsp;\- Image decoding must happen in-memory via \`io.BytesIO\`. Do not persist uploaded images to the local disk.

\- Frontend: Next.js 14.2+ (App Router), TypeScript 5.4+ (Strict Mode), Tailwind CSS, Three.js (@react-three/fiber).

&nbsp;&nbsp;\- Never use the \`any\` type in TypeScript. Use shared types defined in \`src/types/api.ts\`.

&nbsp;&nbsp;\- All client forms and payloads must validate through Zod schemas defined in \`src/schemas/api.ts\`.

&nbsp;&nbsp;\- Visual 3D objects must strictly implement WebGL cleanup (\`dispose()\` geometries and materials on unmount).

&nbsp;

\#\# Directory Boundaries & Responsibilities

\- \`training/\`: Contains offline training and ONNX export scripts for the lab RTX 5090 machine.

\- \`backend/app/ml/\`: Houses ONNX Runtime wrappers and geometry integration algorithms. No HTTP dependencies here.

\- \`backend/app/services/\`: Orchestrates vision pipelines, DB transactions, and domain business rules.

\- \`backend/app/api/v1/endpoints/\`: Thin controllers. Only validate input DTOs, invoke services, and return standard responses.

\- \`frontend/src/components/viewer3d/\`: Three.js Canvas and WebGL components. Must include \`'use client'\`.

\- \`frontend/src/stores/\`: Zustand store (\`useMealStore.ts\`) for synchronizing 3D viewer state and nutrition report data.

&nbsp;

\#\# Error Handling Standards

\- Always raise custom domain exceptions inheriting from \`AppException\` in \`backend/app/core/exceptions.py\`.

\- Every API error response must strictly adhere to the \`StandardErrorResponse\` schema with appropriate \`code\`, \`message\`, and \`timestamp\`.

\- Database operations must be wrapped in transactions that automatically roll back on failure.

&nbsp;

\#\# Critical Verification Commands

\- Backend Lint & Type Check: \`flake8 app/ && mypy app/\`

\- Backend Unit & Integration Tests: \`pytest tests/ \-v\`

\- Frontend Type Check & Build: \`npm run type-check && npm run build\`

&nbsp;

이로써 **VoluMeal-Align** 프로젝트에 대한 3단계 분할 기술 구현 명세서(Technical Specification)의 모든 섹션(섹션 1\~16) 출력이 완결되었습니다. 추가 세부 모듈의 단위 구현 코드나 스크립트가 필요한 경우 요청하십시오.

## **17. FR-004 정정 부록: foodId 기반 변환 계층**

본 부록은 FR-004의 기존 “DINOv2 패치 벡터와 음식명/영양 DB 직접 검색” 표현을 대체합니다.

1. 음식 마스크 크롭을 임베딩 모델에 입력합니다.
2. 임베딩은 음식명이 아니라 라벨된 기준 음식 이미지 임베딩과 코사인 비교합니다.
3. 검색기는 `foodId`, Top-3 후보와 점수를 반환합니다.
4. `foodId`로 분리된 카탈로그, 밀도 프로필, 영양 프로필을 조인합니다.
5. `무게(g) = 부피(cm³) × 밀도(g/cm³)`로 계산합니다.
6. `섭취 영양소 = 기준 영양소 × 추정 무게 / 기준 중량`으로 계산합니다.

자동 확정 조건은 Top-1 점수 0.80 이상이면서 Top-1과 Top-2 점수 차이가 0.10 이상인 경우입니다.
조건을 충족하지 못하면 `requiresConfirmation=true`와 Top-3 후보를 반환하며, 사용자 확인 전
분석 결과와 복약 경고를 영구 저장하지 않습니다.

카메라 EXIF 기본 26mm는 미보정 추정값에만 사용합니다. 정확도 수용 검증은 크기를 아는 마커 또는
동등한 기준 물체로 깊이 스케일을 보정한 뒤 수행해야 하며, 응답의 `isCalibrated`는 이 보정의
실제 적용 여부를 나타냅니다. 깊이 스케일 보정이 없는 결과는 정량 정확도 달성 근거로 사용하지 않습니다.

## **18. 사용자 보정 및 미확인 음식 처리 변경사항**

현재 구현에서는 음식 인식 결과를 항상 자동 확정하지 않습니다. Top-1 점수와 후보 간 차이가 자동 확정 기준에 미달하면 `requiresConfirmation=true`와 함께 Top-3 후보를 반환합니다. 각 후보에는 현재 부피 기준의 밀도, 중량, 칼로리, 탄수화물, 단백질, 지방 및 나트륨 값이 포함됩니다.

프론트엔드는 후보를 버튼으로 표시하며 사용자가 선택한 후보로 음식명·밀도·영양값·총합을 갱신합니다. 사용자가 중량을 수정하면 기존 중량 대비 비율로 영양값과 총합을 다시 계산합니다. 후보 선택과 중량 보정은 현재 클라이언트 임시 상태이며, 사용자 보정 결과를 서버에 영구 저장하는 별도 확정 API는 후속 요구사항입니다.

음식 또는 약제가 검출되지 않은 경우에는 표준값으로 대체하지 않고 `ERR_ZERO_OBJECT_DETECTED`를 반환합니다. 클라이언트는 일반 오류 대신 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영하라는 안내를 표시합니다.

&nbsp;
=======
## **해커톤(AI Championship)**

# **Technical Specification: VoluMeal-Align \- Turn 1**

## **1\. System Overview**

### **1.1 프로젝트 목적 및 해결 과제**

* **수기 무게/인분수 입력 병목 및 2D 영양 오차 해결**: 2D 사진의 평면적 한계(깊이 정보 부재로 인한 30\~50%의 칼로리 오차)를 단안 메트릭 깊이 추정(Metric Depth Estimation)과 RANSAC 기반 3차원 기하학적 수치 적분으로 해결합니다.  
* **실시간 식단-복약 상호작용 충돌 방지**: 식탁 위에 놓인 처방약(알약, PTP 포장, 약봉투)과 음식 간의 대사 간섭 위험(와파린-비타민K, 스타틴-자몽, 갑상선 호르몬제-고칼슘)을 비전 임베딩과 식약처 금기 DB 기반 룰 엔진으로 감지하여 즉각적인 경고를 발출합니다.

### **1.2 핵심 기능 요약**

* **FR-001**: 단안 RGB 이미지 입력 시 Zero-shot Metric Depth 추정을 통한 절대 깊이 맵 생성  
* **FR-002**: 식판, 음식, 식기 및 복용 약제 인스턴스 세그멘테이션 마스크 추출  
* **FR-003**: 2D-to-3D 역투영 및 RANSAC 바닥면 피팅 기반 부피($V, \\text{cm}^3$) 수치 적분  
* **FR-004**: DINOv2 패치 임베딩 검색 기반 식품 밀도($\\rho$) 매핑 및 최종 무게/영양소(칼로리/탄단지) 산출  
* **FR-005**: 시각 접지(Visual Grounding) 및 식약처 DB 매핑 기반 약제-식품 위험 상호작용 판별  
* **FR-006**: Three.js 캔버스 기반 3D 바운딩 볼륨 및 다운샘플링 포인트 클라우드 실시간 렌더링  
* **FR-007**: 식단 영양소 분석 결과 및 복약 주의사항 리포트 저장 및 이력 조회
* **FR-008**: 식품 인식 불확실성에 대한 사용자 후보 확정 및 중량 보정

### **1.3 아키텍처 패턴 및 선정 이유**

* **선정 패턴**: **Decoupled Training & Inference with Modular Monolith**  
* **선정 이유**:  
  1. **물리적 환경 격리**: 랩실 RTX 5090 환경에서는 모델 학습 및 ONNX/TensorRT 파일 추출만 수행하고 즉시 세션을 종료하여, 학내 전산망 보안 이슈(외부 터널링 차단) 및 다른 연구원과의 자원 충돌을 방지합니다.  
  2. **독립 배포 경량화**: 추출된 가중치 모델을 ONNX Runtime CPU 멀티스레딩 최적화로 서빙하여, 고가의 상시 GPU 인프라 비용 없이 개인 노트북이나 저비용 클라우드에서도 400ms 내외의 준실시간 추론 속도를 확보합니다.

### **1.4 주요 시스템 구성요소 관계도 (Mermaid Component Diagram)**

코드 스니펫

graph TB

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Offline\_Training \[랩실 환경: Offline Training Machine \- RTX 5090\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TrainDataset\[(Nutrition5k & KFDA DB)\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Trainer\[Model Fine-tuner: Depth Anything v2 \+ DINOv2\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Exporter\[ONNX / TensorRT Exporter\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TrainDataset \--\> Trainer

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Trainer \--\> Exporter

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Exporter \--\>|가중치 파일 반출: model.onnx| ArtifactStorage\[Local / Cloud Model Storage\]

&nbsp;&nbsp;&nbsp;&nbsp;end


&nbsp;&nbsp;&nbsp;&nbsp;subgraph Client\_App \[프론트엔드: Next.js 14 App Router\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Viewfinder\[Camera Viewfinder & EXIF Parser\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ThreeViewer\[Three.js PointCloud & BBox Canvas\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ZustandStore\[Client State Store\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Serving\_Server \[독립 서빙 환경: FastAPI Backend \- CPU / Local / Cloud\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;APIRouter\[Async REST API Router\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator\[Vision Pipeline Orchestrator\]

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;subgraph Inference\_Engine \[ONNX Runtime CPU Engine\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DepthWorker\[Depth Anything v2 ONNX INT8/FP32\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SegWorker\[YOLOv8-Seg ONNX\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PatchWorker\[DINOv2 Feature Extractor\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;subgraph Geometry\_Core \[C++ / Python Vectorized Core\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BackProjector\[Camera Back-projection\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;RANSACPlane\[Open3D RANSAC Surface Fitter\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Integrator\[NumPy Double Numerical Integrator\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;RuleEngine\[KFDA Drug-Food Interaction Evaluator\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;subgraph Data\_Persistence \[데이터베이스: PostgreSQL 15\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Postgres\[(PostgreSQL: Users, Meals, Drugs, Warnings)\]

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;ArtifactStorage \-.-\>|배포 시 가중치 로드| Inference\_Engine

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Viewfinder \--\>|1. Image Binary \+ EXIF| APIRouter

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\> PipelineOrchestrator

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> DepthWorker

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> SegWorker

&nbsp;&nbsp;&nbsp;&nbsp;PipelineOrchestrator \--\> PatchWorker

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;DepthWorker \--\> BackProjector

&nbsp;&nbsp;&nbsp;&nbsp;SegWorker \--\> BackProjector

&nbsp;&nbsp;&nbsp;&nbsp;BackProjector \--\> RANSACPlane

&nbsp;&nbsp;&nbsp;&nbsp;RANSACPlane \--\> Integrator

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;PatchWorker \--\> RuleEngine

&nbsp;&nbsp;&nbsp;&nbsp;Integrator \--\> RuleEngine

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;RuleEngine \--\> APIRouter

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\> Postgres

&nbsp;&nbsp;&nbsp;&nbsp;APIRouter \--\>|JSON \+ Downsampled PointCloud| ThreeViewer

&nbsp;

## **2\. Functional Requirements**

| ID | 기능명 | 설명 | 주요 동작 | 입력값 | 출력값 | 연관 API | 우선순위 |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **FR-001** | 단안 메트릭 깊이 맵 생성 | RGB 이미지 1장으로부터 픽셀별 물리적 절대 거리(m) 산출 | ONNX Runtime 기반 Depth Anything v2 Metric 추론 및 정규화 | `image/jpeg` 파일, 초점거리($f$) 메타데이터 | `Float32` Depth Matrix ($H \\times W$) | `POST /api/v1/vision/estimate` | P0 |
| **FR-002** | 인스턴스 세그멘테이션 | 음식, 식기, 약제(알약/약봉투) 영역 분할 마스크 추출 | YOLOv8-Seg ONNX 추론을 통한 바운딩 박스 및 픽셀 바이너리 마스크 생성 | 정규화된 이미지 텐서 ($1 \\times 3 \\times H \\times W$) | 인스턴스별 마스크, 클래스 라벨, 신뢰도 스코어 | `POST /api/v1/vision/estimate` | P0 |
| **FR-003** | RANSAC 기준면 분리 및 부피 적분 | 바닥 평면을 추정하고 음식 영역에 대한 높이 차분 수치 적분 수행 | 1\) 2D 픽셀을 3D 점군으로 역투영 |  |  |  |  |

2.   
   RANSAC 평면 피팅 ($ax+by+cz+d=0$)

3. 체적 수치 적분 ($V \= \\iint \\Delta z \\,dx\\,dy$) | Depth 맵, 인스턴스 마스크, 카메라 내부 매트릭스 $K$ | 객체별 체적 부피 ($V, \\text{cm}^3$), 오차 경계값 | `POST /api/v1/vision/estimate` | P0 |  
   &nbsp;| **FR-004** | 식품 매크로 영양소 및 중량 산출 | 라벨된 기준 음식 이미지 검색과 `foodId` 조인을 통한 최종 무게/영양소 계산 | 음식 크롭의 DINOv2 패치 벡터를 기준 이미지 임베딩과 코사인 비교 $\\to$ `foodId` 식별 $\\to$ 별도 밀도/영양 프로필 조회 $\\to$ $W \= V \\times \\rho$ 및 칼로리/탄단지 도출 | 음식 크롭 패치, 계산된 체적($V$) | `foodId`, Top-3 후보, 식품 표준명, 중량(g), 열량(kcal), 탄/단/지/나트륨 | `POST /api/v1/vision/estimate` | P0 |  
   &nbsp;| **FR-005** | 복약 시각 접지 및 간섭 위험 판정 | 식탁 위 감지된 약제 또는 등록 처방약과 식단 영양소 간의 대사 충돌 평가 | 1\) 약제 검출 및 식약처 EDI 코드 매칭

4. 상호작용 금기 룰 조회

5. 위험 등급 산출 | 식별된 약제명, 식단 영양소/원재료 리스트 | 위험 등급(DANGER/CAUTION/SAFE), 유발 성분, 권고문 | `POST /api/v1/vision/estimate`, `GET /api/v1/drugs/interactions` | P0 |  
   &nbsp;| **FR-006** | 3D 시각화 페이로드 전송 | 클라이언트 WebGL 렌더링용 경량 포인트 클라우드 및 와이어프레임 생성 | 마스크 내부 점군 Voxel Grid 다운샘플링 (최대 5,000점) 및 바운딩 박스 정점 8개 연산 | 3D 포인트 클라우드 원본 데이터 | `positions` (Float32Array), 3D 바운딩 박스 좌표 | `POST /api/v1/vision/estimate` | P1 |  
   &nbsp;| **FR-007** | 식단 리포트 저장 및 이력 조회 | 분석된 식단, 영양소 총합, 복약 위험 로그 저장 및 기간별 통계 조회 | PostgreSQL 트랜잭션 적재 및 사용자별 날짜 범위 쿼리 | 사용자 인증 토큰, 분석 DTO, 기간 조회 조건 | 일자별 섭취 칼로리 총합, 복약 충돌 이력 리스트 | `GET /api/v1/meals`, `GET /api/v1/meals/{id}` | P1 |

**FR-008 상세**: 자동 분류가 불확실하거나 새로운 음식일 때 클라이언트는 `requiresConfirmation=true`와 함께 반환된 Top-3 후보를 버튼으로 표시한다. 사용자가 후보를 선택하면 해당 후보의 밀도와 영양값으로 음식 결과와 총합을 갱신한다. 사용자가 중량(g)을 수정하면 `수정 중량 / 기존 중량` 비율로 칼로리·탄수화물·단백질·지방·나트륨을 즉시 재계산한다. 이 보정값은 `POST /api/v1/vision/confirm` 저장 성공 전까지 클라이언트 임시 상태다. 확정 API는 선택한 `foodId`, 측정 부피, 보정 중량을 받아 서버 데이터로 영양값과 복약 경고를 재계산한다. 기존 본인 식단은 같은 식별자로 갱신하며 반복 저장으로 기록을 중복 생성하지 않는다.

### **예외 처리 및 유효성 검증 규칙**

1. **\[BR-VAL-001\] 카메라 초점거리(EXIF) 부재 대응**: 클라이언트 이미지에 EXIF 초점거리 메타데이터가 존재하지 않을 경우, 모바일 표준 광각 기준값($f \= 26.0\\text{mm}$)을 기본값으로 강제 주입하며 `is_calibrated: false` 플래그를 응답에 기록합니다.  
2. **\[BR-VAL-002\] 바닥 평면 추정 실패 (RANSAC Outlier 초과)**: 그릇의 테두리 및 테이블 면의 RANSAC 인라이어(Inlier) 비율이 전체의 40% 미만일 경우 `ERR_GEOMETRY_PLANE_NOT_FOUND` 예외를 발생시키고, 클라이언트는 표준 1인분으로 임의 대체하지 않고 재촬영 안내를 제공합니다.  
3. **\[BR-VAL-003\] 최소 체적 유효 범위 제한**: 수치 적분된 부피가 $V \\le 5\\,\\text{cm}^3$ 미만이거나 $V \\ge 5000\\,\\text{cm}^3$ 초과일 경우 노이즈로 판정하고 `ERR_VOLUME_OUT_OF_BOUNDS`를 반환합니다.

4. **[BR-VAL-004] 음식 미검출 대응**: `ERR_ZERO_OBJECT_DETECTED`가 발생하면 클라이언트는 일반 서버 오류 대신 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영하라는 안내를 표시합니다.
5. **[BR-VAL-005] 사용자 중량 보정**: 사용자가 중량을 수정하면 0보다 큰 유한값만 허용하고, 선택된 음식의 기존 영양값에 `수정 중량 / 기존 중량`을 곱해 화면의 음식 영양값과 총합을 즉시 갱신합니다. 이 보정값은 서버 확정 저장 전까지 임시 클라이언트 상태입니다.

## **3\. Non-Functional Requirements**

### **3.1 성능 (Performance)**

* **학습 파이프라인 (랩실 RTX 5090\)**: Depth Anything v2 `vits` 모델의 경량 어댑터 파인튜닝은 32GB VRAM 및 BF16 Tensor Core 가속을 통해 **1.5시간 이내 완료**.  
* **추론 지연 시간 (배포 서빙 환경)**: 4코어 CPU ONNX Runtime 환경 기준, 이미지 수신부터 3D 기하 연산 및 JSON 응답 반환까지 **단일 이미지 450ms 이내 완결** (로컬 노트북 구동 시 350ms).  
* **클라이언트 3D 렌더링**: Next.js Three.js 캔버스에서 Voxel 다운샘플링된 포인트 클라우드(3,000\~5,000점) 렌더링 시 **60 FPS** 유지.

### **3.2 보안 (Security)**

* **랩실 전산망 완전 격리**: 서빙 서버는 랩실 GPU와 완전히 분리되어 작동하며, 학내 네트워크 외부 터널링(ngrok, cloudflared)을 일절 수행하지 않음.  
* **이미지 메모리 생명주기**: 업로드된 바이너리는 디스크에 영구 적재하지 않고 메모리 버퍼(`io.BytesIO`)에서 NumPy 배열 변환 후 즉시 메모리 할당을 해제.  
* **데이터 무결성 및 암호화**: 사용자 복약 데이터는 AES-256-GCM 컬럼 암호화 적용, JWT 토큰은 `HttpOnly`, `SameSite=Strict` 쿠키로 전송.

### **3.3 안정성 및 가용성 (Reliability & Availability)**

* **추론 동시성 제어**: 배포 서버의 CPU/메모리 고갈 방지를 위해 백엔드에 세마포어(`asyncio.Semaphore(5)`)를 설정하여 동시 처리 요청 수를 5건으로 제한.  
* **트랜잭션 격리 수준**: 식단 분석 결과 및 복약 경고 로그 저장은 PostgreSQL `READ COMMITTED` 수준에서 원자적 처리.

### **3.4 반응형 규격 및 웹 접근성 (Usability & Accessibility)**

* **모바일 뷰포트 최적화**: 360px \~ 430px 폭의 모바일 화면(스마트폰 촬영 뷰파인더) 완전 반응형 지원.  
* **WebGL Graceful Fallback**: 하드웨어 가속이 불가능한 기기 접속 시 3D Canvas 대신 2D 정적 바운딩 박스 오버레이로 자동 전환.

## **4\. Tech Stack & Dependencies**

| 영역 | 기술 스택 | 버전 | 목적 | 선택 근거 |
| ----- | ----- | ----- | ----- | ----- |
| **Model Training** | PyTorch / CUDA | 2.3+ / 12.8+ | 랩실 RTX 5090 기반 모델 파인튜닝 | Blackwell 아키텍처 지원, 32GB VRAM을 통한 초고속 BF16 학습 |
| **Model Export** | ONNX / ONNX Runtime | 1.16+ / 1.18+ | 딥러닝 모델 직렬화 및 CPU 최적화 추론 | GPU 의존성을 제거하고 노트북/서버 CPU에서 400ms대 추론 달성 |
| **3D & Geometry** | Open3D / NumPy / SciPy | 0.18+ / 1.26+ | 점군 처리, RANSAC 평면 피팅, 수치 적분 | C++ 바인딩을 통한 고속 벡터화 체적 계산 파이프라인 구축 |
| **Backend Core** | FastAPI / Uvicorn | 0.111+ / 0.30+ | 비동기 고성능 REST API 서빙 | Async IO 네이티브 지원, Pydantic v2 고속 직렬화 |
| **Database & ORM** | PostgreSQL / SQLAlchemy | 15-alpine / 2.0+ (Async) | 영속 데이터 저장 및 비동기 ORM | 정형 데이터 무결성 보장, JSONB를 통한 점군/BBox 유연성 확보 |
| **DB Migration** | Alembic | 1.13+ | 데이터베이스 스키마 버전 관리 | 재현 가능한 데이터베이스 마이그레이션 자동화 |
| **Frontend Core** | Next.js (App Router) | 14.2+ | 클라이언트 웹 앱 및 라우팅 | React Server Components, 카메라 및 대시보드 생산성 극대화 |
| **Language (FE)** | TypeScript | 5.4+ | 정적 타입 계약 보장 | 백엔드 API 계약(Contract)과의 무결성 보장 및 런타임 에러 방지 |
| **3D Rendering** | Three.js / @react-three/fiber | 0.164+ / 8.16+ | 3D 점군, 와이어프레임, 평면 시각화 | WebGL 추상화를 통한 리액트 선언적 3D 뷰어 개발 |
| **State / Fetching** | Zustand / TanStack Query | 4.5+ / 5.35+ | 클라이언트 전역 상태 및 비동기 캐싱 | 가벼운 상태 관리와 API 요청 라이프사이클 분리 |
| **Container & Deploy** | Docker / Docker Compose | 26+ / 2.27+ | 배포 컨테이너라이징 | 로컬 노트북 및 독립 클라우드 어디서든 동일한 실행 환경 보장 |

## **5\. System Architecture**

### **5.1 논리적 컴포넌트 구조**

시스템은 오프라인 학습 영역과 독립 서빙 영역으로 완전히 분리됩니다.

1. **Offline Training & Export Module (랩실 환경)**:  
   * Nutrition5k 데이터셋 기반 Depth Anything v2 Metric 스케일러 파인튜닝  
   * `torch.onnx.export`를 통해 CPU 연산 최적화된 단일 `.onnx` 파일 생성 및 반출  
2. **Serving Application Layer (FastAPI Backend)**:  
   * 파일 유효성 검사 $\\to$ ONNX Runtime CPU 세션 추론 $\\to$ Open3D/NumPy 기하 연산 $\\to$ 식약처 룰 엔진 평가 $\\to$ DB 저장  
3. **Interactive Client Layer (Next.js Frontend)**:  
   * 모바일 카메라 뷰파인더 캡처 $\\to$ EXIF 초점거리 추출 $\\to$ API 통신 $\\to$ Three.js 3D 점군 및 영양 리포트 동시 렌더링

### **5.2 Request-Response 처리 라이프사이클**

\[Client\] 이미지 촬영/업로드 (multipart/form-data)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[FastAPI: POST /api/v1/vision/estimate\]

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;├── 1\. Request Validator: 매직 넘버 검증 (JPEG/PNG), 파일 크기 제한 (10MB)

&nbsp;&nbsp;&nbsp;├── 2\. Image Preprocessing: OpenCV 인메모리 리사이징 (518x518)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[ONNX Runtime CPU Inference Worker\]

&nbsp;&nbsp;&nbsp;├── Task A: Depth Anything v2 ONNX \-\> Float32 Metric Depth Map (m)

&nbsp;&nbsp;&nbsp;└── Task B: YOLOv8-Seg ONNX \-\> Food & Drug Instance Masks

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Geometry Integration Engine (NumPy & Open3D)\]

&nbsp;&nbsp;&nbsp;├── 1\. Back-projection: 2D (u, v, d) \-\> 3D (X, Y, Z) via Camera Matrix K

&nbsp;&nbsp;&nbsp;├── 2\. Plane Segmentation: Table Surface RANSAC (Inliers Distance: 0.01m)

&nbsp;&nbsp;&nbsp;├── 3\. Double Numerical Integration: V \= ∬ (z\_table \- z\_food) dx dy over mask Ω

&nbsp;&nbsp;&nbsp;└── 4\. Downsampling: Voxel Grid Filter (Leaf size: 0.005m)

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Nutrient & Drug Matching Service\]

&nbsp;&nbsp;&nbsp;├── 1\. DINOv2 Feature Cosine Search against Labeled Food Images \-\> foodId

&nbsp;&nbsp;&nbsp;├── 2\. foodId \-\> Density/Nutrient Profiles \-\> W \= V \* ρ \-\> Compute Calories, Carbs, Protein, Fat

&nbsp;&nbsp;&nbsp;└── 3\. Drug Interaction Engine: Drug vs Food Nutrients check against KFDA rules

&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;▼

\[Response & Storage\]

&nbsp;&nbsp;&nbsp;├── 1\. Asynchronously insert records into PostgreSQL (meals, drug\_warnings)

&nbsp;&nbsp;&nbsp;└── 2\. Return Unified JSON: Bounding Boxes, 3D Points, Nutrition, Drug Warnings

&nbsp;

### **5.3 End-to-End 데이터 흐름도 (Mermaid Sequence Diagram)**

코드 스니펫

sequenceDiagram

&nbsp;&nbsp;&nbsp;&nbsp;autonumber

&nbsp;&nbsp;&nbsp;&nbsp;actor User as 사용자 (모바일 브라우저)

&nbsp;&nbsp;&nbsp;&nbsp;participant Client as Next.js 14 Frontend

&nbsp;&nbsp;&nbsp;&nbsp;participant API as FastAPI Serving Engine

&nbsp;&nbsp;&nbsp;&nbsp;participant ONNX as ONNX Runtime (CPU)

&nbsp;&nbsp;&nbsp;&nbsp;participant Geo as Geometry Integrator

&nbsp;&nbsp;&nbsp;&nbsp;participant Rule as Drug-Food Rule Engine

&nbsp;&nbsp;&nbsp;&nbsp;participant DB as PostgreSQL 15

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over User, Client: \[카메라 촬영 및 메타데이터 파싱\]

&nbsp;&nbsp;&nbsp;&nbsp;User-\>\>Client: 음식 및 약제 사진 촬영

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: EXIF 초점거리 파싱 (focal\_length \= 26mm)

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>API: POST /api/v1/vision/estimate (Multipart File \+ Metadata)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate API

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>API: 이미지 매직 넘버 및 포맷 유효성 검증

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate ONNX

&nbsp;&nbsp;&nbsp;&nbsp;par 모델 추론 (ONNX Runtime CPU)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>ONNX: Run Depth Model (Image Tensor)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ONNX--\>\>API: Metric Depth Map (Float32)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>ONNX: Run YOLOv8-Seg (Image Tensor)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ONNX--\>\>API: Instance Masks & BBoxes

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;&nbsp;&nbsp;&nbsp;deactivate ONNX

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate Geo

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>Geo: 3D 기하 연산 요청 (Depth, Masks, K Matrix)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: 3D 점군 역투영 (Back-projection)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: RANSAC 기반 테이블 바닥 평면 분리

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: 음식 마스크 영역 체적 수치 적분 (V cm³)

&nbsp;&nbsp;&nbsp;&nbsp;Geo-\>\>Geo: Three.js용 Voxel Grid 다운샘플링 점군 생성

&nbsp;&nbsp;&nbsp;&nbsp;Geo--\>\>API: Volume(cm³), 3D BBox, 다운샘플링 점군

&nbsp;&nbsp;&nbsp;&nbsp;deactivate Geo

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;activate Rule

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>Rule: 영양소 계산 및 복약 상호작용 검증

&nbsp;&nbsp;&nbsp;&nbsp;Rule-\>\>Rule: 라벨된 기준 이미지 검색으로 foodId 식별 후 밀도(ρ) 및 중량(W=V\*ρ) 도출

&nbsp;&nbsp;&nbsp;&nbsp;Rule-\>\>Rule: 식약처 금기 DB 대조 (와파린-비타민K 등 간섭 판정)

&nbsp;&nbsp;&nbsp;&nbsp;Rule--\>\>API: 영양 프로필 및 위험 경고 리스트

&nbsp;&nbsp;&nbsp;&nbsp;deactivate Rule

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;API-\>\>DB: INSERT meal\_records, meal\_drug\_warnings

&nbsp;&nbsp;&nbsp;&nbsp;API--\>\>Client: 200 OK (MealEstimateResponse JSON)

&nbsp;&nbsp;&nbsp;&nbsp;deactivate API

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: Zustand 스토어 업데이트

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Client: Three.js 캔버스에 3D 점군 및 와이어프레임 렌더링

&nbsp;&nbsp;&nbsp;&nbsp;Client--\>\>User: 칼로리 수치 및 복약 위험 경고 배너 표출

&nbsp;

## **6\. Directory Structure**

프로젝트는 랩실 오프라인 학습 스크립트(`training/`), 독립 배포용 백엔드(`backend/`), 프론트엔드(`frontend/`)의 모노레포 구조로 명확히 분리됩니다.

volumeal-align/

├── .cursorrules                               \# AI 에이전트 개발 표준 룰셋

├── docker-compose.yml                         \# 로컬/서버 배포 오케스트레이션 (DB, Backend, Frontend)

├── README.md

│

├── training/                                  \# \[랩실 RTX 5090 전용\] 모델 학습 및 Export

│   ├── requirements\_train.txt                 \# PyTorch, CUDA 12.8+, Transformers

│   ├── train\_depth\_metric.py                  \# Depth Anything v2 Metric 미세조정 스크립트

│   ├── export\_onnx.py                         \# 학습 완료 후 CPU 최적화 ONNX 모델 추출 스크립트

│   └── data/

│       └── download\_nutrition5k.sh            \# 훈련용 공개 데이터셋 다운로더

│

├── backend/                                   \# \[독립 서빙 환경\] FastAPI Backend

│   ├── Dockerfile                             \# CPU ONNX 최적화 런타임 이미지

│   ├── requirements.txt                       \# fastapi, onnxruntime, open3d, sqlalchemy

│   ├── alembic.ini

│   ├── migrations/                            \# Alembic DB 마이그레이션

│   │   └── env.py

│   └── app/

│       ├── main.py                            \# FastAPI 진입점 및 미들웨어

│       ├── core/

│       │   ├── config.py                      \# Pydantic BaseSettings 환경설정

│       │   ├── database.py                    \# 비동기 SQLAlchemy 세션 설정

│       │   └── exceptions.py                  \# 커스텀 비즈니스 예외 클래스

│       ├── models/                            \# SQLAlchemy 2.0 ORM 엔티티

│       │   ├── user.py                        \# 사용자 엔티티

│       │   ├── meal.py                        \# 식단 분석 마스터 \[FR-007\]

│       │   ├── food\_item.py                   \# 개별 음식 분석 상세 (부피, 중량, 영양) \[FR-003, FR-004\]

│       │   ├── drug.py                        \# 식약처 약제 마스터 \[FR-005\]

│       │   └── interaction\_log.py             \# 복약 위험 감지 이력 \[FR-005\]

│       ├── schemas/                           \# Pydantic v2 DTO

│       │   ├── vision.py                      \# 추론 요청/응답 스키마 \[FR-001\~FR-006\]

│       │   ├── meal.py                        \# 식단 이력 조회 스키마 \[FR-007\]

│       │   └── drug.py                        \# 복약 및 상호작용 스키마 \[FR-005\]

│       ├── api/v1/

│       │   ├── router.py                      \# v1 라우터 통합

│       │   ├── deps.py                        \# 인증 및 세션 의존성 주입

│       │   └── endpoints/

│       │       ├── vision.py                  \# POST /vision/estimate \[FR-001\~FR-006\]

│       │       ├── meals.py                   \# GET /meals, GET /meals/{id} \[FR-007\]

│       │       └── drugs.py                   \# GET /drugs/interactions \[FR-005\]

│       ├── services/                          \# 비즈니스 오케스트레이션 레이어

│       │   ├── vision\_pipeline.py             \# 비전 추론 파이프라인 총괄

│       │   ├── meal\_service.py                \# 식단 데이터 저장 및 통계 연산 \[FR-007\]

│       │   └── drug\_interaction\_service.py    \# 식약처 금기 룰 매칭 \[FR-005\]

│       ├── ml/                                \# 런타임 추론 및 기하 알고리즘

│       │   ├── weights/                       \# 랩실에서 반출된 ONNX 가중치 저장 폴더

│       │   │   ├── depth\_anything\_v2\_vits.onnx

│       │   │   └── yolov8s\_seg.onnx

│       │   ├── onnx\_depth\_estimator.py        \# ONNX Runtime CPU 깊이 추론기 \[FR-001\]

│       │   ├── onnx\_segmentor.py              \# ONNX Runtime 세그멘테이션 추론기 \[FR-002\]

│       │   ├── geometry\_integrator.py         \# Open3D RANSAC 및 수치 적분기 \[FR-003\]

│       │   ├── patch\_embedder.py              \# DINOv2 패치 특징 추출기 \[FR-004\]

│       │   └── camera\_utils.py                \# 역투영 및 내부 파라미터 행렬 계산 \[FR-003\]

│       └── data/

│           ├── food\_density\_table.json        \# 식품별 밀도 및 영양성분 DB \[FR-004\]

│           └── drug\_interactions.json         \# 식약처 의약품-음식 상호작용 규칙 \[FR-005\]

│

└── frontend/                                  \# \[웹 클라이언트\] Next.js 14 App Router

&nbsp;&nbsp;&nbsp;&nbsp;├── package.json

&nbsp;&nbsp;&nbsp;&nbsp;├── tsconfig.json

&nbsp;&nbsp;&nbsp;&nbsp;├── tailwind.config.ts

&nbsp;&nbsp;&nbsp;&nbsp;└── src/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── app/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── layout.tsx                     \# 전역 레이아웃

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── page.tsx                       \# 메인 카메라 촬영/업로드 \[FR-001\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── dashboard/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│       └── page.tsx                   \# 일자별 영양/복약 대시보드 \[FR-007\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── components/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── camera/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── Viewfinder.tsx             \# 실시간 웹캠 캡처 및 오버레이

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── ExifExtractor.ts           \# 초점거리 추출 유틸리티 \[FR-001\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── viewer3d/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── CanvasContainer.tsx        \# Three.js Canvas 래퍼 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── PointCloudViewer.tsx       \# 점군 렌더링 컴포넌트 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── BoundingVolumeMesh.tsx     \# 3D 와이어프레임 렌더러 \[FR-006\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   ├── report/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   ├── NutritionSummary.tsx       \# 칼로리/매크로 영양소 카드 \[FR-004\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   │   └── DrugWarningBanner.tsx      \# 복약 위험 경고 알림 \[FR-005\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── ui/                            \# 공통 UI 컴포넌트 (버튼, 모달)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── hooks/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── useEstimateMeal.ts             \# React Query 기반 분석 요청 훅

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── stores/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── useMealStore.ts                \# 분석 결과 및 3D 뷰포트 상태 관리

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── types/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│   └── api.ts                         \# 백엔드 공유 타입 인터페이스

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── lib/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── apiClient.ts                   \# Axios API 클라이언트 인스턴스

&nbsp;

# **Technical Specification: VoluMeal-Align \- Turn 2**

## **7\. Database Schema & Seed Data**

### **7.1 스키마 정의 테이블**

#### **7.1.1 `users`**

시스템 접근 사용자 계정 및 권한 관리 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 사용자 고유 식별자 |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | None | `BTREE (email)` | 로그인 이메일 계정 |
| `hashed_password` | `VARCHAR(255)` | `NOT NULL` | None | None | Bcrypt 알고리즘 암호화 해시 |
| `name` | `VARCHAR(100)` | `NOT NULL` | None | None | 사용자 성명 또는 식별 닉네임 |
| `role` | `VARCHAR(20)` | `NOT NULL` | `'USER'` | None | RBAC 역할 (`'USER'`, `'ADMIN'`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 계정 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 계정 정보 변경 일시 |

#### **7.1.2 `drugs` \[FR-005\]**

식품의약품안전처 표준 의약품 마스터 데이터 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 의약품 고유 식별자 |
| `kd_code` | `VARCHAR(50)` | `NOT NULL`, `UNIQUE` | None | `BTREE (kd_code)` | 식약처 의약품 표준코드 (EDI) |
| `brand_name` | `VARCHAR(255)` | `NOT NULL` | None | `BTREE (brand_name)` | 공식 제품명 (예: 쿠마딘정 5mg) |
| `ingredient_name` | `VARCHAR(255)` | `NOT NULL` | None | `BTREE (ingredient_name)` | 의약품 주성분명 (예: Warfarin Sodium) |
| `therapeutic_class` | `VARCHAR(100)` | `NOT NULL` | None | None | 약효 분류군 (예: 항응고제) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.3 `user_medications` \[FR-005\]**

사용자가 프로필에 상시 등록하여 복용 중인 처방약 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 복약 등록 고유 식별자 |
| `user_id` | `UUID` | `NOT NULL`, `REFERENCES users(id) ON DELETE CASCADE` | None | `BTREE (user_id)` | 대상 사용자 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE RESTRICT` | None | `BTREE (drug_id)` | 등록 약제 마스터 식별자 |
| `prescribed_dosage_mg` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 1회 처방 복용량 (mg) |
| `is_active` | `BOOLEAN` | `NOT NULL` | `TRUE` | None | 현재 복약 유지 여부 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.4 `drug_food_contraindications` \[FR-005\]**

약제 성분과 식품 영양소/원재료 간의 약리학적 대사 간섭 및 금기 규칙 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 금기 규칙 고유 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE CASCADE` | None | `BTREE (drug_id)` | 연관 약제 식별자 |
| `trigger_nutrient` | `VARCHAR(100)` | `NOT NULL` | None | `BTREE (trigger_nutrient)` | 간섭 유발 성분/식품 (예: `Vitamin_K`, `Grapefruit`) |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | `'CAUTION'` | None | 위험 등급 (`'DANGER'`, `'CAUTION'`, `'INFO'`) |
| `mechanism_desc` | `TEXT` | `NOT NULL` | None | None | 생화학적 대사 간섭 기전 |
| `action_guide` | `TEXT` | `NOT NULL` | None | None | 환자 행동 지침 (예: 섭취 금지, 시간 격차 유지) |
| `source_authority` | `VARCHAR(100)` | `NOT NULL` | `'KFDA'` | None | 근거 데이터 출처 기관 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.5 `meals` \[FR-001, FR-007\]**

단일 식단 촬영 이벤트 및 총 영양소 집계 마스터 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 식단 분석 고유 식별자 |
| `user_id` | `UUID` | `NOT NULL`, `REFERENCES users(id) ON DELETE CASCADE` | None | `BTREE (user_id)` | 분석 소유 사용자 식별자 |
| `image_url` | `VARCHAR(1024)` | `NOT NULL` | None | None | 분석 대상 이미지 스토리지 경로 |
| `focal_length_mm` | `NUMERIC(6,2)` | `NOT NULL` | `26.00` | None | 역투영에 사용된 카메라 초점거리 |
| `is_calibrated` | `BOOLEAN` | `NOT NULL` | `FALSE` | None | EXIF 메타데이터 기반 캘리브레이션 여부 |
| `total_calories_kcal` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 음식 합산 열량 (kcal) |
| `total_carbs_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 탄수화물 합계 (g) |
| `total_protein_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 단백질 합계 (g) |
| `total_fat_g` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 지방 합계 (g) |
| `total_sodium_mg` | `NUMERIC(8,2)` | `NOT NULL` | `0.00` | None | 전체 나트륨 합계 (mg) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | `BTREE (created_at)` | 식단 촬영 및 분석 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.6 `meal_food_items` \[FR-002, FR-003, FR-004\]**

단일 식단 내 분할 검출된 개별 음식 객체, 산출 체적($V$), 밀도($\\rho$), 영양소 상세 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 개별 음식 객체 식별자 |
| `meal_id` | `UUID` | `NOT NULL`, `REFERENCES meals(id) ON DELETE CASCADE` | None | `BTREE (meal_id)` | 연관 식단 마스터 식별자 |
| `food_name` | `VARCHAR(100)` | `NOT NULL` | None | None | 매핑된 표준 식품명 |
| `confidence_score` | `NUMERIC(4,3)` | `NOT NULL` | None | None | DINOv2 임베딩 검색 신뢰도 |
| `volume_cm3` | `NUMERIC(8,2)` | `NOT NULL` | None | None | RANSAC 수치 적분 부피 ($V$) |
| `density_g_cm3` | `NUMERIC(5,4)` | `NOT NULL` | None | None | 적용된 부피 밀도 ($\\rho$) |
| `weight_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 최종 연산 무게 ($W \= V \\times \\rho$) |
| `calories_kcal` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 열량 (kcal) |
| `carbs_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 탄수화물 (g) |
| `protein_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 단백질 (g) |
| `fat_g` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 지방 (g) |
| `sodium_mg` | `NUMERIC(8,2)` | `NOT NULL` | None | None | 산출된 나트륨 (mg) |
| `bbox_2d` | `JSONB` | `NOT NULL` | None | None | 2D 경계 박스 좌표 `[ymin, xmin, ymax, xmax]` |
| `bbox_3d` | `JSONB` | `NOT NULL` | None | None | 3D 바운딩 볼륨 중심, 치수, 8개 정점 좌표 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

#### **7.1.7 `meal_drug_warnings` \[FR-005\]**

식단 분석 중 도출된 약제-식품 간섭 위험 경고 발출 로그 테이블입니다.

| Column | Data Type | Constraints | Default | Index | Description |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | `BTREE (id)` | 경고 로그 식별자 |
| `meal_id` | `UUID` | `NOT NULL`, `REFERENCES meals(id) ON DELETE CASCADE` | None | `BTREE (meal_id)` | 연관 식단 마스터 식별자 |
| `drug_id` | `UUID` | `NOT NULL`, `REFERENCES drugs(id) ON DELETE CASCADE` | None | None | 충돌 발생 약제 식별자 |
| `food_item_id` | `UUID` | `NULLABLE`, `REFERENCES meal_food_items(id) ON DELETE SET NULL` | None | None | 원인 제공 음식 객체 식별자 |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | None | None | 위험 등급 (`'DANGER'`, `'CAUTION'`, `'INFO'`) |
| `detected_via` | `VARCHAR(30)` | `NOT NULL` | `'VISUAL_GROUNDING'` | None | 식별 경로 (`VISUAL_GROUNDING`, `USER_PROFILE`) |
| `warning_title` | `VARCHAR(255)` | `NOT NULL` | None | None | UI 렌더링용 경고 요약 제목 |
| `warning_message` | `TEXT` | `NOT NULL` | None | None | 의학적 간섭 설명 및 조치 가이드 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 생성 일시 |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `CURRENT_TIMESTAMP` | None | 레코드 수정 일시 |

### **7.2 Entity-Relationship Diagram (Mermaid ERD)**

코드 스니펫

erDiagram

&nbsp;&nbsp;&nbsp;&nbsp;users ||--o{ user\_medications : "registers"

&nbsp;&nbsp;&nbsp;&nbsp;users ||--o{ meals : "records"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ user\_medications : "defined\_in"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ drug\_food\_contraindications : "has\_rules"

&nbsp;&nbsp;&nbsp;&nbsp;meals ||--|{ meal\_food\_items : "contains"

&nbsp;&nbsp;&nbsp;&nbsp;meals ||--o{ meal\_drug\_warnings : "triggers"

&nbsp;&nbsp;&nbsp;&nbsp;drugs ||--o{ meal\_drug\_warnings : "involved\_in"

&nbsp;&nbsp;&nbsp;&nbsp;meal\_food\_items ||--o{ meal\_drug\_warnings : "causes"

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;users {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR email UK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR hashed\_password

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR role

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;drugs {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR kd\_code UK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR brand\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR ingredient\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR therapeutic\_class

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;user\_medications {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID user\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC prescribed\_dosage\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BOOLEAN is\_active

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;drug\_food\_contraindications {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR trigger\_nutrient

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR risk\_level

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT mechanism\_desc

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT action\_guide

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR source\_authority

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meals {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID user\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR image\_url

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC focal\_length\_mm

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;BOOLEAN is\_calibrated

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_calories\_kcal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_carbs\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_protein\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_fat\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC total\_sodium\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meal\_food\_items {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID meal\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR food\_name

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC confidence\_score

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC volume\_cm3

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC density\_g\_cm3

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC weight\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC calories\_kcal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC carbs\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC protein\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC fat\_g

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;NUMERIC sodium\_mg

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JSONB bbox\_2d

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JSONB bbox\_3d

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;meal\_drug\_warnings {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID id PK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID meal\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID drug\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;UUID food\_item\_id FK

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR risk\_level

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR detected\_via

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;VARCHAR warning\_title

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TEXT warning\_message

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ created\_at

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;TIMESTAMPTZ updated\_at

&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;

### **7.3 Local Verification Seed Data**

로컬 개발 환경 검증 및 테스트 통과를 위한 표준 마스터 데이터셋 SQL 스크립트입니다. (`backend/app/data/seed.sql`)

SQL

\-- 1\. 기본 테스트 계정 생성 (비밀번호: Password123\! \-\> bcrypt 해시)

INSERT INTO users (id, email, hashed\_password, name, role, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('a0000000-0000-0000-0000-000000000001', 'admin@volumeal.io', '$2b$12$e0M2/qj9h2Y4F5tN2qG6h.W91d4e0e5j8r8z6k4s9v2w1x3y4z5a6', '최고관리자', 'ADMIN', NOW(), NOW()),

&nbsp;&nbsp;('a0000000-0000-0000-0000-000000000002', 'tester@volumeal.io', '$2b$12$e0M2/qj9h2Y4F5tN2qG6h.W91d4e0e5j8r8z6k4s9v2w1x3y4z5a6', '일반테스터', 'USER', NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 2\. 표준 약제 마스터 데이터 등록 \[FR-005\]

INSERT INTO drugs (id, kd\_code, brand\_name, ingredient\_name, therapeutic\_class, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000001', '641800240', '쿠마딘정5밀리그람', '와파린나트륨 (Warfarin Sodium)', '항응고제', NOW(), NOW()),

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000002', '644900110', '리피토정20밀리그람', '아토르바스타틴칼슘삼수화물 (Atorvastatin)', '고지혈증치료제', NOW(), NOW()),

&nbsp;&nbsp;('d0000000-0000-0000-0000-000000000003', '642102550', '씬지로이드정0.1밀리그람', '레보티록신나트륨 (Levothyroxine)', '갑상선호르몬제', NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 3\. 약제-식품 상호작용 위험 매트릭스 등록 \[FR-005\]

INSERT INTO drug\_food\_contraindications (id, drug\_id, trigger\_nutrient, risk\_level, mechanism\_desc, action\_guide, source\_authority, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000001',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000001',

&nbsp;&nbsp;&nbsp;&nbsp;'Vitamin\_K',

&nbsp;&nbsp;&nbsp;&nbsp;'DANGER',

&nbsp;&nbsp;&nbsp;&nbsp;'비타민 K는 간에서 혈액 응고 인자의 생합성을 촉진하여 와파린의 프로트롬빈 시간 연장 작용을 직접적으로 길항 및 저해합니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'시금치, 케일, 브로콜리 등 비타민 K가 다량 함유된 녹색 채소류의 과다 섭취를 엄격히 제한하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;),

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000002',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000002',

&nbsp;&nbsp;&nbsp;&nbsp;'Grapefruit',

&nbsp;&nbsp;&nbsp;&nbsp;'DANGER',

&nbsp;&nbsp;&nbsp;&nbsp;'자몽의 푸라노쿠마린(Furanocoumarin) 성분이 소장 내 대사 효소 CYP3A4를 비가역적으로 억제하여 스타틴 혈중 농도를 급증시키고 횡문근융해증 유발 위험을 높입니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'아토르바스타틴 복용 기간 동안 자몽 생과 및 자몽 주스의 섭취를 금지하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;),

&nbsp;&nbsp;(

&nbsp;&nbsp;&nbsp;&nbsp;'c0000000-0000-0000-0000-000000000003',

&nbsp;&nbsp;&nbsp;&nbsp;'d0000000-0000-0000-0000-000000000003',

&nbsp;&nbsp;&nbsp;&nbsp;'Calcium\_High',

&nbsp;&nbsp;&nbsp;&nbsp;'CAUTION',

&nbsp;&nbsp;&nbsp;&nbsp;'고칼슘 유제품 및 칼슘 보충제가 위장관 내에서 레보티록신과 불용성 킬레이트를 형성하여 약물의 생체이용률을 현저히 떨어뜨립니다.',

&nbsp;&nbsp;&nbsp;&nbsp;'우유, 치즈 등 고칼슘 식품은 갑상선 호르몬제 복용 후 최소 2시간에서 4시간의 간격을 두고 섭취하십시오.',

&nbsp;&nbsp;&nbsp;&nbsp;'식품의약품안전처',

&nbsp;&nbsp;&nbsp;&nbsp;NOW(),

&nbsp;&nbsp;&nbsp;&nbsp;NOW()

&nbsp;&nbsp;)

ON CONFLICT (id) DO NOTHING;

&nbsp;

\-- 4\. 테스터 사용자의 상시 복약 정보 등록

INSERT INTO user\_medications (id, user\_id, drug\_id, prescribed\_dosage\_mg, is\_active, created\_at, updated\_at)

VALUES

&nbsp;&nbsp;('m0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000001', 5.00, TRUE, NOW(), NOW())

ON CONFLICT (id) DO NOTHING;

&nbsp;

## **8\. API Specifications & Type Contracts**

### **8.1 엔드포인트 개요**

| Method | Endpoint | Auth Required | HTTP Status | FR-ID 매핑 | 설명 |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `POST` | `/api/v1/auth/register` | No | `201 Created` | FR-007 | 신규 사용자 계정 등록 |
| `POST` | `/api/v1/auth/login` | No | `200 OK` | FR-007 | 이메일/비밀번호 인증 및 HttpOnly 세션 쿠키 발급 |
| `POST` | `/api/v1/auth/refresh` | No | `200 OK` | FR-007 | Refresh Token 검증을 통한 Access Token 재발급 |
| `POST` | `/api/v1/auth/logout` | Yes | `200 OK` | FR-007 | 인증 쿠키 만료 처리 및 로그아웃 |
| `POST` | `/api/v1/vision/estimate` | Yes | `200 OK` | FR-001 \~ FR-006 | 이미지 업로드 기반 단안 3D 부피 추정 및 복약 간섭 분석 |
| `GET` | `/api/v1/meals` | Yes | `200 OK` | FR-007 | 사용자의 과거 식단 기록 페이지네이션 목록 조회 |
| `GET` | `/api/v1/meals/{meal_id}` | Yes | `200 OK` | FR-007 | 특정 식단의 3D 시각화 데이터 및 영양/복약 상세 조회 |
| `GET` | `/api/v1/drugs/interactions` | Yes | `200 OK` | FR-005 | 특정 약제-식품 상호작용 규칙 사전 조회 |

### **8.2 완전한 TypeScript Type Contracts (`frontend/src/types/api.ts`)**

TypeScript

export type UserRole \= 'USER' | 'ADMIN';

export type RiskLevel \= 'DANGER' | 'CAUTION' | 'INFO';

export type DetectionSource \= 'VISUAL\_GROUNDING' | 'USER\_PROFILE';

&nbsp;

export interface BoundingBox2D {

&nbsp;&nbsp;ymin: number;

&nbsp;&nbsp;xmin: number;

&nbsp;&nbsp;ymax: number;

&nbsp;&nbsp;xmax: number;

}

&nbsp;

export interface Point3D {

&nbsp;&nbsp;x: number;

&nbsp;&nbsp;y: number;

&nbsp;&nbsp;z: number;

}

&nbsp;

export interface BoundingBox3D {

&nbsp;&nbsp;center: Point3D;

&nbsp;&nbsp;dimensions: Point3D;

&nbsp;&nbsp;rotations: Point3D;

&nbsp;&nbsp;vertices: Point3D\[\];

}

&nbsp;

export interface PlaneEquation {

&nbsp;&nbsp;a: number;

&nbsp;&nbsp;b: number;

&nbsp;&nbsp;c: number;

&nbsp;&nbsp;d: number;

}

&nbsp;

export interface FoodItemEstimation {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;foodName: string;

&nbsp;&nbsp;confidenceScore: number;

&nbsp;&nbsp;volumeCm3: number;

&nbsp;&nbsp;densityGCm3: number;

&nbsp;&nbsp;weightG: number;

&nbsp;&nbsp;caloriesKcal: number;

&nbsp;&nbsp;carbsG: number;

&nbsp;&nbsp;proteinG: number;

&nbsp;&nbsp;fatG: number;

&nbsp;&nbsp;sodiumMg: number;

&nbsp;&nbsp;bbox2d: BoundingBox2D;

&nbsp;&nbsp;bbox3d: BoundingBox3D;

}

&nbsp;

export interface DrugInteractionWarning {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;drugBrandName: string;

&nbsp;&nbsp;drugIngredient: string;

&nbsp;&nbsp;triggerNutrientOrFood: string;

&nbsp;&nbsp;riskLevel: RiskLevel;

&nbsp;&nbsp;detectedVia: DetectionSource;

&nbsp;&nbsp;warningTitle: string;

&nbsp;&nbsp;warningMessage: string;

&nbsp;&nbsp;actionGuide: string;

}

&nbsp;

export interface SparsePointCloudPayload {

&nbsp;&nbsp;count: number;

&nbsp;&nbsp;positions: number\[\];

&nbsp;&nbsp;colors: number\[\];

}

&nbsp;

export interface NutritionSummary {

&nbsp;&nbsp;caloriesKcal: number;

&nbsp;&nbsp;carbsG: number;

&nbsp;&nbsp;proteinG: number;

&nbsp;&nbsp;fatG: number;

&nbsp;&nbsp;sodiumMg: number;

}

&nbsp;

export interface MealEstimateResponse {

&nbsp;&nbsp;mealId: string;

&nbsp;&nbsp;imageUrl: string;

&nbsp;&nbsp;isCalibrated: boolean;

&nbsp;&nbsp;focalLengthMm: number;

&nbsp;&nbsp;groundPlane: PlaneEquation;

&nbsp;&nbsp;totalNutrition: NutritionSummary;

&nbsp;&nbsp;foodItems: FoodItemEstimation\[\];

&nbsp;&nbsp;drugWarnings: DrugInteractionWarning\[\];

&nbsp;&nbsp;visualization3d: {

&nbsp;&nbsp;&nbsp;&nbsp;pointCloud: SparsePointCloudPayload;

&nbsp;&nbsp;};

&nbsp;&nbsp;processedAt: string;

&nbsp;&nbsp;inferenceLatencyMs: number;

}

&nbsp;

export interface MealSummaryItem {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;imageUrl: string;

&nbsp;&nbsp;totalCaloriesKcal: number;

&nbsp;&nbsp;foodItemCount: number;

&nbsp;&nbsp;highestRiskLevel: RiskLevel | 'NONE';

&nbsp;&nbsp;createdAt: string;

}

&nbsp;

export interface MealHistoryResponse {

&nbsp;&nbsp;totalCount: number;

&nbsp;&nbsp;page: number;

&nbsp;&nbsp;pageSize: number;

&nbsp;&nbsp;items: MealSummaryItem\[\];

}

&nbsp;

export interface DrugInteractionDetail {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;drugId: string;

&nbsp;&nbsp;kdCode: string;

&nbsp;&nbsp;brandName: string;

&nbsp;&nbsp;ingredientName: string;

&nbsp;&nbsp;triggerNutrient: string;

&nbsp;&nbsp;riskLevel: RiskLevel;

&nbsp;&nbsp;mechanismDesc: string;

&nbsp;&nbsp;actionGuide: string;

&nbsp;&nbsp;sourceAuthority: string;

}

&nbsp;

export interface UserProfileResponse {

&nbsp;&nbsp;id: string;

&nbsp;&nbsp;email: string;

&nbsp;&nbsp;name: string;

&nbsp;&nbsp;role: UserRole;

&nbsp;&nbsp;createdAt: string;

}

&nbsp;

export interface StandardApiResponse\<T\> {

&nbsp;&nbsp;success: true;

&nbsp;&nbsp;data: T;

}

&nbsp;

export interface StandardApiErrorDetail {

&nbsp;&nbsp;field: string;

&nbsp;&nbsp;issue: string;

}

&nbsp;

export interface StandardErrorResponse {

&nbsp;&nbsp;success: false;

&nbsp;&nbsp;error: {

&nbsp;&nbsp;&nbsp;&nbsp;code: string;

&nbsp;&nbsp;&nbsp;&nbsp;message: string;

&nbsp;&nbsp;&nbsp;&nbsp;timestamp: string;

&nbsp;&nbsp;&nbsp;&nbsp;path: string;

&nbsp;&nbsp;&nbsp;&nbsp;details?: StandardApiErrorDetail\[\];

&nbsp;&nbsp;};

}

&nbsp;

### **8.3 Zod Validation Schemas (`frontend/src/schemas/api.ts`)**

TypeScript

import { z } from 'zod';

&nbsp;

export const RegisterRequestSchema \= z.object({

&nbsp;&nbsp;email: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이메일은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.email('올바른 이메일 형식이 아닙니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(255, '이메일은 최대 255자까지 가능합니다.'),

&nbsp;&nbsp;password: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '비밀번호는 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(8, '비밀번호는 최소 8자 이상이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(128, '비밀번호는 최대 128자까지 가능합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[A-Z\]/, '비밀번호에 최소 1개 이상의 대문자가 포함되어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[0-9\]/, '비밀번호에 최소 1개 이상의 숫자가 포함되어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/\[^A-Za-z0-9\]/, '비밀번호에 최소 1개 이상의 특수문자가 포함되어야 합니다.'),

&nbsp;&nbsp;name: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이름은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(2, '이름은 최소 2자 이상이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.max(100, '이름은 최대 100자까지 가능합니다.')

});

&nbsp;

export const LoginRequestSchema \= z.object({

&nbsp;&nbsp;email: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '이메일은 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.email('올바른 이메일 형식이 아닙니다.'),

&nbsp;&nbsp;password: z

&nbsp;&nbsp;&nbsp;&nbsp;.string({ required\_error: '비밀번호는 필수 입력값입니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.min(1, '비밀번호를 입력해야 합니다.')

});

&nbsp;

export const VisionEstimateFormSchema \= z.object({

&nbsp;&nbsp;file: z

&nbsp;&nbsp;&nbsp;&nbsp;.instanceof(File, { message: '업로드할 이미지 파일이 필요합니다.' })

&nbsp;&nbsp;&nbsp;&nbsp;.refine((file) \=\> file.size \<= 10 \* 1024 \* 1024, '이미지 크기는 최대 10MB까지 가능합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.refine(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(file) \=\> \['image/jpeg', 'image/png', 'image/webp'\].includes(file.type),

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'지원 가능한 이미지 형식은 JPEG, PNG, WEBP입니다.'

&nbsp;&nbsp;&nbsp;&nbsp;),

&nbsp;&nbsp;focal\_length\_mm: z

&nbsp;&nbsp;&nbsp;&nbsp;.number()

&nbsp;&nbsp;&nbsp;&nbsp;.positive('초점거리는 양수여야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional()

&nbsp;&nbsp;&nbsp;&nbsp;.default(26.0)

});

&nbsp;

export const MealHistoryQuerySchema \= z.object({

&nbsp;&nbsp;page: z.coerce.number().int().positive().default(1),

&nbsp;&nbsp;pageSize: z.coerce.number().int().min(1).max(50).default(10),

&nbsp;&nbsp;startDate: z

&nbsp;&nbsp;&nbsp;&nbsp;.string()

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/^\\d{4}-\\d{2}-\\d{2}$/, '시작일은 YYYY-MM-DD 형식이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional(),

&nbsp;&nbsp;endDate: z

&nbsp;&nbsp;&nbsp;&nbsp;.string()

&nbsp;&nbsp;&nbsp;&nbsp;.regex(/^\\d{4}-\\d{2}-\\d{2}$/, '종료일은 YYYY-MM-DD 형식이어야 합니다.')

&nbsp;&nbsp;&nbsp;&nbsp;.optional()

});

&nbsp;

export const DrugInteractionQuerySchema \= z.object({

&nbsp;&nbsp;drug\_id: z.string().uuid('유효한 UUID 형식이어야 합니다.').optional(),

&nbsp;&nbsp;kd\_code: z.string().max(50).optional()

});

&nbsp;

export type RegisterRequestDto \= z.infer\<typeof RegisterRequestSchema\>;

export type LoginRequestDto \= z.infer\<typeof LoginRequestSchema\>;

export type VisionEstimateFormDto \= z.infer\<typeof VisionEstimateFormSchema\>;

export type MealHistoryQueryDto \= z.infer\<typeof MealHistoryQuerySchema\>;

export type DrugInteractionQueryDto \= z.infer\<typeof DrugInteractionQuerySchema\>;

&nbsp;

### **8.4 엔드포인트별 상세 입출력 명세**

#### **8.4.1 `POST /api/v1/vision/estimate` \[FR-001 \~ FR-006\]**

* **요청 헤더**: `Authorization: Bearer <AccessToken>` (또는 `access_token` 쿠키), `Content-Type: multipart/form-data`  
* **Request Form Data**:  
  * `file`: 이미지 바이너리 (`image/jpeg`, `image/png`)  
  * `focal_length_mm`: 선택 입력 (부재 시 기본값 `26.0`)  
* **성공 응답 (`200 OK`)**:

JSON

{

&nbsp;&nbsp;"success": true,

&nbsp;&nbsp;"data": {

&nbsp;&nbsp;&nbsp;&nbsp;"mealId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",

&nbsp;&nbsp;&nbsp;&nbsp;"imageUrl": "\<https://storage.volumeal.io/meals/2026/09/09/sample\_meal.jpg\>",

&nbsp;&nbsp;&nbsp;&nbsp;"isCalibrated": true,

&nbsp;&nbsp;&nbsp;&nbsp;"focalLengthMm": 26.0,

&nbsp;&nbsp;&nbsp;&nbsp;"groundPlane": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"a": 0.012,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"b": \-0.998,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"c": 0.054,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"d": 0.452

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"totalNutrition": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"caloriesKcal": 542.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"carbsG": 72.30,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"proteinG": 34.20,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"fatG": 12.80,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"sodiumMg": 640.00

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"foodItems": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "e1a2b3c4-0001-4000-8000-000000000001",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"foodName": "백미밥",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"confidenceScore": 0.942,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"volumeCm3": 210.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"densityGCm3": 1.0500,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"weightG": 221.03,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"caloriesKcal": 320.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"carbsG": 68.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"proteinG": 6.20,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"fatG": 0.80,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"sodiumMg": 4.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox2d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"ymin": 0.45,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"xmin": 0.12,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"ymax": 0.78,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"xmax": 0.45

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox3d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"center": { "x": \-0.15, "y": \-0.05, "z": 0.52 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"dimensions": { "x": 0.12, "y": 0.06, "z": 0.12 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"rotations": { "x": 0.0, "y": 0.0, "z": 0.0 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"vertices": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.08, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.08, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.02, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.02, "z": 0.46 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.08, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.08, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.09, "y": \-0.02, "z": 0.58 },

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{ "x": \-0.21, "y": \-0.02, "z": 0.58 }

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\],

&nbsp;&nbsp;&nbsp;&nbsp;"drugWarnings": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "w1a2b3c4-0001-4000-8000-000000000001",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"drugBrandName": "쿠마딘정5밀리그람",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"drugIngredient": "와파린나트륨 (Warfarin Sodium)",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"triggerNutrientOrFood": "시금치나물 (Vitamin\_K)",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"riskLevel": "DANGER",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"detectedVia": "VISUAL\_GROUNDING",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"warningTitle": "와파린 약효 저하 위험 성분 감지",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"warningMessage": "식탁에서 식별된 처방약(쿠마딘정)과 고비타민K 반찬(시금치나물) 간의 대사 간섭이 발생합니다.",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"actionGuide": "비타민 K 섭취가 급증하면 혈전 예방 작용이 길항됩니다. 섭취량을 최소화하거나 담당 의료진과 상의하십시오."

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\],

&nbsp;&nbsp;&nbsp;&nbsp;"visualization3d": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"pointCloud": {

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"count": 3,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"positions": \[-0.15, \-0.05, 0.52, \-0.14, \-0.04, 0.51, \-0.16, \-0.05, 0.53\],

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"colors": \[0.85, 0.82, 0.78, 0.86, 0.83, 0.79, 0.84, 0.81, 0.77\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;},

&nbsp;&nbsp;&nbsp;&nbsp;"processedAt": "2026-09-09T11:42:00.123Z",

&nbsp;&nbsp;&nbsp;&nbsp;"inferenceLatencyMs": 284

&nbsp;&nbsp;}

}

&nbsp;

#### **8.4.2 `GET /api/v1/meals` \[FR-007\]**

* **요청 파라미터**: `page=1&pageSize=10`  
* **성공 응답 (`200 OK`)**:

JSON

{

&nbsp;&nbsp;"success": true,

&nbsp;&nbsp;"data": {

&nbsp;&nbsp;&nbsp;&nbsp;"totalCount": 42,

&nbsp;&nbsp;&nbsp;&nbsp;"page": 1,

&nbsp;&nbsp;&nbsp;&nbsp;"pageSize": 10,

&nbsp;&nbsp;&nbsp;&nbsp;"items": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"imageUrl": "\<https://storage.volumeal.io/meals/2026/09/09/sample\_meal.jpg\>",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"totalCaloriesKcal": 542.50,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"foodItemCount": 3,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"highestRiskLevel": "DANGER",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"createdAt": "2026-09-09T11:42:00.123Z"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;}

}

&nbsp;

## **9\. Authentication & Authorization**

### **9.1 인증 라이프사이클 (JWT Lifecycle)**

코드 스니펫

sequenceDiagram

&nbsp;&nbsp;&nbsp;&nbsp;autonumber

&nbsp;&nbsp;&nbsp;&nbsp;actor Client as 브라우저 (Next.js 14\)

&nbsp;&nbsp;&nbsp;&nbsp;participant AuthAPI as FastAPI Auth Router

&nbsp;&nbsp;&nbsp;&nbsp;participant Guard as JWT Dependency Guard

&nbsp;&nbsp;&nbsp;&nbsp;participant DB as PostgreSQL 15

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, AuthAPI: 1\. 로그인 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/login (email, password)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>DB: SELECT \* FROM users WHERE email \= :email

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: verify\_password(raw\_password, hashed\_password)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: create\_access\_token(sub=user\_id, role, exp=15m)\<br\>create\_refresh\_token(sub=user\_id, jti, exp=7d)

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (HttpOnly, Secure, SameSite=Strict, Max-Age=900)\<br\>Set-Cookie: refresh\_token (HttpOnly, Secure, SameSite=Strict, Max-Age=604800)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, Guard: 2\. 인가된 요청 및 만료 갱신 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Guard: POST /api/v1/vision/estimate (Cookie 자동 첨부)

&nbsp;&nbsp;&nbsp;&nbsp;alt Access Token 유효

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard-\>\>Guard: decode\_token(access\_token) & verify\_signature

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard--\>\>AuthAPI: Request Proceed (Current UserContext 주입)

&nbsp;&nbsp;&nbsp;&nbsp;else Access Token 만료 (401 Unauthorized)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Guard--\>\>Client: 401 Unauthorized (ERR\_TOKEN\_EXPIRED)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/refresh (refresh\_token Cookie 첨부)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI-\>\>AuthAPI: verify\_token(refresh\_token)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (신규 토큰 갱신)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>Guard: POST /api/v1/vision/estimate (재요청 성공)

&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;Note over Client, AuthAPI: 3\. 로그아웃 단계

&nbsp;&nbsp;&nbsp;&nbsp;Client-\>\>AuthAPI: POST /api/v1/auth/logout

&nbsp;&nbsp;&nbsp;&nbsp;AuthAPI--\>\>Client: 200 OK\<br\>Set-Cookie: access\_token (Max-Age=0)\<br\>Set-Cookie: refresh\_token (Max-Age=0)

&nbsp;

### **9.2 토큰 보관 및 전송 보안 메커니즘**

1. **브라우저 스토리지 차단**: `access_token`과 `refresh_token`은 브라우저의 `localStorage`, `sessionStorage`, 일반 JavaScript 런타임 메모리에 저장하지 않으며 서버 응답 헤더의 `Set-Cookie`를 통해서만 설정됩니다.  
2. **쿠키 보안 플래그 강제**:  
   * `HttpOnly`: XSS 공격 스크립트를 통한 토큰 탈취 원천 차단.  
   * `Secure`: HTTPS 전송 구간에서만 쿠키 전송 허용.  
   * `SameSite=Strict`: 타 사이트로부터 유입되는 Cross-Site 요청에 쿠키 첨부를 전면 차단하여 CSRF 무력화.  
3. **토큰 규격**:  
   * `access_token`: 수명 15분, 서명 알고리즘 `HS256`, 클레임(`sub`: User UUID, `role`: UserRole, `exp`: Timestamp).  
   * `refresh_token`: 수명 7일, 클레임(`sub`: User UUID, `jti`: Session UUID, `exp`: Timestamp).

### **9.3 RBAC 권한 매트릭스 테이블**

| 엔드포인트 경로 | HTTP Method | GUEST (미인증) | USER (일반회원) | ADMIN (관리자) |
| ----- | ----- | ----- | ----- | ----- |
| `/api/v1/auth/register` | `POST` | 허용 | 차단 | 차단 |
| `/api/v1/auth/login` | `POST` | 허용 | 차단 | 차단 |
| `/api/v1/auth/refresh` | `POST` | 허용 | 허용 | 허용 |
| `/api/v1/auth/logout` | `POST` | 차단 | 허용 | 허용 |
| `/api/v1/vision/estimate` | `POST` | 차단 | 허용 | 허용 |
| `/api/v1/meals` | `GET` | 차단 | 본인 데이터 한정 허용 | 전체 허용 |
| `/api/v1/meals/{meal_id}` | `GET` | 차단 | 본인 데이터 한정 허용 | 전체 허용 |
| `/api/v1/drugs/interactions` | `GET` | 차단 | 허용 | 허용 |
| `/api/v1/admin/**` | ALL | 차단 | 차단 | 전체 허용 |

### **9.4 FastAPI 인증 의존성 구현 명세 (`backend/app/api/deps.py`)**

Python

from typing import Annotated

import uuid

from fastapi import Depends, HTTPException, Request, status

from jose import JWTError, jwt

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

&nbsp;

from app.core.config import settings

from app.core.database import get\_db\_session

from app.models.user import User

&nbsp;

async def get\_current\_user(

&nbsp;&nbsp;&nbsp;&nbsp;request: Request,

&nbsp;&nbsp;&nbsp;&nbsp;db: Annotated\[AsyncSession, Depends(get\_db\_session)\]) \-\> User:

&nbsp;&nbsp;&nbsp;&nbsp;token \= request.cookies.get("access\_token")

&nbsp;&nbsp;&nbsp;&nbsp;if not token:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;auth\_header \= request.headers.get("Authorization")

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if auth\_header and auth\_header.startswith("Bearer "):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;token \= auth\_header.split(" ")\[1\]

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;if not token:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_AUTHENTICATION\_REQUIRED", "message": "인증 자격 증명이 누락되었습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;try:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;payload \= jwt.decode(token, settings.JWT\_SECRET\_KEY, algorithms=\[settings.JWT\_ALGORITHM\])

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;user\_id\_str: str \= payload.get("sub")

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if not user\_id\_str:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_INVALID\_TOKEN", "message": "유효하지 않은 토큰 페이로드입니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;user\_id \= uuid.UUID(user\_id\_str)

&nbsp;&nbsp;&nbsp;&nbsp;except (JWTError, ValueError):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_TOKEN\_EXPIRED", "message": "인증 토큰이 만료되었거나 서명이 유효하지 않습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;stmt \= select(User).where(User.id \== user\_id)

&nbsp;&nbsp;&nbsp;&nbsp;result \= await db.execute(stmt)

&nbsp;&nbsp;&nbsp;&nbsp;user \= result.scalar\_one\_or\_none()

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;if not user:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_401\_UNAUTHORIZED,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_USER\_NOT\_FOUND", "message": "토큰에 해당하는 사용자를 찾을 수 없습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;return user

&nbsp;

def require\_role(required\_role: str):

&nbsp;&nbsp;&nbsp;&nbsp;async def role\_checker(current\_user: Annotated\[User, Depends(get\_current\_user)\]) \-\> User:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if current\_user.role \!= required\_role and current\_user.role \!= "ADMIN":

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise HTTPException(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status\_code=status.HTTP\_403\_FORBIDDEN,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detail={"code": "ERR\_ACCESS\_DENIED", "message": "해당 작업에 대한 접근 권한이 없습니다."}

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return current\_user

&nbsp;&nbsp;&nbsp;&nbsp;return role\_checker

&nbsp;

## **10\. Error Handling**

### **10.1 전역 표준 에러 응답 규격**

모든 시스템 실패 응답은 일관된 JSON 객체 구조를 반환합니다.

JSON

{

&nbsp;&nbsp;"success": false,

&nbsp;&nbsp;"error": {

&nbsp;&nbsp;&nbsp;&nbsp;"code": "ERR\_VALIDATION\_FAILED",

&nbsp;&nbsp;&nbsp;&nbsp;"message": "입력 파라미터 유효성 검증에 실패했습니다.",

&nbsp;&nbsp;&nbsp;&nbsp;"timestamp": "2026-09-09T11:51:26.000Z",

&nbsp;&nbsp;&nbsp;&nbsp;"path": "/api/v1/vision/estimate",

&nbsp;&nbsp;&nbsp;&nbsp;"details": \[

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"field": "file",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"issue": "파일 확장자가 지원되지 않는 포맷입니다."

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}

&nbsp;&nbsp;&nbsp;&nbsp;\]

&nbsp;&nbsp;}

}

&nbsp;

TypeScript

export interface StandardErrorResponse {

&nbsp;&nbsp;success: false;

&nbsp;&nbsp;error: {

&nbsp;&nbsp;&nbsp;&nbsp;code: string;

&nbsp;&nbsp;&nbsp;&nbsp;message: string;

&nbsp;&nbsp;&nbsp;&nbsp;timestamp: string;

&nbsp;&nbsp;&nbsp;&nbsp;path: string;

&nbsp;&nbsp;&nbsp;&nbsp;details?: Array\<{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;field: string;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;issue: string;

&nbsp;&nbsp;&nbsp;&nbsp;}\>;

&nbsp;&nbsp;};

}

&nbsp;

### **10.2 시스템 에러 매핑 테이블**

| HTTP Status | Internal Error Code | Error Message | 발생 조건 |
| ----- | ----- | ----- | ----- |
| `400 Bad Request` | `ERR_BAD_REQUEST` | 잘못된 요청 형식입니다. | JSON 역직렬화 실패 또는 필수 파라미터 누락 |
| `400 Bad Request` | `ERR_INVALID_IMAGE_PAYLOAD` | 이미지 매직 넘버 검증에 실패했습니다. | 파일 확장자는 이미지이나 바이너리 헤더 불일치 |
| `400 Bad Request` | `ERR_IMAGE_SIZE_EXCEEDED` | 업로드 파일 크기가 10MB를 초과했습니다. | 업로드 파일 크기 \> 10,485,760 바이트 |
| `401 Unauthorized` | `ERR_AUTHENTICATION_REQUIRED` | 인증 자격 증명이 누락되었습니다. | Auth Cookie 및 Authorization 헤더 미제공 |
| `401 Unauthorized` | `ERR_TOKEN_EXPIRED` | 인증 토큰이 만료되었습니다. | JWT `exp` 타임스탬프 경과 |
| `401 Unauthorized` | `ERR_INVALID_CREDENTIALS` | 이메일 또는 비밀번호가 일치하지 않습니다. | 로그인 시 계정 부재 또는 해시 불일치 |
| `403 Forbidden` | `ERR_ACCESS_DENIED` | 해당 리소스에 접근 권한이 없습니다. | 타 사용자의 Meal ID 상세 조회 시도 |
| `404 Not Found` | `ERR_RESOURCE_NOT_FOUND` | 요청한 리소스를 찾을 수 없습니다. | 조회 대상 `meal_id` 또는 `drug_id` 부재 |
| `422 Unprocessable Entity` | `ERR_GEOMETRY_PLANE_NOT_FOUND` | 테이블 기준 평면 추정에 실패했습니다. | RANSAC 평면 피팅 인라이어 비율 40% 미달 |
| `422 Unprocessable Entity` | `ERR_VOLUME_OUT_OF_BOUNDS` | 연산된 음식 부피가 유효 범위를 벗어났습니다. | 부피 계산치 $V \\le 5\\,\\text{cm}^3$ 또는 $V \\ge 5000\\,\\text{cm}^3$ |
| `422 Unprocessable Entity` | `ERR_ZERO_OBJECT_DETECTED` | 이미지 내 음식 또는 약제가 검출되지 않았습니다. | YOLOv8-Seg 검출 객체 수 \= 0 |
| `429 Too Many Requests` | `ERR_RATE_LIMIT_EXCEEDED` | 단시간 내 너무 많은 요청이 발생했습니다. | API별 할당 Rate Limit 임계치 초과 |
| `500 Internal Server Error` | `ERR_INFERENCE_ENGINE_CRASH` | 비전 추론 런타임 처리 중 장애가 발생했습니다. | ONNX Runtime 프로세스 충돌 또는 모델 연산 에러 |
| `500 Internal Server Error` | `ERR_DATABASE_TRANSACTION` | 데이터베이스 작업 중 오류가 발생했습니다. | SQLAlchemy 비동기 트랜잭션 충돌 및 롤백 |

# **Technical Specification: VoluMeal-Align \- Turn 3**

## **11\. Testing Strategy**

### **11.1 Unit Test (도메인 수치 기하학 및 약리 규칙 검증)**

| Test Suite | 대상 파일 | 검증 시나리오 및 경계 조건 | 기대 결과 | 연관 FR |
| ----- | ----- | ----- | ----- | ----- |
| `test_geometry_plane_ransac` | `app/ml/geometry_integrator.py` | 가상 평면($z \= 0$) 위에 합성 노이즈($\\sigma=0.005\\text{m}$)가 포함된 10,000개 포인트 클라우드 입력 시 RANSAC 표면 방정식($ax+by+cz+d=0$) 추정 | 법선 벡터 각도 오차 $\\le 1.5^\\circ$, 평면 인라이어 비율 $\\ge 90\\%$ | FR-003 |
| `test_volume_numerical_integration` | `app/ml/geometry_integrator.py` | $10\\text{cm} \\times 10\\text{cm} \\times 10\\text{cm}$ 크기의 이상적 직육면체 합성 깊이 맵 ($V \= 1000\\,\\text{cm}^3$) 적분 | 연산 체적 오차율 $\\le 2.5\\%$ ($975 \\le V \\le 1025$) | FR-003 |
| `test_volume_out_of_bounds_rejection` | `app/ml/geometry_integrator.py` | 유효 범위를 벗어난 체적 입력 ($V \= 2.1\\,\\text{cm}^3$ 및 $V \= 6400\\,\\text{cm}^3$) | `VolumeOutOfBoundsException` (HTTP 422 매핑) 발생 | FR-003 |
| `test_drug_interaction_matrix` | `app/services/drug_interaction_service.py` | 1\) 쿠마딘정(와파린) \+ 시금치나물(Vitamin K) |  |  |

2.   
   리피토정(스타틴) \+ 자몽주스(Grapefruit)

3. 씬지로이드(레보티록신) \+ 우유(Calcium)

4. 음성 대조군: 리피토정 \+ 백미밥 | 1\) `DANGER` 등급 경고 반환

5. `DANGER` 등급 경고 반환

6. `CAUTION` 등급 경고 반환

7. `drugWarnings` 빈 배열 반환 | FR-005 |  
   &nbsp;| `test_camera_backprojection` | `app/ml/camera_utils.py` | 초점거리 $f=26\\text{mm}$, 센서 규격 기준 깊이 $Z=0.5\\text{m}$ 지점의 주점 $(c\_x, c\_y)$ 역투영 | $X=0.0, Y=0.0, Z=0.5$ 공간 좌표 정확 도출 | FR-001, FR-003 |

#### **핵심 수치 기하학 및 약리 규칙 단위 테스트 구현 (`backend/tests/unit/test_geometry_and_rules.py`)**

Python

import pytest

import numpy as np

from app.ml.geometry\_integrator import NumericalVolumeIntegrator

from app.services.drug\_interaction\_service import DrugInteractionService

from app.core.exceptions import VolumeOutOfBoundsException

&nbsp;

def test\_ransac\_plane\_fitting\_synthetic():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;np.random.seed(42)

&nbsp;&nbsp;&nbsp;&nbsp;\# z \= 0.5m 평면 상의 5000개 점군 생성

&nbsp;&nbsp;&nbsp;&nbsp;x \= np.random.uniform(-0.3, 0.3, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;y \= np.random.uniform(-0.3, 0.3, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;z \= np.full\_like(x, 0.5) \+ np.random.normal(0, 0.002, 5000\)

&nbsp;&nbsp;&nbsp;&nbsp;points \= np.stack(\[x, y, z\], axis=-1)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;plane\_eq, inlier\_ratio \= integrator.fit\_plane\_ransac(points, distance\_threshold=0.01)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert inlier\_ratio \>= 0.90

&nbsp;&nbsp;&nbsp;&nbsp;\# 평면 방정식 ax \+ by \+ cz \+ d \= 0에서 z축 법선 벡터 c는 1에 수렴해야 함

&nbsp;&nbsp;&nbsp;&nbsp;normal \= np.array(\[plane\_eq\["a"\], plane\_eq\["b"\], plane\_eq\["c"\]\])

&nbsp;&nbsp;&nbsp;&nbsp;normal \= normal / np.linalg.norm(normal)

&nbsp;&nbsp;&nbsp;&nbsp;assert abs(abs(normal\[2\]) \- 1.0) \< 0.05

&nbsp;

def test\_exact\_cube\_numerical\_integration():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;\# 10cm x 10cm 바닥에 높이 5cm인 음식 (부피 500 cm3)

&nbsp;&nbsp;&nbsp;&nbsp;grid\_res \= 0.002  \# 2mm 단위 격자

&nbsp;&nbsp;&nbsp;&nbsp;x \= np.arange(-0.05, 0.05, grid\_res)

&nbsp;&nbsp;&nbsp;&nbsp;y \= np.arange(-0.05, 0.05, grid\_res)

&nbsp;&nbsp;&nbsp;&nbsp;xx, yy \= np.meshgrid(x, y)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;z\_table \= np.full\_like(xx, 0.60) \# 바닥면 거리 0.60m

&nbsp;&nbsp;&nbsp;&nbsp;z\_food \= np.full\_like(xx, 0.55)  \# 음식 상단 거리 0.55m (높이 0.05m \= 5cm)

&nbsp;&nbsp;&nbsp;&nbsp;mask \= np.ones\_like(xx, dtype=bool)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;volume\_cm3 \= integrator.integrate\_height\_difference(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;z\_table=z\_table,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;z\_food=z\_food,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask=mask,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pixel\_area\_m2=grid\_res \* grid\_res

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert pytest.approx(volume\_cm3, rel=0.025) \== 500.0

&nbsp;

def test\_volume\_boundary\_exception():

&nbsp;&nbsp;&nbsp;&nbsp;integrator \= NumericalVolumeIntegrator()

&nbsp;&nbsp;&nbsp;&nbsp;with pytest.raises(VolumeOutOfBoundsException):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;integrator.validate\_volume\_bounds(3.5) \# 5cm3 미만 차단

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;with pytest.raises(VolumeOutOfBoundsException):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;integrator.validate\_volume\_bounds(5500.0) \# 5000cm3 초과 차단

&nbsp;

def test\_drug\_interaction\_rule\_evaluation():

&nbsp;&nbsp;&nbsp;&nbsp;service \= DrugInteractionService()

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;\# 케이스 1: 와파린 \+ 비타민K 위험 판정

&nbsp;&nbsp;&nbsp;&nbsp;warnings \= service.evaluate\_interactions(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detected\_drug\_codes=\["641800240"\], \# 쿠마딘정

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;food\_nutrients=\["Vitamin\_K", "Carbohydrate"\]

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;assert len(warnings) \== 1

&nbsp;&nbsp;&nbsp;&nbsp;assert warnings\[0\].risk\_level \== "DANGER"

&nbsp;&nbsp;&nbsp;&nbsp;assert "와파린" in warnings\[0\].warning\_title

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;\# 케이스 2: 스타틴 \+ 일반 쌀밥 (정상)

&nbsp;&nbsp;&nbsp;&nbsp;safe\_check \= service.evaluate\_interactions(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;detected\_drug\_codes=\["644900110"\], \# 리피토정

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;food\_nutrients=\["Carbohydrate", "Protein"\]

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;&nbsp;&nbsp;&nbsp;assert len(safe\_check) \== 0

&nbsp;

### **11.2 Integration Test (ONNX 서빙 및 DB 트랜잭션 격리 검증)**

* **ONNX 서빙 가상화 및 모델 모킹(Mocking)**:  
  * CI 서버 및 유닛 통합 테스트 환경에서는 대형 모델의 연산 병목을 제거하기 위해 고정된 깊이 맵(Float32 Matrix, 전 영역 0.55m)과 표준 식판 마스크 바이너리 텐서를 반환하는 `MockDepthEstimator`, `MockSegmentor`를 의존성 주입 컨테이너에 바인딩합니다.  
* **DB 세이브포인트 롤백 전략**:  
  * `pytest-asyncio` 환경에서 테스트 세션 시작 시 `AsyncConnection`을 열고 각 테스트 함수마다 중첩 트랜잭션(`begin_nested()`)을 생성하여 테스트가 통과/실패한 직후 무조건 `ROLLBACK` 처리함으로써 DB 격리성을 100% 보장합니다.

#### **통합 테스트 엔드포인트 파이프라인 검증 (`backend/tests/integration/test_vision_endpoint.py`)**

Python

import pytest

from httpx import AsyncClient

import io

from PIL import Image

from app.main import app

from app.api.deps import get\_depth\_estimator, get\_segmentor

&nbsp;

class FakeDepthEstimator:

&nbsp;&nbsp;&nbsp;&nbsp;def infer(self, image\_tensor):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\# 518x518 크기의 0.55m 깊이 맵 반환

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return np.full((518, 518), 0.55, dtype=np.float32)

&nbsp;

class FakeSegmentor:

&nbsp;&nbsp;&nbsp;&nbsp;def infer(self, image\_tensor):

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\# 중앙 영역 100x100 픽셀 마스크 1건 반환

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask \= np.zeros((518, 518), dtype=bool)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;mask\[200:300, 200:300\] \= True

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return \[{

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"label": "백미밥",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"confidence": 0.95,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"mask": mask,

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"bbox2d": \[0.38, 0.38, 0.58, 0.58\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}\]

&nbsp;

@pytest.fixture

def override\_vision\_models():

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides\[get\_depth\_estimator\] \= lambda: FakeDepthEstimator()

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides\[get\_segmentor\] \= lambda: FakeSegmentor()

&nbsp;&nbsp;&nbsp;&nbsp;yield

&nbsp;&nbsp;&nbsp;&nbsp;app.dependency\_overrides.clear()

&nbsp;

@pytest.mark.asyncio

async def test\_vision\_estimate\_full\_pipeline(async\_client: AsyncClient, auth\_cookie: dict, override\_vision\_models):

&nbsp;&nbsp;&nbsp;&nbsp;\# 가상 JPEG 이미지 바이너리 생성

&nbsp;&nbsp;&nbsp;&nbsp;img \= Image.new("RGB", (640, 480), color=(200, 200, 200))

&nbsp;&nbsp;&nbsp;&nbsp;buffer \= io.BytesIO()

&nbsp;&nbsp;&nbsp;&nbsp;img.save(buffer, format="JPEG")

&nbsp;&nbsp;&nbsp;&nbsp;buffer.seek(0)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;response \= await async\_client.post(

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"/api/v1/vision/estimate",

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;files={"file": ("meal.jpg", buffer, "image/jpeg")},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;data={"focal\_length\_mm": 26.0},

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cookies=auth\_cookie

&nbsp;&nbsp;&nbsp;&nbsp;)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;assert response.status\_code \== 200

&nbsp;&nbsp;&nbsp;&nbsp;res\_data \= response.json()

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["success"\] is True

&nbsp;&nbsp;&nbsp;&nbsp;assert "mealId" in res\_data\["data"\]

&nbsp;&nbsp;&nbsp;&nbsp;assert len(res\_data\["data"\]\["foodItems"\]) \== 1

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["data"\]\["foodItems"\]\[0\]\["foodName"\] \== "백미밥"

&nbsp;&nbsp;&nbsp;&nbsp;assert res\_data\["data"\]\["foodItems"\]\[0\]\["volumeCm3"\] \> 0

&nbsp;

### **11.3 End-to-End Test (Playwright 기반 시나리오 명세)**

* **E2E-001 (Happy Path \- 식단 촬영부터 3D 렌더링 및 위험 감지 완결)**:  
  1. 테스터 계정(`tester@volumeal.io`)으로 `/login` 페이지 접속 후 로그인 성공 및 `/` 이동.  
  2. 모바일 뷰파인더 캡처 입력폼에 시금치와 쿠마딘정이 포함된 `test_spinach_warfarin.jpg` 파일 입력.  
  3. 로딩 상태 스피너 노출 확인 후 1.5초 이내 결과 화면 렌더링 검증.  
  4. Three.js Canvas 엘리먼트(`canvas[data-engine="three.js"]`) 로드 및 점군 3D 객체 마운트 확인.  
  5. UI 상단 `DrugWarningBanner`에 `와파린 약효 저하 위험 성분 감지` (배경색: Red-600) 노출 확인.  
  6. 하단 아코디언에서 '시금치나물' 부피($\\text{cm}^3$), 중량($g$), 칼로리가 정확히 바인딩되었는지 확인.  
* **E2E-002 (Failure Path \- 파일 위변조 차단 및 유효성 에러 표출)**:  
  1. `.jpg` 확장자로 속인 임의의 텍스트 파일 `malicious.jpg` 업로드 시도.  
  2. 백엔드 매직 넘버 검증 실패로 `400 Bad Request` (`ERR_INVALID_IMAGE_PAYLOAD`) 발생.  
  3. 클라이언트 토스트 컴포넌트에 "유효한 이미지 형식이 아닙니다." 문구 노출 확인 및 업로드 폼 초기화.  
* **E2E-003 (Failure Path \- 바닥 평면 미검출 시 Graceful Fallback)**:  
  1. 테이블 바닥이 전혀 노출되지 않은 극단적 음식 클로즈업 사진 `no_plane_surface.jpg` 업로드.  
  2. 백엔드 수치 적분기에서 `ERR_GEOMETRY_PLANE_NOT_FOUND` (HTTP 422\) 수신.  
  3. 프론트엔드가 크래시되지 않고 "바닥면 인식 실패: 표준 1인분 영양 성분으로 대체 표시합니다" 다이얼로그를 표시하며 정적 2D 영양 정보로 Graceful Fallback 렌더링.

## **12\. Implementation Milestones**

10일 해커톤 일정 동안 "랩실 5090 오프라인 학습 $\\to$ ONNX 추출 $\\to$ 독립 서빙 배포" 구조를 완성하기 위한 단계별 실행 계획입니다.

\[Day 1\~2\] 스캐폴딩 & 인프라 ──\> \[Day 2\~3\] DB 스키마 & 시드 ──\> \[Day 3\~6\] 5090 학습 & ONNX 서빙

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

\[Day 9\~10\] E2E 검증 & 데모 리허설 \<── \[Day 6\~8\] Next.js & Three.js 3D 뷰어 \<──┘

&nbsp;

### **Phase 1: 프로젝트 스캐폴딩 및 기반 환경 구축 (Day 1 \~ Day 2\)**

* **Action Items**:

  * `volumeal-align` 모노레포 구조 세팅 및 `.cursorrules` 주입.  
  * `training/`, `backend/`, `frontend/` 디렉토리 초기화 및 독립 가상환경/패키지 설정.  
  * Docker Compose 로컬 환경(PostgreSQL 15, FastAPI, Next.js) 구성.

**실행 터미널 명령어**:Bash

&nbsp;\# 1\. 모노레포 루트 생성

mkdir \-p volumeal-align/{training,backend,frontend}

cd volumeal-align

&nbsp;

\# 2\. 백엔드 초기화

cd backend

python3 \-m venv .venv && source .venv/bin/activate

pip install fastapi==0.111.0 uvicorn\[standard\]==0.30.1 sqlalchemy\[asyncio\]==2.0.30 asyncpg==0.29.0 pydantic-settings==2.2.1 alembic==1.13.1 onnxruntime==1.18.0 open3d==0.18.0 numpy==1.26.4 pillow==10.3.0 python-jose\[cryptography\]==3.3.0 passlib\[bcrypt\]==1.7.4

pip freeze \> requirements.txt

&nbsp;

\# 3\. 프론트엔드 초기화

cd ../frontend

npx create-next-app@14.2.3 . \--typescript \--tailwind \--app \--src-dir \--import-alias "@/\*" \--use-npm

npm install three @types/three @react-three/fiber @react-three/drei zustand @tanstack/react-query zod axios clsx tailwind-merge lucide-react

* &nbsp;  
* **Definition of Done (DoD)**:

  * `docker compose up -d` 구동 시 PostgreSQL(`5432`), FastAPI Swagger UI(`http://localhost:8000/docs`), Next.js 메인(`http://localhost:3000`)이 정상 200 헬스체크를 반환함.

### **Phase 2: DB 스키마 구축, 마이그레이션 및 시드 데이터 적재 (Day 2 \~ Day 3\)**

* **Action Items**:

  * `backend/app/models/` 내 7개 SQLAlchemy 2.0 ORM 엔티티 정의.  
  * Alembic 비동기 마이그레이션 파이프라인 구성 및 최초 DDL 실행.  
  * `seed.sql` 마스터 데이터(관리자/테스터 계정, 식약처 3종 약제, 상호작용 매트릭스) 적재 스크립트 작성.

**실행 터미널 명령어**:Bash

&nbsp;cd backend

alembic init \-t async migrations

\# migrations/env.py에 app.models Base 등록 후 실행

alembic revision \--autogenerate \-m "create\_initial\_schema"

alembic upgrade head

python \-m app.data.seed\_runner

* &nbsp;  
* **Definition of Done (DoD)**:

  * PostgreSQL 컨테이너 내 7개 테이블이 정상 생성되고 외래키 인덱스가 활성화되며, `psql`을 통해 테스터 계정과 쿠마딘정-비타민K 금기 룰이 정상 쿼리됨.

### **Phase 3: 랩실 5090 학습, ONNX 모델 반출 및 독립 추론 엔진 구축 (Day 3 \~ Day 6\)**

* **Action Items**:

  * **\[랩실 GPU 환경\]**: `training/train_depth_metric.py` 실행하여 Depth Anything v2 Metric 경량 어댑터 학습.  
  * **\[랩실 GPU 환경\]**: `training/export_onnx.py` 실행하여 INT8/FP32 CPU 가속형 `depth_anything_v2_vits.onnx` 추출.  
  * 모델 아티팩트를 개인 배포 환경(`backend/app/ml/weights/`)으로 다운로드 후 랩실 세션 완전 종료.  
  * **\[독립 서빙 환경\]**: `onnx_depth_estimator.py`, `onnx_segmentor.py`, `geometry_integrator.py` 구현 \[FR-001\~FR-004\].  
  * `POST /api/v1/vision/estimate` API 엔드포인트 통합 및 수치 적분 부피 계산 완결 \[FR-006\].

**실행 터미널 명령어**:Bash

&nbsp;\# 랩실 RTX 5090 머신에서 실행 (1\~2시간 소요)

cd training

python train\_depth\_metric.py \--epochs 10 \--batch-size 32 \--device cuda

python export\_onnx.py \--checkpoint weights/best\_metric.pth \--output ../backend/app/ml/weights/depth\_anything\_v2\_vits.onnx

&nbsp;

\# 파일 추출 확인 후 랩실 프로세스 종료

ls \-lh ../backend/app/ml/weights/depth\_anything\_v2\_vits.onnx \# 약 95MB 확인

* &nbsp;  
* **Definition of Done (DoD)**:

  * 로컬/배포 백엔드 환경에서 GPU 없이 CPU ONNX Runtime만으로 테스트 이미지 입력 시 450ms 이내에 $V(\\text{cm}^3)$, $W(g)$, 영양소 및 다운샘플링된 점군 페이로드가 포함된 JSON 응답이 반환됨.

### **Phase 4: 프론트엔드 연동, Three.js 3D 뷰어 및 대시보드 UI (Day 6 \~ Day 8\)**

* **Action Items**:  
  * 모바일 카메라 뷰파인더 캡처 및 EXIF 초점거리 자동 추출기 구현 \[FR-001\].  
  * Three.js 기반 3D 점군(`PointCloudViewer.tsx`) 및 3D Bounding Box(`BoundingVolumeMesh.tsx`) 컴포넌트 개발 \[FR-006\].  
  * 영양소 통계 카드(`NutritionSummary.tsx`) 및 약제 위험 배너(`DrugWarningBanner.tsx`) 구현 \[FR-004, FR-005\].  
  * Zustand 상태 스토어(`useMealStore.ts`) 및 TanStack Query 비동기 연동.  
* **Definition of Done (DoD)**:  
  * 사용자가 모바일 뷰포트에서 식단 사진을 업로드하면 3D 뷰어에 음식 포인트 클라우드가 로드되어 터치 드래그로 회전/확대가 가능하고, 복약 위험 알림이 즉각 렌더링됨.

### **Phase 5: 인증/인가 통합, 전역 에러 핸들링 및 최종 데모 리허설 (Day 9 \~ Day 10\)**

* **Action Items**:  
  * JWT HttpOnly 쿠키 인증 가드 및 RBAC 미들웨어 통합.  
  * 전역 표준 예외 핸들러 및 React Error Boundary 컴포넌트 적용.  
  * Playwright E2E 자동화 스크립트 작성 및 Happy/Failure 3종 시나리오 통과.  
  * 심사용 데모 프리셋 데이터 캐싱 구축 (네트워크 단절 대비).  
* **Definition of Done (DoD)**:  
  * 심사위원 시연 시나리오(쿠마딘정 \+ 시금치 식단 촬영) 실행 시 1초 이내에 3D 와이어프레임과 DANGER 위험 알림이 표출되며 전체 E2E 테스트 통과.

## **13\. Environment & Deployment**

### **13.1 환경변수 명세 테이블**

| Variable Name | Environment | Purpose | Example Format | Required |
| ----- | ----- | ----- | ----- | ----- |
| `ENV` | Common | 런타임 환경 식별 | `development` | `production` |
| `PORT` | Backend | 서버 리스닝 포트 | `8000` | Yes |
| `DATABASE_URL` | Backend | PostgreSQL 비동기 연결 DSN | `postgresql+asyncpg://volu:pass@db:5432/volumeal` | Yes |
| `JWT_SECRET_KEY` | Backend | JWT 토큰 서명 대칭키 (최소 256bit) | `8f4b2c1e7a...64자 Hex` | Yes |
| `JWT_ALGORITHM` | Backend | 서명 알고리즘 | `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Access Token 수명 | `15` | Yes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Refresh Token 수명 | `7` | Yes |
| `ONNX_DEPTH_MODEL_PATH` | Backend | 반출된 Depth ONNX 파일 경로 | `/app/ml/weights/depth_anything_v2_vits.onnx` | Yes |
| `ONNX_SEG_MODEL_PATH` | Backend | 반출된 Segment ONNX 파일 경로 | `/app/ml/weights/yolov8s_seg.onnx` | Yes |
| `CORS_ORIGINS` | Backend | CORS 허용 프론트엔드 도메인 | `http://localhost:3000,<https://volumeal.io`\> | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | 클라이언트 호출 API 게이트웨이 | `http://localhost:8000/api/v1` | Yes |

### **13.2 Dockerfile 사양 (`backend/Dockerfile`)**

랩실 GPU 의존성을 제거하고, 가벼운 컨테이너 환경에서 ONNX Runtime CPU 멀티스레딩 추론을 구동하기 위한 Multi-stage 빌드 명세입니다.

Dockerfile

\# Stage 1: Build & Dependencies installation

FROM python:3.10-slim AS builder

&nbsp;

ENV PYTHONDONTWRITEBYTECODE=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONUNBUFFERED=1

&nbsp;

RUN apt-get update && apt-get install \-y \--no-install-recommends \\

&nbsp;&nbsp;&nbsp;&nbsp;build-essential \\

&nbsp;&nbsp;&nbsp;&nbsp;curl \\

&nbsp;&nbsp;&nbsp;&nbsp;&& rm \-rf /var/lib/apt/lists/\*

&nbsp;

WORKDIR /install

COPY requirements.txt .

RUN pip install \--no-cache-dir \--prefix=/install/deps \-r requirements.txt

&nbsp;

\# Stage 2: Minimal Runtime Environment

FROM python:3.10-slim AS runner

&nbsp;

ENV PYTHONDONTWRITEBYTECODE=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONUNBUFFERED=1 \\

&nbsp;&nbsp;&nbsp;&nbsp;PATH="/install/deps/bin:$PATH" \\

&nbsp;&nbsp;&nbsp;&nbsp;PYTHONPATH="/install/deps/lib/python3.10/site-packages:$PYTHONPATH" \\

&nbsp;&nbsp;&nbsp;&nbsp;OMP\_NUM\_THREADS=4 \\

&nbsp;&nbsp;&nbsp;&nbsp;MKL\_NUM\_THREADS=4

&nbsp;

\# Open3D 및 OpenCV 헤드리스 종속 라이브러리 설치

RUN apt-get update && apt-get install \-y \--no-install-recommends \\

&nbsp;&nbsp;&nbsp;&nbsp;libgl1 \\

&nbsp;&nbsp;&nbsp;&nbsp;libglib2.0-0 \\

&nbsp;&nbsp;&nbsp;&nbsp;libgomp1 \\

&nbsp;&nbsp;&nbsp;&nbsp;&& rm \-rf /var/lib/apt/lists/\*

&nbsp;

WORKDIR /app

&nbsp;

COPY \--from=builder /install/deps /install/deps

COPY . .

&nbsp;

\# 보안 강화를 위한 Non-root 실행 유저 생성

RUN useradd \-u 1001 appuser && chown \-R appuser:appuser /app

USER appuser

&nbsp;

EXPOSE 8000

&nbsp;

CMD \["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--lifespan", "on"\]

&nbsp;

### **13.3 Docker Compose 구성 스펙 (`docker-compose.yml`)**

YAML

version: '3.8'

&nbsp;

services:

&nbsp;&nbsp;db:

&nbsp;&nbsp;&nbsp;&nbsp;image: postgres:15-alpine

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-postgres

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_USER: voluuser

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_PASSWORD: volupassword

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_DB: volumeal

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "5432:5432"

&nbsp;&nbsp;&nbsp;&nbsp;volumes:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- pgdata:/var/lib/postgresql/data

&nbsp;&nbsp;&nbsp;&nbsp;healthcheck:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;test: \["CMD-SHELL", "pg\_isready \-U voluuser \-d volumeal"\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;interval: 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;timeout: 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;retries: 5

&nbsp;

&nbsp;&nbsp;backend:

&nbsp;&nbsp;&nbsp;&nbsp;build:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;context: ./backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dockerfile: Dockerfile

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-backend

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;depends\_on:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;db:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;condition: service\_healthy

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ENV=development

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- PORT=8000

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- DATABASE\_URL=postgresql+asyncpg://voluuser:volupassword@db:5432/volumeal

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- JWT\_SECRET\_KEY=e83a9f7a6b2c4d5e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- JWT\_ALGORITHM=HS256

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ONNX\_DEPTH\_MODEL\_PATH=/app/app/ml/weights/depth\_anything\_v2\_vits.onnx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ONNX\_SEG\_MODEL\_PATH=/app/app/ml/weights/yolov8s\_seg.onnx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- CORS\_ORIGINS=http://localhost:3000

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "8000:8000"

&nbsp;&nbsp;&nbsp;&nbsp;volumes:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- ./backend/app/ml/weights:/app/app/ml/weights:ro

&nbsp;

&nbsp;&nbsp;frontend:

&nbsp;&nbsp;&nbsp;&nbsp;build:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;context: ./frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;dockerfile: Dockerfile

&nbsp;&nbsp;&nbsp;&nbsp;container\_name: volumeal-frontend

&nbsp;&nbsp;&nbsp;&nbsp;restart: unless-stopped

&nbsp;&nbsp;&nbsp;&nbsp;depends\_on:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- backend

&nbsp;&nbsp;&nbsp;&nbsp;environment:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- NEXT\_PUBLIC\_API\_BASE\_URL=http://localhost:8000/api/v1

&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- "3000:3000"

&nbsp;

volumes:

&nbsp;&nbsp;pgdata:

&nbsp;

### **13.4 CI/CD 배포 파이프라인 (.github/workflows/ci-cd.yml)**

YAML

name: VoluMeal-Align CI/CD Pipeline

&nbsp;

on:

&nbsp;&nbsp;push:

&nbsp;&nbsp;&nbsp;&nbsp;branches: \[ main, develop \]

&nbsp;&nbsp;pull\_request:

&nbsp;&nbsp;&nbsp;&nbsp;branches: \[ main \]

&nbsp;

jobs:

&nbsp;&nbsp;backend-lint-and-test:

&nbsp;&nbsp;&nbsp;&nbsp;runs-on: ubuntu-22.04

&nbsp;&nbsp;&nbsp;&nbsp;services:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;postgres:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;image: postgres:15-alpine

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_USER: voluuser

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_PASSWORD: volupassword

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;POSTGRES\_DB: volumeal\_test

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ports:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- 5432:5432

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;options: \>-

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-cmd pg\_isready

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-interval 10s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-timeout 5s

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\--health-retries 5

&nbsp;&nbsp;&nbsp;&nbsp;steps:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- uses: actions/checkout@v4

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Set up Python 3.10

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;uses: actions/setup-python@v5

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;python-version: "3.10"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache: "pip"

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Install Dependencies

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install \--upgrade pip

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install \-r requirements.txt

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pip install pytest pytest-asyncio flake8 mypy httpx

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Run Linting

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;flake8 app/ \--max-line-length=120 \--exclude=migrations/

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Run Backend Tests

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;DATABASE\_URL: postgresql+asyncpg://voluuser:volupassword@localhost:5432/volumeal\_test

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JWT\_SECRET\_KEY: test\_secret\_key\_1234567890\_test\_secret\_key\_1234567890

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JWT\_ALGORITHM: HS256

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd backend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PYTHONPATH=. pytest tests/ \-v

&nbsp;&nbsp;frontend-check:

&nbsp;&nbsp;&nbsp;&nbsp;runs-on: ubuntu-22.04

&nbsp;&nbsp;&nbsp;&nbsp;steps:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- uses: actions/checkout@v4

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Set up Node.js 18

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;uses: actions/setup-node@v4

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;node-version: 18

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache: "npm"

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cache-dependency-path: frontend/package-lock.json

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Install Frontend Dependencies

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm ci

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\- name: Type Check & Build

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cd frontend

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm run type-check

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;npm run build

&nbsp;

## **14\. Security Requirements**

### **14.1 OWASP Top 10 대응 설정치**

\[클라이언트 요청 수신\]

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

1\. 업로드 검증 (Magic Byte Header Check) ──\> 위조 바이너리 즉시 차단 (400)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

2\. Rate Limiting (SlowAPI / IP 기준 검사) ──\> 무차별 요청 차단 (429)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

3\. SQL Injection 방지 (SQLAlchemy 2.0 ORM) ──\> Parameterized Binding 강제

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

4\. 응답 전송: OWASP 보안 헤더 주입 ──\> CSP, HSTS, X-Content-Type-Options

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼

\[브라우저 렌더링: React JSX Auto-Escaping \+ DOMPurify (XSS 차단)\]

&nbsp;

* **SQL Injection 방어**: ORM(`SQLAlchemy 2.0`) 및 명시적 파라미터 바인딩 방식을 100% 강제합니다. 문자열 병합(`f"SELECT ... {input}"`)을 사용한 원시 쿼리 유입을 CI의 정적 분석 린터로 사전 차단합니다.  
* **Cross-Site Scripting (XSS) 방어**: Next.js React JSX의 Contextual Auto-Escaping을 유지하며, 임의의 HTML 삽입(`dangerouslySetInnerHTML`) 사용을 금지합니다. 외부 텍스트(식품 영양 정보, 약제 가이드) 렌더링 시 클라이언트 DOMPurify 정화 처리를 적용합니다.  
* **Cross-Site Request Forgery (CSRF) 방어**: 세션 토큰 쿠키에 `SameSite=Strict`, `Secure`, `HttpOnly` 속성을 강제하여 서드파티 사이트에서의 크로스 사이트 요청 전송을 원천 차단합니다.  
* **CORS 설정**: 프로덕션 배포 시 `allow_origins`에 정밀 허용 도메인(`https://volumeal.io`)만 명시하고 와일드카드() 지정을 엄격히 금지합니다.

### **14.2 Rate Limiting 및 무차별 대입(Brute Force) 방어 규칙**

* **FastAPI SlowAPI 적용**:  
  * `POST /api/v1/auth/login`: 동일 IP 및 사용자 계정 기준 **분당 5회** 초과 시 `429 Too Many Requests`를 반환하고 해당 계정에 대해 15분간 로그인 잠금을 적용합니다.  
  * `POST /api/v1/vision/estimate`: CPU 리소스 고갈 방지를 위해 인증된 사용자 토큰 기준 **분당 20회**로 요청을 제한합니다.  
* **파일 업로드 버퍼 제한**: 멀티파트 파싱 시 메모리 버퍼 한도를 10MB로 설정하여 대용량 파일 전송을 통한 DoS 공격을 차단합니다.

## **15\. Assumptions & Risks**

### **15.1 \[Assumption\] (기술적 가정 및 영향도)**

1. **\[ASM-001\] 모바일 브라우저 EXIF 초점거리 부재 시 표준 화각 대체**:  
   * *가정*: 모바일 OS 보안 정책 또는 압축 전송으로 인해 EXIF 메타데이터가 손실된 경우, 스마트폰 기본 광각 카메라 기준값($f=26\\text{mm}$, 수평 화각 약 $68^\\circ$)을 카메라 내부 행렬 $K$로 기본 적용합니다.  
   * *영향도*: 2배/3배 망원 줌으로 촬영된 사진의 경우 3D 역투영 스케일에서 15\~20%의 수축 오차가 발생할 수 있습니다. 시스템은 응답 객체에 `is_calibrated: false` 플래그를 설정하여 UI에 "표준 화각 기준 추정치" 경고를 노출합니다.  
2. **\[ASM-002\] 3차원 바닥면 밀착 및 닫힌 표면(Closed Surface) 가정**:  
   * *가정*: 단안 카메라 특성상 음식 밑면과 그릇 바닥 사이의 비가시 영역을 관측할 수 없으므로, 음식 객체는 RANSAC으로 추정된 바닥 평면 위에 틈새 없이 놓여 있는 닫힌 체적으로 간주합니다.  
   * *영향도*: 국물에 반쯤 떠 있는 음식이나 공중에 띄워진 식기 구조에서는 체적이 과대 추정될 수 있으며, 이는 국물류 마스크 면적 제외 계수 보정으로 완화합니다.

### **15.2 \[Decision Required\] (개발 착수 전 결정 완료 항목)**

1. **\[DEC-001\] 랩실 GPU와 배포 서빙 환경의 분리 정책 확정**:  
   * *확정 내용*: 랩실 RTX 5090은 모델 학습 및 `model.onnx` 파일 반출용으로만 1\~2시간 한정 구동 후 종료합니다. 배포 및 심사 시연은 개인 노트북 CPU(또는 독립 클라우드)에서 ONNX Runtime CPU로 구동하여 연구실 전산망 보안 위반 및 자원 점유 리스크를 원천 차단합니다.  
2. **\[DEC-002\] 약제 식별 입력 경로 우선순위 정책**:  
   * *확정 내용*: 식탁 위 알약/약봉투의 100% 비전 자동 검출(Visual Grounding) 실패 가능성에 대비하여, '사용자 등록 처방약 프로필'을 1순위 베이스라인으로 삼고 식탁 위 비전 검출 결과를 결합하는 하이브리드 판정 정책을 채택합니다.

### **15.3 식별된 주요 기술 리스크 및 완화 방안 (Risk & Mitigation Plan)**

| Risk ID | 위험 요인 | 발생 확률 | 영향도 | 완화 방안 (Mitigation Strategy) |
| ----- | ----- | ----- | ----- | ----- |
| **RSK-001** | **RANSAC 바닥 평면 추정 실패** |  |  |  |

(식기 테두리 차폐 또는 테이블 패턴 노이즈로 인라이어 40% 미달) | 중 | 상 | 식기 테두리 픽셀의 깊이 최솟값(Min Depth)과 그릇 검출 마스크의 기하학적 형태를 결합한 원통형/타원체 체적 근사 수식($V \\approx \\frac{2}{3} \\pi r^2 h$)으로 즉각 Fallback 수행. |  
&nbsp;| **RSK-002** | **CPU 서빙 환경에서 추론 지연 시간 급증** | 중 | 중 | Depth Anything v2의 인코더 백본을 `vits`(Small, 약 2,500만 파라미터)로 고정하고, ONNX OMP 스레드를 4개로 고정하여 단일 이미지 450ms 이내 처리 보장. |  
&nbsp;| **RSK-003** | **Three.js 모바일 브라우저 WebGL 메모리 누수** | 중 | 상 | 컴포넌트 언마운트(`useEffect` 클린업) 시 캔버스 내 지오메트리(`geometry.dispose()`) 및 재질(`material.dispose()`)을 명시적으로 해제하고 최대 점군 수를 5,000개로 강제 제한. |  
&nbsp;| **RSK-004** | **심사 당일 현장 네트워크 불안정 및 지연** | 중 | 치명 | 발표용 3대 시나리오(와파린-시금치, 스타틴-자몽, 갑상선약-우유)에 대한 분석 결과 JSON 및 3D 점군 데이터를 클라이언트 로컬 캐시(`/demo-presets`)로 탑재하여 오프라인 환경에서도 시연 가능하도록 보장. |

## **16\. Agent Instruction Configuration**

AI 코딩 도구(Cursor, Claude Code, Devin 등)가 프로젝트 루트 컨텍스트에서 직접 로드하여 개발 표준과 아키텍처 원칙을 준수하도록 강제하는 인스트럭션 파일입니다.

### **16.1 `.cursorrules` / `CLAUDE.md`**

Markdown

\# VoluMeal-Align AI Coding Agent Ruleset

&nbsp;

\#\# Core Architecture Principles

\- You are implementing VoluMeal-Align, an enterprise-grade monocular 3D meal volume estimation & drug interaction engine.

\- Always maintain 1:1 traceability to the Functional Requirements (FR-001 to FR-007).

\- Architecture Rule: Model training occurs offline on a lab RTX 5090 GPU, exporting standalone ONNX weights (\`model.onnx\`). The serving backend runs independently on ONNX Runtime CPU. Never write code that assumes an active GPU or lab network connection during serving.

\- No speculative code, no incomplete stubs (\`// TODO\`, \`// ...생략\`), and no unhandled exceptions.

&nbsp;

\#\# Tech Stack & Language Conventions

\- Backend: Python 3.10+, FastAPI 0.111+, SQLAlchemy 2.0 (Async), Pydantic v2, ONNX Runtime 1.18+, Open3D 0.18+.

&nbsp;&nbsp;\- All DB queries must use \`select(...)\` syntax with \`AsyncSession\`. Never use legacy Query API.

&nbsp;&nbsp;\- Pydantic models must use \`model\_config \= ConfigDict(from\_attributes=True)\` for ORM compatibility.

&nbsp;&nbsp;\- Point cloud and numerical arrays must be vectorized using NumPy or Open3D. Never use Python \`for\` loops over image pixels.

&nbsp;&nbsp;\- Image decoding must happen in-memory via \`io.BytesIO\`. Do not persist uploaded images to the local disk.

\- Frontend: Next.js 14.2+ (App Router), TypeScript 5.4+ (Strict Mode), Tailwind CSS, Three.js (@react-three/fiber).

&nbsp;&nbsp;\- Never use the \`any\` type in TypeScript. Use shared types defined in \`src/types/api.ts\`.

&nbsp;&nbsp;\- All client forms and payloads must validate through Zod schemas defined in \`src/schemas/api.ts\`.

&nbsp;&nbsp;\- Visual 3D objects must strictly implement WebGL cleanup (\`dispose()\` geometries and materials on unmount).

&nbsp;

\#\# Directory Boundaries & Responsibilities

\- \`training/\`: Contains offline training and ONNX export scripts for the lab RTX 5090 machine.

\- \`backend/app/ml/\`: Houses ONNX Runtime wrappers and geometry integration algorithms. No HTTP dependencies here.

\- \`backend/app/services/\`: Orchestrates vision pipelines, DB transactions, and domain business rules.

\- \`backend/app/api/v1/endpoints/\`: Thin controllers. Only validate input DTOs, invoke services, and return standard responses.

\- \`frontend/src/components/viewer3d/\`: Three.js Canvas and WebGL components. Must include \`'use client'\`.

\- \`frontend/src/stores/\`: Zustand store (\`useMealStore.ts\`) for synchronizing 3D viewer state and nutrition report data.

&nbsp;

\#\# Error Handling Standards

\- Always raise custom domain exceptions inheriting from \`AppException\` in \`backend/app/core/exceptions.py\`.

\- Every API error response must strictly adhere to the \`StandardErrorResponse\` schema with appropriate \`code\`, \`message\`, and \`timestamp\`.

\- Database operations must be wrapped in transactions that automatically roll back on failure.

&nbsp;

\#\# Critical Verification Commands

\- Backend Lint & Type Check: \`flake8 app/ && mypy app/\`

\- Backend Unit & Integration Tests: \`pytest tests/ \-v\`

\- Frontend Type Check & Build: \`npm run type-check && npm run build\`

&nbsp;

이로써 **VoluMeal-Align** 프로젝트에 대한 3단계 분할 기술 구현 명세서(Technical Specification)의 모든 섹션(섹션 1\~16) 출력이 완결되었습니다. 추가 세부 모듈의 단위 구현 코드나 스크립트가 필요한 경우 요청하십시오.

## **17. FR-004 정정 부록: foodId 기반 변환 계층**

본 부록은 FR-004의 기존 “DINOv2 패치 벡터와 음식명/영양 DB 직접 검색” 표현을 대체합니다.

1. 음식 마스크 크롭을 임베딩 모델에 입력합니다.
2. 임베딩은 음식명이 아니라 라벨된 기준 음식 이미지 임베딩과 코사인 비교합니다.
3. 검색기는 `foodId`, Top-3 후보와 점수를 반환합니다.
4. `foodId`로 분리된 카탈로그, 밀도 프로필, 영양 프로필을 조인합니다.
5. `무게(g) = 부피(cm³) × 밀도(g/cm³)`로 계산합니다.
6. `섭취 영양소 = 기준 영양소 × 추정 무게 / 기준 중량`으로 계산합니다.

자동 확정 조건은 Top-1 점수 0.80 이상이면서 Top-1과 Top-2 점수 차이가 0.10 이상인 경우입니다.
조건을 충족하지 못하면 `requiresConfirmation=true`와 Top-3 후보를 반환하며, 사용자 확인 전
분석 결과와 복약 경고를 영구 저장하지 않습니다.

카메라 EXIF 기본 26mm는 미보정 추정값에만 사용합니다. 정확도 수용 검증은 크기를 아는 마커 또는
동등한 기준 물체로 깊이 스케일을 보정한 뒤 수행해야 하며, 응답의 `isCalibrated`는 이 보정의
실제 적용 여부를 나타냅니다. 깊이 스케일 보정이 없는 결과는 정량 정확도 달성 근거로 사용하지 않습니다.

## **18. 사용자 보정 및 미확인 음식 처리 변경사항**

현재 구현에서는 음식 인식 결과를 항상 자동 확정하지 않습니다. Top-1 점수와 후보 간 차이가 자동 확정 기준에 미달하면 `requiresConfirmation=true`와 함께 Top-3 후보를 반환합니다. 각 후보에는 현재 부피 기준의 밀도, 중량, 칼로리, 탄수화물, 단백질, 지방 및 나트륨 값이 포함됩니다.

프론트엔드는 후보를 버튼으로 표시하며 사용자가 선택한 후보로 음식명·밀도·영양값·총합을 갱신합니다. 사용자가 중량을 수정하면 기존 중량 대비 비율로 영양값과 총합을 다시 계산합니다. 후보 선택과 중량 보정은 저장 성공 전까지 클라이언트 임시 상태입니다. 모든 후보를 선택한 뒤 “확정하고 저장”으로 `POST /api/v1/vision/confirm`을 호출합니다. 서버는 `foodId`, `volumeCm3`, 선택적 `weightG`로 영양값과 복약 경고를 재계산하고 저장합니다. 측정 부피는 중량 보정으로 변경하지 않습니다. 이미 자동 저장된 본인 식단은 갱신하며, 동일 식단 재시도로 중복 기록을 생성하지 않습니다. 타인의 식단 수정은 거부합니다. 저장 실패 시 클라이언트 보정값을 유지하여 재시도할 수 있습니다. 분석 단계에서는 자동 확정된 결과만 저장합니다.

음식 또는 약제가 검출되지 않은 경우에는 표준값으로 대체하지 않고 `ERR_ZERO_OBJECT_DETECTED`를 반환합니다. 클라이언트는 일반 오류 대신 음식이 잘 보이도록 밝은 곳에서 접시 전체를 다시 촬영하라는 안내를 표시합니다.

&nbsp;
>>>>>>> REPLACE
```

## 신규 파일: frontend/tests/e2e/confirmation.spec.ts

```typescript
import { test, expect } from '@playwright/test';
import fixture from '../fixtures/vision-estimate.json';
import type { MealEstimateResponse } from '../../src/types/vision';

test('FR-008 candidate, weight correction, failed save and retry', async ({ page }) => {
  const data: MealEstimateResponse = structuredClone(fixture.data);
  data.isPersisted = false;
  data.requiresConfirmation = true;
  const item = data.foodItems[0];
  item.requiresConfirmation = true;
  item.topCandidates = [{ foodId: 'chosen', foodName: '선택 음식', score: 0.7,
    densityGCm3: 1, weightG: 100, caloriesKcal: 200, carbsG: 30, proteinG: 5, fatG: 3, sodiumMg: 20 }];
  let attempts = 0;
  await page.route('**/api/v1/health', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'fixture' } }));
  await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
  await page.route('**/api/v1/vision/estimate', route => route.fulfill({ json: { success: true, data } }));
  await page.route('**/api/v1/vision/confirm', async route => {
    attempts++;
    const body = route.request().postDataJSON();
    expect(body.mealId).toBe(data.mealId);
    expect(body.confirmedItems[0].foodId).toBe('chosen');
    expect(body.confirmedItems[0].weightG).toBe(200);
    expect(body.confirmedItems[0].volumeCm3).toBe(item.volumeCm3);
    expect(body.confirmedItems[0].caloriesKcal).toBeUndefined();
    if (attempts === 1) return route.fulfill({ status: 503, json: { error: { message: '저장 실패' } } });
    return route.fulfill({ json: { success: true, data: {
      ...data, isPersisted: true, requiresConfirmation: false, drugWarnings: [],
      totalNutrition: { caloriesKcal: 400, carbsG: 60, proteinG: 10, fatG: 6, sodiumMg: 40 },
      foodItems: [{ ...item, foodId: 'chosen', foodName: '선택 음식', weightG: 200, caloriesKcal: 400 }],
    } } });
  });
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('fixture-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'test.png', mimeType: 'image/png', buffer: Buffer.from('fixture') });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  const save = page.getByRole('button', { name: '확정하고 저장' });
  await expect(save).toBeDisabled();
  await page.getByRole('button', { name: /선택 음식/ }).click();
  await page.getByLabel('선택 음식 중량').fill('200');
  await expect(page.getByText('400 kcal', { exact: true })).toBeVisible();
  await save.click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('저장 실패');
  await expect(page.getByLabel('선택 음식 중량')).toHaveValue('200');
  await save.click();
  await expect(page.getByText('저장되었습니다.', { exact: true })).toBeVisible();
  await expect(save).toBeDisabled();
  expect(attempts).toBe(2);
});

test('FR-008 plane failure gives retake guidance', async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/auth/login', route => route.fulfill({ json: { accessToken: 'fixture' } }));
  await page.route('**/api/v1/meals', route => route.fulfill({ json: { success: true, data: { items: [] } } }));
  await page.route('**/api/v1/vision/estimate', route => route.fulfill({ status: 422,
    json: { error: { code: 'ERR_GEOMETRY_PLANE_NOT_FOUND', message: 'internal geometry detail' } } }));
  await page.goto('/');
  await page.getByLabel('이메일').fill('fixture@test.invalid');
  await page.getByLabel('비밀번호').fill('fixture-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'test.png', mimeType: 'image/png', buffer: Buffer.from('fixture') });
  await page.getByRole('button', { name: '식단 분석', exact: true }).click();
  await expect(page.getByRole('main').getByRole('alert')).toContainText('접시와 주변 테이블이 함께 보이도록 다시 촬영');
});

```
