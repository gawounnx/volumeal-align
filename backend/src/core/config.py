import secrets
from pathlib import Path
from typing import List, Literal, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    ENV: str = "development"
    PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://voluuser:volupassword@0.0.0.0:5432/volumeal"
    REDIS_URL: str = "redis://0.0.0.0:6379/0"
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_COOKIE_NAME: str = "volumeal_access"
    AUTH_REFRESH_COOKIE_NAME: str = "volumeal_refresh"
    AUTH_COOKIE_SECURE: bool = False
    ONNX_DEPTH_MODEL_PATH: str = str(BACKEND_ROOT / "weights/depth_anything_v2_vits.onnx")
    ONNX_SEG_MODEL_PATH: str = str(BACKEND_ROOT / "weights/yolov8s_seg.onnx")
    ONNX_USE_CUDA: bool = False
    DEPTH_MODEL_IS_METRIC: bool = True
    DEPTH_SCALE_FACTOR: float = 0.18
    FOOD_CATALOG_PATH: str = str(BACKEND_ROOT / "data/food_catalog.json")
    FOOD_DENSITY_PATH: str = str(BACKEND_ROOT / "data/food_density_profiles.json")
    FOOD_NUTRIENTS_PATH: str = str(BACKEND_ROOT / "data/food_nutrients.json")
    FOOD_EMBEDDING_MODEL_PATH: str = str(BACKEND_ROOT / "weights/dinov2_food_embedder.onnx")
    FOOD_EMBEDDING_INDEX_PATH: str = str(BACKEND_ROOT / "data/food_reference_embeddings.npz")
    FOOD_RECOGNITION_PROVIDER: Literal["local", "logmeal"] = "local"
    FOOD_RECOGNITION_API_KEY: str = ""
    FOOD_RECOGNITION_API_URL: str = ""
    FOOD_RECOGNITION_TIMEOUT_SECONDS: float = 5.0
    LOGMEAL_API_TOKEN: str = ""
    LOGMEAL_API_BASE_URL: str = "https://api.logmeal.com"
    LOGMEAL_TIMEOUT_SECONDS: float = 8.0
    FOOD_RECOGNITION_MAX_RETRIES: int = 1
    FOOD_RECOGNITION_MIN_CONFIDENCE: float = 0.25
    DEV_AUTH_BYPASS: bool = False
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    MAX_IMAGE_PIXELS: int = 12_000_000
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v if isinstance(v, list) else ["http://localhost:3000"]

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value[len("postgresql://"):]
        return value

    @field_validator("FOOD_RECOGNITION_TIMEOUT_SECONDS")
    @classmethod
    def validate_food_recognition_timeout(cls, value: float) -> float:
        if not 0 < value <= 30:
            raise ValueError("FOOD_RECOGNITION_TIMEOUT_SECONDS must be in (0, 30]")
        return value

    @field_validator("FOOD_RECOGNITION_MAX_RETRIES")
    @classmethod
    def validate_food_recognition_retries(cls, value: int) -> int:
        if not 0 <= value <= 3:
            raise ValueError("FOOD_RECOGNITION_MAX_RETRIES must be in [0, 3]")
        return value

    @field_validator("FOOD_RECOGNITION_MIN_CONFIDENCE")
    @classmethod
    def validate_food_recognition_confidence(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("FOOD_RECOGNITION_MIN_CONFIDENCE must be in [0, 1]")
        return value

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

if not settings.JWT_SECRET_KEY:
    if settings.ENV != "development":
        raise RuntimeError("JWT_SECRET_KEY must be configured outside development")
    settings.JWT_SECRET_KEY = secrets.token_urlsafe(48)
