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
    weightG: Optional[float] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("weightG", "weight_g", "correctedWeightG", "corrected_weight_g"),
        description="사용자 보정 중량(g) [FR-007, FR-008]",
    )
    correctedWeightG: Optional[float] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("correctedWeightG", "corrected_weight_g", "weightG", "weight_g"),
        description="사용자 보정 중량(g) [FR-007]",
    )
    volumeCm3: Optional[float] = Field(default=None, ge=5, le=5000, description="기측정된 부피 (cm³)")
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class MealCorrectionInput(StrictModel):
    foodItemId: str = Field(
        ...,
        validation_alias=AliasChoices("foodItemId", "food_item_id", "itemId", "item_id"),
        description="보정 대상 음식 항목 식별자 (UUID) [FR-007]",
    )
    correctedWeightG: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("correctedWeightG", "corrected_weight_g", "weightG", "weight_g"),
        description="수정 중량(g) [FR-007]",
    )


class FoodItemVolumeData(StrictModel):
    itemId: Optional[str] = None
    id: Optional[str] = None
    foodId: Optional[str] = None
    volumeCm3: float = Field(ge=5, le=5000)
    confidenceScore: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    bbox2d: Optional[BoundingBox2D] = None
    bbox3d: Optional[BoundingBox3D] = None


class VisionConfirmRequest(StrictModel):
    mealId: Optional[str] = Field(default=None, description="식단 식별자 (UUID)")
    imageUrl: Optional[str] = Field(default="", description="식단 이미지 URL")
    focalLengthMm: float = Field(default=26.0, gt=0, le=1000, description="35mm 환산 초점거리")
    isCalibrated: bool = Field(default=False, description="깊이 스케일 보정 여부")
    confirmedItems: List[ConfirmedFoodSelection] = Field(
        default=[],
        validation_alias=AliasChoices("confirmedItems", "confirmedFoods", "selectedFoods", "selections", "confirmed_items"),
        description="사용자가 확정한 [{ itemId, foodId }] 리스트"
    )
    corrections: Optional[List[MealCorrectionInput]] = Field(
        default=None,
        validation_alias=AliasChoices("corrections", "correctionItems", "correction_items"),
        description="[FR-007] 수동 중량 보정 항목 리스트 [{ foodItemId, correctedWeightG }]"
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
        if not self.confirmedItems and not self.corrections:
            raise ValueError("확정할 음식 항목(confirmedItems) 또는 보정 항목(corrections)이 최소 1개 이상 필요합니다.")
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
    isUserAdjusted: bool = Field(default=False)
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

