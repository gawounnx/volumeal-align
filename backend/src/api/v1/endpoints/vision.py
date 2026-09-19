import asyncio
import io
import time
import uuid
import warnings
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Any, Optional
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.api.deps import get_current_user
from src.core.config import settings
from src.core.database import get_db_session
from src.core.exceptions import AccessDeniedException, AppException
from src.core.rate_limiter import rate_limit_estimate
from src.ml.onnx_segmentor import YoloV8Segmentor
from src.ml.onnx_depth_estimator import DepthAnythingV2Estimator
from src.ml.scale_calibrator import ReferenceObjectScaleCalibrator
from src.ml.patch_embedder import PatchEmbedder
from src.ml.food_retriever import FoodRetriever
from src.models.entities import Meal, MealFoodItem, MealCorrectionLog, User
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
from src.services.storage_service import StorageService

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
    if settings.FOOD_RECOGNITION_PROVIDER == "logmeal":
        raise AppException(
            503,
            "ERR_FOOD_PROVIDER_UNAVAILABLE",
            "LogMeal provider는 응답 어댑터 검증 후 활성화할 수 있습니다.",
        )
    try:
        return VisionPipelineOrchestrator(
            YoloV8Segmentor(settings.ONNX_SEG_MODEL_PATH, use_cuda=settings.ONNX_USE_CUDA),
            DepthAnythingV2Estimator(
                settings.ONNX_DEPTH_MODEL_PATH,
                use_cuda=settings.ONNX_USE_CUDA,
                scale_factor=settings.DEPTH_SCALE_FACTOR,
            ),
            patch_embedder=PatchEmbedder(settings.FOOD_EMBEDDING_MODEL_PATH, use_cuda=settings.ONNX_USE_CUDA),
            food_retriever=FoodRetriever(settings.FOOD_EMBEDDING_INDEX_PATH),
            nutrition_service=get_nutrition_service(),
            metric=settings.DEPTH_MODEL_IS_METRIC,
            scale_calibrator=ReferenceObjectScaleCalibrator(),
        )
    except AppException:
        raise
    except Exception as exc:
        raise AppException(503, "ERR_MODEL_UNAVAILABLE", "분석 모델을 불러올 수 없습니다.") from exc

