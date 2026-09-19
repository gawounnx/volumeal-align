import datetime
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class FoodItemDetail(BaseModel):
    id: uuid.UUID
    foodName: str
    confidenceScore: float
    volumeCm3: float
    densityGCm3: float
    weightG: float
    caloriesKcal: float
    carbsG: float
    proteinG: float
    fatG: float
    sodiumMg: float
    bbox2d: Dict[str, Any]
    bbox3d: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class DrugWarningDetail(BaseModel):
    id: uuid.UUID
    drugId: uuid.UUID
    foodItemId: Optional[uuid.UUID]
    riskLevel: str
    detectedVia: str
    warningTitle: str
    warningMessage: str

    model_config = ConfigDict(from_attributes=True)


class MealDetailResponse(BaseModel):
    id: uuid.UUID
    userId: uuid.UUID
    imageUrl: str
    focalLengthMm: float
    isCalibrated: bool
    totalCaloriesKcal: float
    totalCarbsG: float
    totalProteinG: float
    totalFatG: float
    totalSodiumMg: float
    foodItems: List[FoodItemDetail]
    drugWarnings: List[DrugWarningDetail]
    createdAt: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class MealListItem(BaseModel):
    id: uuid.UUID
    imageUrl: str
    totalCaloriesKcal: float
    foodItemCount: int
    highestRiskLevel: str
    createdAt: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class MealListData(BaseModel):
    totalCount: int
    page: int
    pageSize: int
    items: List[MealListItem]

    model_config = ConfigDict(from_attributes=True)


class MealListResponse(BaseModel):
    success: bool = True
    data: MealListData

    model_config = ConfigDict(from_attributes=True)

