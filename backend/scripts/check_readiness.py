"""Read-only startup diagnostics with strict authenticity and provenance verification."""
import asyncio
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, text
from src.core.config import settings
from src.core.database import engine
from src.models.entities import User, Meal, MealFoodItem, MealCorrectionLog
from src.ml.food_retriever import FoodRetriever
from src.ml.patch_embedder import PatchEmbedder
from src.services.nutrition_service import NutritionService


async def check():
    report = {
        "database": False,
        "schema": False,
        "segmentationModel": False,
        "metricDepthModel": False,
        "foodRecognition": False,
        "nutritionData": False,
        "provenanceVerified": False,
        "inferenceProviders": [],
        "unverifiedReasons": [],
    }

    # 1. DB 연결 및 스키마 검증
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            report["database"] = True
            for model in (User, Meal, MealFoodItem, MealCorrectionLog):
                await connection.execute(select(model).limit(0))
            report["schema"] = True
    except Exception as exc:
        report["databaseError"] = type(exc).__name__
        report["unverifiedReasons"].append(f"데이터베이스 연결/스키마 실패: {exc}")
    finally:
        await engine.dispose()

    # 2. 세그멘테이션 모델 검증
    try:
        from src.ml.onnx_segmentor import YoloV8Segmentor
        seg_file = Path(settings.ONNX_SEG_MODEL_PATH)
        if not seg_file.is_file() or seg_file.stat().st_size < 50_000_000:
            report["unverifiedReasons"].append("세그멘테이션 모델 파일이 부재하거나 크기가 비정상적입니다.")
        else:
            model = YoloV8Segmentor(settings.ONNX_SEG_MODEL_PATH, use_cuda=settings.ONNX_USE_CUDA)
            report["segmentationModel"] = True
            report["inferenceProviders"] = model.session.get_providers()
    except Exception as exc:
        report["segmentationError"] = type(exc).__name__
        report["unverifiedReasons"].append(f"세그멘테이션 모델 로드 실패: {exc}")

    # 3. 실측 메트릭 깊이 모델 검증 (FR-001)
    depth_file = Path(settings.ONNX_DEPTH_MODEL_PATH)
    if not settings.DEPTH_MODEL_IS_METRIC:
        report["unverifiedReasons"].append("DEPTH_MODEL_IS_METRIC 플래그가 비활성화되어 있습니다.")
    elif not depth_file.is_file():
        report["unverifiedReasons"].append("ONNX_DEPTH_MODEL_PATH 파일이 존재하지 않습니다.")
    elif depth_file.stat().st_size < 50_000_000:
        report["unverifiedReasons"].append(f"깊이 모델 크기가 비정상입니다 ({depth_file.stat().st_size} bytes, 최소 50MB 요구).")
    else:
        try:
            from src.ml.onnx_depth_estimator import DepthAnythingV2Estimator
            estimator = DepthAnythingV2Estimator(settings.ONNX_DEPTH_MODEL_PATH)
            report["metricDepthModel"] = estimator.session is not None
            if not report["metricDepthModel"]:
                report["unverifiedReasons"].append("깊이 모델 ONNX 세션 초기화에 실패했습니다.")
        except Exception as exc:
            report["depthError"] = type(exc).__name__
            report["unverifiedReasons"].append(f"깊이 모델 추론기 로드 실패: {exc}")

    # 4. 정품 DINOv2 임베더 및 실제 음식 임베딩 인덱스 검증 (FR-004)
    embedder_file = Path(settings.FOOD_EMBEDDING_MODEL_PATH)
    index_file = Path(settings.FOOD_EMBEDDING_INDEX_PATH)

    if not embedder_file.is_file() or embedder_file.stat().st_size < 10_000_000:
        report["unverifiedReasons"].append(
            f"DINOv2 임베더 모델이 미배치되었거나 비정규 임시 모델입니다 (크기: {embedder_file.stat().st_size if embedder_file.is_file() else 0} bytes, 최소 10MB 요구)."
        )
    elif not index_file.is_file():
        report["unverifiedReasons"].append("식품 레퍼런스 임베딩 인덱스 파일(food_reference_embeddings.npz)이 없습니다.")
    else:
        try:
            PatchEmbedder(settings.FOOD_EMBEDDING_MODEL_PATH)
            retriever = FoodRetriever(settings.FOOD_EMBEDDING_INDEX_PATH)
            report["foodRecognition"] = True
        except Exception as exc:
            report["foodRecognitionError"] = type(exc).__name__
            report["unverifiedReasons"].append(f"음식 임베딩 검색 엔진 로드 실패: {exc}")

    # 5. 공식 식품코드 및 출처(Provenance) 엄격 검증 (FR-004)
    try:
        nutrition = NutritionService(settings.FOOD_CATALOG_PATH, settings.FOOD_DENSITY_PATH, settings.FOOD_NUTRIENTS_PATH)
        report["nutritionData"] = True

        if report["foodRecognition"]:
            missing = sorted(set(retriever.food_ids) - set(nutrition.catalog))
            missing_index = sorted(set(nutrition.catalog) - set(retriever.food_ids))
            report["missingNutritionFoodIds"] = missing
            report["missingEmbeddingFoodIds"] = missing_index
            if missing:
                report["nutritionData"] = False
                report["unverifiedReasons"].append(f"카탈로그 누락 식품 ID: {missing}")
            if missing_index:
                report["foodRecognition"] = False
                report["unverifiedReasons"].append(f"임베딩 누락 식품 ID: {missing_index}")

        # 출처 및 공식 코드 유효성 전수 검증
        provenance_ok = True
        temp_code_pattern = re.compile(r"^D00000[0-9]$")

        for fid, nut in nutrition.nutrients.items():
            code = getattr(nut, "sourceFoodCode", "")
            # 단순 임시 순번 코드(D000001~D000009) 엄격 차단
            if temp_code_pattern.match(code):
                provenance_ok = False
                report["unverifiedReasons"].append(f"{fid}: 임시 순번 코드({code})가 감지되었습니다. 공공 표준 코드가 필요합니다.")
            if not getattr(nut, "sourceUrl", "") or not getattr(nut, "officialFoodName", ""):
                provenance_ok = False
                report["unverifiedReasons"].append(f"{fid}: 공식 출처 URL 또는 공시 품목명이 누락되었습니다.")

        for fid, den in nutrition.densities.items():
            protocol = getattr(den, "protocol", "")
            sample_count = getattr(den, "sampleCount", 0)
            if not protocol or sample_count < 1:
                provenance_ok = False
                report["unverifiedReasons"].append(f"{fid}: 밀도 실측 프로토콜 또는 측정 횟수 메타데이터가 누락되었습니다.")

        report["provenanceVerified"] = provenance_ok

    except Exception as exc:
        report["nutritionError"] = type(exc).__name__
        report["unverifiedReasons"].append(f"영양 데이터 로드 실패: {exc}")

    # 모든 항목 및 정합성/출처 검증까지 통과해야만 최종 ready=True
    report["ready"] = all(
        report[key]
        for key in (
            "database",
            "schema",
            "segmentationModel",
            "metricDepthModel",
            "foodRecognition",
            "nutritionData",
            "provenanceVerified",
        )
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(check()))