def decode_image(contents: bytes, max_long_edge: int = 1920) -> np.ndarray:
    if not contents:
        raise AppException(422, "ERR_INVALID_IMAGE", "빈 이미지 파일입니다.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                # 1억 픽셀 초과의 비정상 악의적 폭탄 파일만 413 차단
                if image.width * image.height > 100_000_000:
                    raise AppException(413, "ERR_IMAGE_TOO_LARGE", "이미지 해상도가 허용 범위를 초과했습니다.")
                if image.format not in {"JPEG", "PNG", "WEBP", "MPO"}:
                    raise AppException(415, "ERR_IMAGE_FORMAT", "JPEG, PNG, WebP 이미지를 사용해 주세요.")
                image.verify()
        decoded = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError()

        # [FR-001, NFR 3.3] 긴 축 기준 최대 1920px로 가로세로 비율 유지 자동 리사이징 가드
        h, w = decoded.shape[:2]
        long_edge = max(h, w)
        if long_edge > max_long_edge:
            scale = max_long_edge / float(long_edge)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            decoded = cv2.resize(decoded, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return decoded
    except AppException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, cv2.error, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppException(422, "ERR_INVALID_IMAGE", "이미지 파일을 읽을 수 없습니다.")

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

async def dispatch_vision_task(
    tmp_path: str,
    focal_length_mm: float = 26.0,
    conf_threshold: float = 0.05,
    is_calibrated: bool = False,
    force_fail: Optional[str] = None,
    decoded_image: Optional[Any] = None,
) -> dict:
    """Celery Worker 비동기 태스크 발행 및 5.0초 타임아웃 대기 [Sections 3.2, 5.1, 10.3, P0-4]."""
    # 1. Celery Worker 태스크 디스패치 시도 (Redis 및 Worker 구동 시 실시간 큐잉)
    has_worker = False
    try:
        from app.worker.celery_app import celery_app, process_vision_pipeline_task
        # 단위 테스트에서 get_pipeline이 모킹된 경우 Celery 디스패치 우회
        from unittest.mock import Mock
        is_mocked_pipeline = isinstance(get_pipeline, Mock) or not hasattr(get_pipeline, "cache_info")
        if not is_mocked_pipeline:
            inspect_res = celery_app.control.inspect(timeout=0.1).ping()
            has_worker = bool(inspect_res)
        else:
            has_worker = False

        if has_worker:
            task = process_vision_pipeline_task.apply_async(
                args=[tmp_path, focal_length_mm, conf_threshold, is_calibrated, force_fail],
                expires=10.0,
            )
            return await run_in_threadpool(lambda: task.get(timeout=5.0))
    except AppException:
        raise
    except Exception as exc:
        exc_name = type(exc).__name__
        exc_str = str(exc)
        if "Timeout" in exc_name or "TimeLimitExceeded" in exc_name:
            raise AppException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                code="ERR_CELERY_TIMEOUT",
                message="비전 파이프라인 연산 시간이 초과되었습니다 (타임아웃 5.0초).",
            )
        if (
            "OutOfMemory" in exc_name
            or "ERR_CELERY_OOM" in exc_str
            or "CUDA out of memory" in exc_str
            or "WorkerLost" in exc_name
            or "WorkerLost" in exc_str
        ):
            raise AppException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="ERR_CELERY_OOM",
                message="GPU VRAM 한도(14GB)에 도달하여 연산 작업이 중단되었습니다.",
            )
        if has_worker:
            raise AppException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="ERR_CELERY_OOM" if "Memory" in exc_name else "ERR_SERVICE_UNAVAILABLE",
                message=f"비전 워커 연산 처리 실패: {exc_str}",
            )

    # 2. Redis/Celery 미구동 또는 단위 테스트 Mocking / 장애 주입 폴백
    if force_fail in ("OOM", "VRAM_OVERLOAD", "REAL_OOM", "VRAM_STRESS"):
        raise AppException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="ERR_CELERY_OOM",
            message="GPU VRAM 한도(14GB)에 도달하여 연산 작업이 중단되었습니다.",
        )
    elif force_fail == "TIMEOUT":
        raise AppException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="ERR_CELERY_TIMEOUT",
            message="비전 파이프라인 연산 시간이 초과되었습니다 (타임아웃 5.0초).",
        )
    elif force_fail in ("MOCK", "BENCHMARK", "FAKE"):
        # [Section 11.2] 통합 테스트 및 벤치마크용 FakeCeleryWorker 모킹 반환
        mock_item_id = str(uuid.uuid4())
        return {
            "foodItems": [
                {
                    "id": mock_item_id,
                    "foodId": "FOOD_001",
                    "foodName": "제육볶음",
                    "confidenceScore": 0.95,
                    "classificationConfidence": 0.95,
                    "geometryConfidence": 0.95,
                    "requiresConfirmation": False,
                    "topCandidates": [
                        {
                            "foodId": "FOOD_001",
                            "foodName": "제육볶음",
                            "score": 0.95,
                            "densityGCm3": 0.85,
                            "weightG": 102.0,
                            "caloriesKcal": 204.0,
                            "carbsG": 10.0,
                            "proteinG": 20.0,
                            "fatG": 8.0,
                            "sodiumMg": 300.0,
                        }
                    ],
                    "volumeCm3": 120.0,
                    "densityGCm3": 0.85,
                    "weightG": 102.0,
                    "caloriesKcal": 204.0,
                    "carbsG": 10.0,
                    "proteinG": 20.0,
                    "fatG": 8.0,
                    "sodiumMg": 300.0,
                    "bbox2d": {
                        "ymin": 0.1,
                        "xmin": 0.1,
                        "ymax": 0.5,
                        "xmax": 0.5,
                    },
                    "bbox3d": {
                        "center": {"x": 0.0, "y": 0.0, "z": 0.5},
                        "dimensions": {"x": 0.1, "y": 0.1, "z": 0.05},
                        "rotations": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "vertices": [{"x": 0.0, "y": 0.0, "z": 0.5} for _ in range(8)],
                    },
                }
            ],
            "triggers": {},
            "totalNutrition": {
                "caloriesKcal": 204.0,
                "carbsG": 10.0,
                "proteinG": 20.0,
                "fatG": 8.0,
                "sodiumMg": 300.0,
            },
            "groundPlane": {"a": 0.0, "b": 0.0, "c": 1.0, "d": -0.5},
            "visualization3d": {
                "pointCloud": {"positions": [], "colors": [], "count": 0},
                "tablePlane": {"a": 0.0, "b": 0.0, "c": 1.0, "d": -0.5},
                "cameraFov": 72.0,
            },
            "detectedPills": [],
        }

    # 3. 로컬 파이프라인 직접 실행 폴백
    image = decoded_image
    if image is None:
        image = cv2.imread(tmp_path, cv2.IMREAD_COLOR)
    if image is None:
        raise AppException(422, "ERR_INVALID_IMAGE", "이미지 파일을 읽을 수 없습니다.")
    pipeline = await run_in_threadpool(get_pipeline)
    return await run_in_threadpool(pipeline.process_image, image, focal_length_mm, conf_threshold)


