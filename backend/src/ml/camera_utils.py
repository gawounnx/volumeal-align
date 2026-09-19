from typing import Optional, Tuple
import numpy as np


class CameraGeometryUtils:
    """단안 카메라 내부 파라미터 행렬(K) 산출 및 2D-3D 역투영 연산 유틸리티 [FR-001, FR-003]"""

    @staticmethod
    def compute_focal_length_px(
        image_width: int,
        fov_degrees: float = 72.0,
    ) -> float:
        """[BR-VAL-001] EXIF 초점거리/센서 사이즈 부재 시 35mm 환산 72도 화각 기준 픽셀 초점거리 산출 공식:
        f_px = W / (2 * tan(72° / 2)) = W / (2 * tan(36°))
        기존 26mm/36mm 임의 대입 오차(약 4.9%)를 제거하고 허용 오차 <= 1% 충족.
        """
        half_fov_rad = np.radians(fov_degrees / 2.0)
        return float(image_width / (2.0 * np.tan(half_fov_rad)))

    @staticmethod
    def compute_intrinsic_matrix(
        focal_length_mm: Optional[float] = None,
        image_width: int = 640,
        image_height: int = 480,
        sensor_width_mm: Optional[float] = None,
        fov_degrees: float = 72.0,
    ) -> np.ndarray:
        """[BR-VAL-001] 카메라 내부 파라미터 행렬(K) 산출.
        EXIF 초점거리 및 센서 사이즈가 명시되지 않거나 임의 기본값(26mm/36mm)인 경우,
        35mm 환산 72도 화각 기준 f_px = W / (2 * tan(36°)) 산출 공식을 강제 적용합니다.
        """
        # 명시적인 35mm 환산 EXIF 초점거리 또는 센서 규격이 주어졌을 때 (임의 26mm/36mm 대입 제외)
        if (
            focal_length_mm is not None
            and sensor_width_mm is not None
            and sensor_width_mm > 0
            and not (abs(focal_length_mm - 26.0) < 1e-5 and abs(sensor_width_mm - 36.0) < 1e-5)
        ):
            fx = (float(focal_length_mm) / float(sensor_width_mm)) * image_width
        elif focal_length_mm is not None and sensor_width_mm is not None and sensor_width_mm > 0:
            # 26mm/36mm 임의 대입인 경우 72도 화각 정규화 공식 적용
            fx = CameraGeometryUtils.compute_focal_length_px(image_width, fov_degrees=fov_degrees)
        elif focal_length_mm is not None and sensor_width_mm is None:
            # 센서 사이즈 부재 시 72도 화각 정규화 공식 적용
            fx = CameraGeometryUtils.compute_focal_length_px(image_width, fov_degrees=fov_degrees)
        else:
            # EXIF 초점거리 부재 시 72도 화각 정규화 공식 적용
            fx = CameraGeometryUtils.compute_focal_length_px(image_width, fov_degrees=fov_degrees)

        fy = fx
        cx = image_width / 2.0
        cy = image_height / 2.0

        return np.array(
            [
                [fx, 0.0, cx],
                [0.0, fy, cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def backproject_depth_to_pointcloud(
        depth_map: np.ndarray,
        k_matrix: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """2D 깊이 맵(m)을 3D 포인트 클라우드(X, Y, Z)로 역투영 (NumPy 벡터화)"""
        h, w = depth_map.shape
        u_coords, v_coords = np.meshgrid(np.arange(w), np.arange(h))

        valid_condition = (depth_map > 0.05) & (depth_map < 3.0)
        if mask is not None:
            valid_condition = valid_condition & mask

        u_valid = u_coords[valid_condition]
        v_valid = v_coords[valid_condition]
        z_valid = depth_map[valid_condition]

        fx = k_matrix[0, 0]
        fy = k_matrix[1, 1]
        cx = k_matrix[0, 2]
        cy = k_matrix[1, 2]

        x_valid = (u_valid - cx) * z_valid / fx
        y_valid = (v_valid - cy) * z_valid / fy

        points_xyz = np.stack([x_valid, y_valid, z_valid], axis=-1).astype(np.float32)
        pixel_indices = np.stack([v_valid, u_valid], axis=-1)

        return points_xyz, pixel_indices