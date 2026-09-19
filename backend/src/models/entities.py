"""Models matching the specification (SSOT) schema."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from src.core.database import Base


class Record:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc)
    )


class User(Record, Base):
    """사용자 계정 엔티티 [FR-008] (Requirement Specification 7.1.1)."""
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("password_hash", String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)

    # Backward compatibility synonym
    hashed_password = synonym("password_hash")

    meals: Mapped[list["Meal"]] = relationship(back_populates="user")


class Meal(Record, Base):
    """식단 분석 마스터 엔티티 [FR-001, FR-006] (Requirement Specification 7.1.2)."""
    __tablename__ = "meals"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    focal_length_mm: Mapped[float] = mapped_column(Numeric(6, 2), default=26.00, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ESTIMATED", nullable=False)
    total_calories: Mapped[float] = mapped_column("total_calories", Numeric(8, 2), default=0.00, nullable=False)
    total_carbs: Mapped[float] = mapped_column("total_carbs", Numeric(8, 2), default=0.00, nullable=False)
    total_protein: Mapped[float] = mapped_column("total_protein", Numeric(8, 2), default=0.00, nullable=False)
    total_fat: Mapped[float] = mapped_column("total_fat", Numeric(8, 2), default=0.00, nullable=False)

    # Additional runtime helper columns
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    total_sodium_mg: Mapped[float | None] = mapped_column(Numeric(8, 2), default=0.00, nullable=True)

    # Backward compatibility synonyms
    total_calories_kcal = synonym("total_calories")
    total_carbs_g = synonym("total_carbs")
    total_protein_g = synonym("total_protein")
    total_fat_g = synonym("total_fat")

    user: Mapped[User] = relationship(back_populates="meals")
    food_items: Mapped[list["MealFoodItem"]] = relationship(back_populates="meal", cascade="all, delete-orphan")


class MealFoodItem(Record, Base):
    """개별 음식 체적 및 영양소 엔티티 [FR-003, FR-004, FR-007] (Requirement Specification 7.1.3)."""
    __tablename__ = "meal_food_items"
    meal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True, nullable=False)
    food_id: Mapped[str] = mapped_column(String(64), default="FOOD_001", nullable=False)
    food_name: Mapped[str] = mapped_column(String(100), nullable=False)
    volume_cm3: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    weight_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    calories: Mapped[float] = mapped_column("calories", Numeric(8, 2), default=0.00, nullable=False)
    carbs: Mapped[float] = mapped_column("carbs", Numeric(8, 2), default=0.00, nullable=False)
    protein: Mapped[float] = mapped_column("protein", Numeric(8, 2), default=0.00, nullable=False)
    fat: Mapped[float] = mapped_column("fat", Numeric(8, 2), default=0.00, nullable=False)
    is_user_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Additional runtime helper columns
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 4), default=1.0, nullable=True)
    density_g_cm3: Mapped[float | None] = mapped_column(Numeric(6, 4), default=1.0, nullable=True)
    sodium_mg: Mapped[float | None] = mapped_column(Numeric(8, 2), default=0.0, nullable=True)
    bbox_2d: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    bbox_3d: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Backward compatibility synonyms
    calories_kcal = synonym("calories")
    carbs_g = synonym("carbs")
    protein_g = synonym("protein")
    fat_g = synonym("fat")

    meal: Mapped[Meal] = relationship(back_populates="food_items")
    correction_logs: Mapped[list["MealCorrectionLog"]] = relationship(
        back_populates="meal_food_item", cascade="all, delete-orphan"
    )


class MealCorrectionLog(Base):
    """SSOT 기반 사용자 수동 보정 이력 감사 테이블 [FR-007] (Requirement Specification 7.1.4)."""
    __tablename__ = "meal_correction_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_food_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meal_food_items.id", ondelete="CASCADE"), nullable=False, index=True)
    original_weight_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    new_weight_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    meal_food_item: Mapped[MealFoodItem] = relationship(back_populates="correction_logs")