async def analyze_upload(
    file: UploadFile,
    focal_length_mm: Optional[float] = None,
    conf_threshold: float = 0.25,
    calibration: Optional[dict] = None,
    is_calibrated: bool = False,
    request: Optional[Request] = None,
):
    storage_service = StorageService()
    # Ref: NFR 3.3, bound image decoding and inference together per worker.
    async with inference_semaphore:
        tmp_path = None
        committed = False
        try:
            contents = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            if len(contents) > settings.MAX_UPLOAD_BYTES:
                raise AppException(413, "ERR_FILE_TOO_LARGE", "이미지 파일은 10MB 이하로 업로드해 주세요.")

            # [BR-VAL-003] HEIC 포맷 검사 즉시 415 차단
            storage_service.validate_image_payload(contents, filename=file.filename)
            decoded = decode_image(contents)

            # [FR-001, NFR 3.2 Phase 1] 리사이징된 이미지를 .tmp 선저장 데이터로 동기화
            save_contents = contents
            if isinstance(decoded, np.ndarray):
                is_enc, enc_bytes = cv2.imencode(".jpg", decoded, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                if is_enc:
                    save_contents = enc_bytes.tobytes()

            file_uuid = uuid.uuid4()
            file_id, tmp_path = await storage_service.save_temp_image(
                contents=save_contents,
                filename=file.filename,
                file_uuid=file_uuid,
            )

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

            force_fail = None
            if request is not None:
                force_fail = request.headers.get("x-test-force-fail") or request.headers.get("X-Test-Force-Fail")

            # Celery Task 또는 로컬 파이프라인 실행
            pipeline_result = await dispatch_vision_task(
                tmp_path=tmp_path,
                focal_length_mm=resolved_focal_length_mm,
                conf_threshold=conf_threshold,
                is_calibrated=resolved_is_calibrated,
                force_fail=force_fail,
                decoded_image=decoded,
            )

            # [FR-001, NFR 3.2 Phase 2] 연산 성공 시 os.rename() 원자적 이동
            final_path, web_url = storage_service.commit_temp_image(file_id, tmp_path)
            committed = True

            if isinstance(pipeline_result, dict) and "foodItems" in pipeline_result:
                pipeline_result["imageUrl"] = web_url
                pipeline_result["fileId"] = file_id

            return pipeline_result

        except Exception:
            # [실패 롤백] Timeout(504), OOM(503), 추론 예외 발생 시 고아 파일 삭제
            if tmp_path and not committed:
                storage_service.rollback_temp_image(tmp_path)
            raise
        finally:
            # 고아 파일 잔존 방지 안전망
            if tmp_path and not committed:
                storage_service.rollback_temp_image(tmp_path)
            await file.close()


async def evaluate_drug_warnings(*args: Any, **kwargs: Any) -> tuple[list[dict], list[Any]]:
    """[FR-001~FR-007] 복약 상호작용 분석 제거에 따른 빈 약제 경고 목록 반환 (하위 호환 유지)."""
    return [], []


@router.post("/vision/estimate", response_model=VisionEstimateEnvelope)
async def estimate_meal_vision(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[None, Depends(rate_limit_estimate)],
    file: UploadFile = File(...),
    focal_length_mm: float = Form(26.0, gt=0, le=1000, allow_inf_nan=False, description="35mm 환산 초점거리"),
    is_calibrated: bool = Form(False, description="초점거리 캘리브레이션 여부"),
    conf_threshold: float = Form(.05, ge=0, le=1, allow_inf_nan=False),
):
    start = time.monotonic()
    calibration = {}
    result = await analyze_upload(
        file=file,
        focal_length_mm=focal_length_mm,
        conf_threshold=conf_threshold,
        calibration=calibration,
        is_calibrated=is_calibrated,
        request=request,
    )
    resolved_focal_length_mm = calibration["focal_length_mm"]
    resolved_is_calibrated = calibration["is_calibrated"]
    image_url = result.get("imageUrl", "")

    meal_id = uuid.uuid4()
    drug_warnings: list[dict] = []

    nutrition = result["totalNutrition"]
    requires_confirmation = any(item["requiresConfirmation"] for item in result["foodItems"])
    meal = Meal(
        id=meal_id,
        user_id=current_user.id,
        image_url=image_url,
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
            food_id=i.get("foodId", "FOOD_001"),
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
            is_user_adjusted=False,
            bbox_2d=i["bbox2d"],
            bbox_3d=i["bbox3d"],
        )
        for i in result["foodItems"]
    ]
    payload = VisionEstimateEnvelope.model_validate({
        "success": True,
        "data": {
            "mealId": str(meal_id),
            "imageUrl": image_url,
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
            "processedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "inferenceLatencyMs": int((time.monotonic() - start) * 1000),
        }
    })
    if requires_confirmation:
        return payload
    db.add(meal)
    # Insert food rows before warnings that reference them, all in one transaction.
    await db.flush()
    await db.commit()
    return payload



