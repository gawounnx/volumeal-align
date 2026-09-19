import datetime
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_user
from src.core.database import get_db_session
from src.core.exceptions import AccessDeniedException
from src.models.entities import Meal, User
from src.schemas.meal import (
    DrugWarningDetail,
    FoodItemDetail,
    MealDetailResponse,
    MealListData,
    MealListItem,
    MealListResponse,
)

router = APIRouter(prefix="/meals", tags=["Meals"])


def _compute_highest_risk_level(warnings: list) -> str:
    # Ref: [FR-007] Risk level precedence: DANGER > CAUTION > NONE
    levels = {w.risk_level for w in warnings}
    if "DANGER" in levels:
        return "DANGER"
    if "CAUTION" in levels:
        return "CAUTION"
    return "NONE"


@router.get(
    "",
    response_model=MealListResponse,
    status_code=status.HTTP_200_OK,
    summary="사용자 식단 기록 목록 조회",
)
async def list_user_meals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    pageSize: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    startDate: Optional[datetime.datetime] = Query(None, description="조회 시작 일시 (ISO 8601)"),
    endDate: Optional[datetime.datetime] = Query(None, description="조회 종료 일시 (ISO 8601)"),
) -> MealListResponse:
    # Ref: [FR-007] 사용자별 식단 목록 필터링 및 페이징 Envelope 조회
    filters = [Meal.user_id == current_user.id]
    if startDate is not None:
        filters.append(Meal.created_at >= startDate)
    if endDate is not None:
        filters.append(Meal.created_at <= endDate)

    count_stmt = select(func.count()).select_from(Meal).where(*filters)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * pageSize
    stmt = (
        select(Meal)
        .where(*filters)
        .options(selectinload(Meal.food_items))
        .order_by(desc(Meal.created_at))
        .offset(offset)
        .limit(pageSize)
    )
    result = await db.execute(stmt)
    meals = result.scalars().all()

    items = [
        MealListItem(
            id=m.id,
            imageUrl=m.image_url,
            totalCaloriesKcal=float(m.total_calories_kcal),
            foodItemCount=len(m.food_items),
            highestRiskLevel=_compute_highest_risk_level(getattr(m, "drug_warnings", [])),
            createdAt=m.created_at,
        )
        for m in meals
    ]

    return MealListResponse(
        success=True,
        data=MealListData(
            totalCount=total_count,
            page=page,
            pageSize=pageSize,
            items=items,
        ),
    )



@router.get(
    "/{meal_id}",
    response_model=MealDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="식단 상세 3D 체적 및 약제 경고 정보 조회",
)
async def get_meal_detail(
    meal_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MealDetailResponse:
    # Ref: [Section 9.3, 14.1] IDOR 방어: WHERE id = :meal_id AND user_id = :current_user_id 강제
    stmt = (
        select(Meal)
        .where(Meal.id == meal_id, Meal.user_id == current_user.id)
        .options(selectinload(Meal.food_items))
    )
    result = await db.execute(stmt)
    meal = result.scalar_one_or_none()

    if not meal:
        # Ref: [Section 9.3, 14.1] 대상 식단 레코드가 존재하지만 타인 소유인 경우 403 Forbidden 반환
        existing = (await db.execute(select(Meal.id).where(Meal.id == meal_id))).scalar_one_or_none()
        if existing:
            raise AccessDeniedException("본인 소유의 식단에만 접근할 수 있습니다.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"식단 ID({meal_id})를 찾을 수 없습니다.",
        )

    return MealDetailResponse(
        id=meal.id,
        userId=meal.user_id,
        imageUrl=meal.image_url,
        focalLengthMm=float(meal.focal_length_mm),
        isCalibrated=meal.is_calibrated,
        totalCaloriesKcal=float(meal.total_calories_kcal),
        totalCarbsG=float(meal.total_carbs_g),
        totalProteinG=float(meal.total_protein_g),
        totalFatG=float(meal.total_fat_g),
        totalSodiumMg=float(meal.total_sodium_mg),
        foodItems=[
            FoodItemDetail(
                id=item.id,
                foodName=item.food_name,
                confidenceScore=float(item.confidence_score),
                volumeCm3=float(item.volume_cm3),
                densityGCm3=float(item.density_g_cm3),
                weightG=float(item.weight_g),
                caloriesKcal=float(item.calories_kcal),
                carbsG=float(item.carbs_g),
                proteinG=float(item.protein_g),
                fatG=float(item.fat_g),
                sodiumMg=float(item.sodium_mg),
                bbox2d=item.bbox_2d,
                bbox3d=item.bbox_3d,
            )
            for item in meal.food_items
        ],
        drugWarnings=[
            DrugWarningDetail(
                id=w.id,
                drugId=w.drug_id,
                foodItemId=w.food_item_id,
                riskLevel=w.risk_level,
                detectedVia=w.detected_via,
                warningTitle=w.warning_title,
                warningMessage=w.warning_message,
            )
            for w in getattr(meal, "drug_warnings", [])
        ],
        createdAt=meal.created_at,
    )
