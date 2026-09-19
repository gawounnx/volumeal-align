"""Celery Worker 데몬 및 GPU 샌드박스 비전 파이프라인 태스크 [Sections 1.3, 3.2, 3.3, 5.1, 10.3].

- Redis(6379) 브로커 및 결과 백엔드
- Worker 부트스트랩 시 PyTorch VRAM 14GB 한도 Lock (torch.cuda.set_per_process_memory_fraction(0.43, device=0))
- 작업 타임아웃 5.0초 강제 (task_time_limit=5.0)
- OOM 발생 시 ERR_CELERY_OOM (503) 전파
"""
import os
import time
from typing import Any, Dict, Optional
import cv2
import numpy as np
from celery import Celery
from celery.signals import worker_process_init

# Redis Broker & Backend URL 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 앱 인스턴스 초기화
celery_app = Celery(
    "volumeal_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Celery 상세 설정 (5.0초 타임아웃, 단일 GPU 프로세스 격리)
celery_app.conf.update(
    task_time_limit=5.0,
    task_soft_time_limit=5.0,
    worker_concurrency=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=300,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
)


_vram_limit_applied = False


def apply_gpu_vram_limit() -> None:
    """[NFR 3.3, 10.3, P0-4] Celery Worker 프로세스 기동 시 GPU VRAM 14GB 한도 잠금."""
    global _vram_limit_applied
    if _vram_limit_applied:
        return
    try:
        import torch
        if torch.cuda.is_available():
            # RTX 5090 32GB 기준 14GB 락 (14/32 = 0.4375)
            fraction = 14.0 / 32.0
            torch.cuda.set_per_process_memory_fraction(fraction, device=0)
            _vram_limit_applied = True
            print(f"[Celery Worker] GPU VRAM fraction clamped to {fraction:.4f} (14.0GB limit on 32GB RTX 5090)")
    except Exception as exc:
        print(f"[Celery Worker] GPU VRAM limit notice: {exc}")


@worker_process_init.connect
def on_worker_init(**kwargs: Any) -> None:
    """Worker fork 후 프로세스 초기화 시 VRAM 락 적용 (Fork 안전성 보장)."""
    apply_gpu_vram_limit()


from celery.signals import worker_ready


@worker_ready.connect
def on_worker_ready(**kwargs: Any) -> None:
    """Solo 풀 또는 단일 프로세스 모드 기동 시 VRAM 락 적용."""
    apply_gpu_vram_limit()


@celery_app.task(bind=True, name="app.worker.celery_app.process_vision_pipeline_task")
def process_vision_pipeline_task(
    self,
    temp_image_path: str,
    focal_length_mm: Optional[float] = 26.0,
    conf_threshold: float = 0.05,
    is_calibrated: bool = False,
    force_fail: Optional[str] = None,
) -> Dict[str, Any]:
    """임시 저장된 이미지 경로를 입력받아 비전 추론 파이프라인 비동기 실행 [FR-001~FR-004, P0-4]."""
    # 안전망: 워커 프로세스 내 VRAM 상한 미적용 시 적용
    apply_gpu_vram_limit()
    # 1. 테스트 목적의 장애 주입 처리 [Section 11.2, P0-4]
    called_directly = getattr(getattr(self, "request", None), "called_directly", False)
    oom_exc_cls = MemoryError if called_directly else RuntimeError

    if force_fail == "OOM":
        raise oom_exc_cls("ERR_CELERY_OOM: CUDA out of memory (Simulated 14GB VRAM exceed)")
    elif force_fail in ("VRAM_OVERLOAD", "REAL_OOM", "VRAM_STRESS"):
        # [P0-4] 실제 GPU VRAM 14GB 샌드박스 초과 유도 부하 테스트
        import torch
        if torch.cuda.is_available():
            tensors = []
            try:
                # 1GB chunk(250M float32 = 1,000,000,000 bytes) 단위로 최대 16GB 할당 시도
                # torch.cuda.set_per_process_memory_fraction(14/32)에 의해 14GB 도달 시 OutOfMemoryError 발생
                for _ in range(16):
                    tensors.append(torch.empty((250_000_000,), dtype=torch.float32, device="cuda:0"))
            except Exception as exc:
                if "OutOfMemoryError" in type(exc).__name__ or "CUDA out of memory" in str(exc):
                    raise oom_exc_cls("ERR_CELERY_OOM: GPU VRAM limit exceeded (clamped at 14GB)") from exc
                raise
            finally:
                del tensors
                torch.cuda.empty_cache()
        else:
            raise oom_exc_cls("ERR_CELERY_OOM: GPU VRAM limit exceeded (clamped at 14GB)")
    elif force_fail == "TIMEOUT":
        time.sleep(6.0)
    elif force_fail in ("MOCK", "BENCHMARK", "FAKE"):
        import uuid
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
                    "bbox2d": {"ymin": 0.1, "xmin": 0.1, "ymax": 0.5, "xmax": 0.5},
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

    # 2. 이미지 파일 디코딩
    if not os.path.exists(temp_image_path):
        raise FileNotFoundError(f"임시 이미지 파일이 존재하지 않습니다: {temp_image_path}")

    image = cv2.imread(temp_image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("유효하지 않은 이미지 파일입니다.")

    # 3. 비전 파이프라인 로드 및 추론 수행
    try:
        from src.api.v1.endpoints.vision import get_pipeline
        pipeline = get_pipeline()
        result = pipeline.process_image(
            image=image,
            focal_length_mm=focal_length_mm,
            conf_threshold=conf_threshold,
        )
        return result
    except Exception as exc:
        # torch.cuda.OutOfMemoryError 발생 감지
        if "OutOfMemoryError" in type(exc).__name__ or "CUDA out of memory" in str(exc) or "ERR_CELERY_OOM" in str(exc):
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            raise MemoryError("ERR_CELERY_OOM: GPU VRAM limit exceeded") from exc
        raise