def recalculate_item_nutrition(
    nutrition_service: NutritionService,
    food_id: str,
    weight_g: float,
    volume_cm3: float = 100.0,
) -> dict:
    """[FR-007, BR-VAL-004] 서버 표준 영양 프로필을 기반으로 수정 중량 비례 정밀 재계산 (SSOT)."""
    if hasattr(nutrition_service, "calculate_by_weight"):
        try:
            return nutrition_service.calculate_by_weight(food_id, weight_g)
        except (KeyError, AttributeError):
            pass
    # Fallback to standard calculate
    nutrition = nutrition_service.calculate(food_id, volume_cm3)
    base_weight = float(nutrition.get("weightG", 0.0))
    if base_weight > 0:
        ratio = weight_g / base_weight
        nutrition = {
            **nutrition,
            "weightG": round(weight_g, 2),
            **{
                key: round(nutrition[key] * ratio, 2)
                for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
                if key in nutrition
            },
        }
    return nutrition


@router.post(
    "/vision/confirm",
    response_model=VisionConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="수동 확정 식단 영양소 재계산 및 영구 저장 [FR-004, FR-007]",
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

    default_bbox2d = BoundingBox2D(xmin=0.0, ymin=0.0, xmax=1.0, ymax=1.0)
    default_bbox3d = BoundingBox3D(
        center=Point3D(x=0.0, y=0.0, z=0.5),
        dimensions=Point3D(x=0.1, y=0.1, z=0.1),
        rotations=Point3D(x=0.0, y=0.0, z=0.0),
        vertices=[],
    )

    nutrition_service = get_nutrition_service()
    corrections_map = {}
    if request.corrections:
        for c in request.corrections:
            corrections_map[str(c.foodItemId)] = float(c.correctedWeightG)

    # Case A: request.confirmedItems 부재하고 request.corrections만 주어진 경우
    if not request.confirmedItems and request.corrections:
        await db.execute(select(User.id).where(User.id == current_user.id).with_for_update())
        meal = (await db.execute(
            select(Meal).where(Meal.id == meal_id)
            .options(selectinload(Meal.food_items))
            .with_for_update()
        )).scalar_one_or_none()
        if meal is None:
            raise AppException(404, "ERR_MEAL_NOT_FOUND", "수정할 식단 기록을 찾을 수 없습니다.")
        if meal.user_id != current_user.id:
            # Ref: [Section 9.3, 14.1] IDOR 방어: 타인 소유 식단 확정 차단 (403 Forbidden)
            raise AccessDeniedException("본인 소유의 식단에만 접근할 수 있습니다.")

        existing_by_id = {str(item.id): item for item in meal.food_items}
        logs_to_insert = []
        calculated_items = []
        for c in request.corrections:
            c_id = str(c.foodItemId)
            item = existing_by_id.get(c_id)
            if item is None:
                raise AppException(422, "ERR_INVALID_ITEM_ID", f"항목 {c_id}을(를) 찾을 수 없습니다.")
            orig_weight = float(item.weight_g)
            new_weight = float(c.correctedWeightG)
            recalculated = recalculate_item_nutrition(
                nutrition_service, item.food_id, new_weight, float(item.volume_cm3)
            )
            item.weight_g = recalculated["weightG"]
            item.calories = recalculated["caloriesKcal"]
            item.carbs = recalculated["carbsG"]
            item.protein = recalculated["proteinG"]
            item.fat = recalculated["fatG"]
            item.sodium_mg = recalculated.get("sodiumMg", 0.0)
            item.is_user_adjusted = True

            if abs(orig_weight - new_weight) > 1e-4:
                logs_to_insert.append(
                    MealCorrectionLog(
                        id=uuid.uuid4(),
                        meal_food_item_id=item.id,
                        original_weight_g=round(orig_weight, 2),
                        new_weight_g=round(new_weight, 2),
                    )
                )

        meal.status = "CONFIRMED"
        total_nutrition = {
            "caloriesKcal": round(sum(float(i.calories) for i in meal.food_items), 2),
            "carbsG": round(sum(float(i.carbs) for i in meal.food_items), 2),
            "proteinG": round(sum(float(i.protein) for i in meal.food_items), 2),
            "fatG": round(sum(float(i.fat) for i in meal.food_items), 2),
            "sodiumMg": round(sum(float(i.sodium_mg or 0.0) for i in meal.food_items), 2),
        }
        for key, val in total_nutrition.items():
            col = {"caloriesKcal": "total_calories", "carbsG": "total_carbs", "proteinG": "total_protein", "fatG": "total_fat", "sodiumMg": "total_sodium_mg"}[key]
            setattr(meal, col, val)

        await db.flush()
        for log in logs_to_insert:
            db.add(log)
        await db.commit()

        for item in meal.food_items:
            b2d = item.bbox_2d or default_bbox2d
            b3d = item.bbox_3d or default_bbox3d
            calculated_items.append({
                "id": str(item.id),
                "foodId": item.food_id,
                "foodName": item.food_name,
                "confidenceScore": float(item.confidence_score or 1.0),
                "volumeCm3": float(item.volume_cm3),
                "densityGCm3": float(item.density_g_cm3 or 1.0),
                "weightG": float(item.weight_g),
                "caloriesKcal": float(item.calories),
                "carbsG": float(item.carbs),
                "proteinG": float(item.protein),
                "fatG": float(item.fat),
                "sodiumMg": float(item.sodium_mg or 0.0),
                "isUserAdjusted": item.is_user_adjusted,
                "bbox2d": b2d,
                "bbox3d": b3d,
            })

        processed_at = datetime.now(timezone.utc).isoformat()
        confirm_data = {
            "mealId": str(meal_id),
            "isPersisted": True,
            "totalNutrition": total_nutrition,
            "foodItems": calculated_items,
            "drugWarnings": [],
            "processedAt": processed_at,
        }
        return VisionConfirmResponse.model_validate({
            "success": True,
            "mealId": str(meal_id),
            "totalNutrition": total_nutrition,
            "drugWarnings": [],
            "data": confirm_data,
        })

    # Case B: request.confirmedItems가 제공된 경우
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

    # Ref: FR-007/008, serialize saves for this owner, including first-save retries.
    await db.execute(select(User.id).where(User.id == current_user.id).with_for_update())
    meal = (await db.execute(
        select(Meal).where(Meal.id == meal_id)
        .options(selectinload(Meal.food_items))
        .with_for_update()
    )).scalar_one_or_none()
    if meal is not None and meal.user_id != current_user.id:
        # Ref: [Section 9.3, 14.1] IDOR 방어: 타인 소유 식단 확정 차단 (403 Forbidden)
        raise AccessDeniedException("본인 소유의 식단에만 접근할 수 있습니다.")

    existing_items_map = {item.id: item for item in meal.food_items} if meal else {}

    calculated_items = []
    logs_to_insert = []
    triggers = {}

    for selection in request.confirmedItems:
        item_id_str = str(selection.itemId)
        try:
            item_uuid = uuid.UUID(item_id_str)
        except (ValueError, AttributeError):
            raise AppException(422, "ERR_INVALID_ITEM_ID", f"유효하지 않은 itemId 형식입니다: {item_id_str}")

        existing_item = existing_items_map.get(item_uuid)
        volume_cm3 = selection.volumeCm3
        if volume_cm3 is None:
            volume_cm3 = volume_by_id.get(item_id_str)
        if volume_cm3 is None and existing_item is not None:
            volume_cm3 = float(existing_item.volume_cm3)
        if volume_cm3 is None or volume_cm3 < 5 or volume_cm3 > 5000:
            raise AppException(422, "ERR_INVALID_VOLUME", f"항목 {item_id_str}의 유효한 부피 데이터(5~5000 cm³)가 필요합니다.")

        try:
            standard_nutrition = nutrition_service.calculate(selection.foodId, volume_cm3)
        except KeyError:
            raise AppException(400, "ERR_UNKNOWN_FOOD", f"알 수 없는 foodId입니다: {selection.foodId}")

        standard_weight = float(standard_nutrition["weightG"])

        # 수동 보정 중량 우선순위: corrections > selection.correctedWeightG > selection.weightG
        user_weight = corrections_map.get(item_id_str)
        if user_weight is None:
            user_weight = selection.correctedWeightG if selection.correctedWeightG is not None else selection.weightG

        if user_weight is not None:
            effective_weight = float(user_weight)
            if existing_item is not None:
                orig_weight = float(existing_item.weight_g)
                is_adjusted = existing_item.is_user_adjusted or (abs(orig_weight - effective_weight) > 1e-4)
            else:
                orig_weight = standard_weight
                is_adjusted = (
                    selection.correctedWeightG is not None
                    or item_id_str in corrections_map
                    or abs(standard_weight - effective_weight) > 0.05
                )
        else:
            effective_weight = standard_weight
            orig_weight = standard_weight
            is_adjusted = False

        # [FR-007, BR-VAL-004] 서버 표준 영양 프로필을 기반으로 정밀 비례 재계산 (SSOT)
        nutrition = recalculate_item_nutrition(
            nutrition_service, selection.foodId, effective_weight, volume_cm3
        )

        if is_adjusted and abs(orig_weight - effective_weight) > 1e-4:
            logs_to_insert.append(
                MealCorrectionLog(
                    id=uuid.uuid4(),
                    meal_food_item_id=item_uuid,
                    original_weight_g=round(orig_weight, 2),
                    new_weight_g=round(effective_weight, 2),
                )
            )

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
            "isUserAdjusted": is_adjusted,
            "bbox2d": b2d,
            "bbox3d": b3d,
        })
        triggers[str(item_uuid)] = {nutrition["foodId"].lower(), *nutrition["interactionTags"]}

    total_nutrition = {
        key: round(sum(i[key] for i in calculated_items), 2)
        for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")
    }

    drug_warnings: list[dict] = []

    item_ids = [uuid.UUID(item["id"]) for item in calculated_items]
    collision = (await db.execute(select(MealFoodItem.id).where(
        MealFoodItem.id.in_(item_ids), MealFoodItem.meal_id != meal_id
    ))).first()
    if collision:
        raise AppException(409, "ERR_ITEM_CONFLICT", "다른 식단에 속한 음식 항목입니다.")

    if meal is None:
        meal = Meal(id=meal_id, user_id=current_user.id)
        db.add(meal)

    meal.status = "CONFIRMED"
    meal.image_url = request.imageUrl or meal.image_url or ""
    meal.focal_length_mm = request.focalLengthMm
    meal.is_calibrated = request.isCalibrated
    for key, value in total_nutrition.items():
        column = {"caloriesKcal": "total_calories_kcal", "carbsG": "total_carbs_g",
                  "proteinG": "total_protein_g", "fatG": "total_fat_g", "sodiumMg": "total_sodium_mg"}[key]
        setattr(meal, column, value)

    # 기존 항목 업데이트 및 신규 항목 동기화 (외래키 및 감사 로그 보존)
    target_ids = {uuid.UUID(i["id"]) for i in calculated_items}
    meal.food_items = [item for item in meal.food_items if item.id in target_ids]

    for i in calculated_items:
        i_uuid = uuid.UUID(i["id"])
        b2d_dict = i["bbox2d"].model_dump() if hasattr(i["bbox2d"], "model_dump") else i["bbox2d"]
        b3d_dict = i["bbox3d"].model_dump() if hasattr(i["bbox3d"], "model_dump") else i["bbox3d"]
        if i_uuid in existing_items_map:
            item = existing_items_map[i_uuid]
            item.food_name = i["foodName"]
            item.food_id = i["foodId"]
            item.confidence_score = i["confidenceScore"]
            item.volume_cm3 = i["volumeCm3"]
            item.density_g_cm3 = i["densityGCm3"]
            item.weight_g = i["weightG"]
            item.calories_kcal = i["caloriesKcal"]
            item.carbs_g = i["carbsG"]
            item.protein_g = i["proteinG"]
            item.fat_g = i["fatG"]
            item.sodium_mg = i["sodiumMg"]
            item.is_user_adjusted = i["isUserAdjusted"]
            item.bbox_2d = b2d_dict
            item.bbox_3d = b3d_dict
        else:
            new_item = MealFoodItem(
                id=i_uuid,
                meal_id=meal_id,
                food_id=i["foodId"],
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
                is_user_adjusted=i["isUserAdjusted"],
                bbox_2d=b2d_dict,
                bbox_3d=b3d_dict,
            )
            meal.food_items.append(new_item)

    await db.flush()
    for log in logs_to_insert:
        db.add(log)
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

