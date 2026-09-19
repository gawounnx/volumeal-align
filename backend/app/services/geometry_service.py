"""기하 연산 및 초점거리 보정 서비스 [FR-001, FR-003, BR-VAL-001].

Requirement Specification Section 11.1 단위 테스트 대상 모듈.
"""
from typing import Optional, Tuple
import numpy as np
from src.ml.camera_utils import CameraGeometryUtils


def calculate_focal_length_px(image_width: int, fov_degrees: float = 72.0) -> float:
    """[BR-VAL-001] EXIF 부재 시 35mm 환산 72도 화각 기준 f_px 산출:
    f_px = W / (2 * tan(72° / 2)) = W / (2 * tan(36°))
    """
    return CameraGeometryUtils.compute_focal_length_px(image_width, fov_degrees=fov_degrees)


compute_focal_length_px = calculate_focal_length_px


class GeometryService:
    """기하 파라미터 및 핀홀 카메라 모델 서비스."""

    @staticmethod
    def compute_intrinsic_matrix(
        focal_length_mm: Optional[float] = None,
        image_width: int = 640,
        image_height: int = 480,
        sensor_width_mm: Optional[float] = None,
        fov_degrees: float = 72.0,
    ) -> np.ndarray:
        return CameraGeometryUtils.compute_intrinsic_matrix(
            focal_length_mm=focal_length_mm,
            image_width=image_width,
            image_height=image_height,
            sensor_width_mm=sensor_width_mm,
            fov_degrees=fov_degrees,
        )
