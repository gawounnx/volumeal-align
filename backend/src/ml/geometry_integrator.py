"""RANSAC 평면 피팅 및 3D 기하 체적 적분 코어 엔진."""
from typing import Any, Dict, Optional, Tuple
import numpy as np
import open3d as o3d
from src.core.exceptions import PlaneNotFoundException, VolumeOutOfBoundsException


class NumericalVolumeIntegrator:
    """RANSAC 기준면 분리, 높이 차분 수치 적분 및 3D 바운딩 박스 연산 코어 [FR-003, FR-006]"""

    def fit_plane_ransac(
        self,
        points: np.ndarray,
        distance_threshold: float = 0.01,
        min_inlier_ratio: float = 0.40,
    ) -> Tuple[Dict[str, float], float]:
        """Open3D RANSAC 알고리즘 기반 기준 평면 방정식 (ax + by + cz + d = 0) 도출"""
        if len(points) < 100:
            raise PlaneNotFoundException("평면 피팅을 위한 점군의 수가 부족합니다.")

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))

        # 1차 기본 임계값 피팅 시도
        plane_model, inliers = pcd.segment_plane(
            distance_threshold=distance_threshold,
            ransac_n=3,
            num_iterations=1000,
        )
        inlier_ratio = float(len(inliers)) / float(len(points))

        # [FR-003, Section 14] 단안 깊이 추정 노이즈 및 촬영 각도(사선/탑뷰) 대응 적응형 RANSAC (0.015 -> 0.02 -> 0.025 -> 0.03)
        if inlier_ratio < min_inlier_ratio:
            adaptive_thresholds = [0.015, 0.02, 0.025, 0.03]
            for th in adaptive_thresholds:
                if th <= distance_threshold:
                    continue
                p_model, cur_inliers = pcd.segment_plane(
                    distance_threshold=th,
                    ransac_n=3,
                    num_iterations=1000,
                )
                cur_ratio = float(len(cur_inliers)) / float(len(points))
                if cur_ratio >= min_inlier_ratio:
                    plane_model = p_model
                    inlier_ratio = cur_ratio
                    break

        if inlier_ratio < min_inlier_ratio:
            raise PlaneNotFoundException(
                f"평면 신뢰도 미달: 인라이어 비율({inlier_ratio:.2%})이 기준치({min_inlier_ratio:.2%})보다 낮습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.",
                code="ERR_PLANE_NOT_FOUND",
            )

        a, b, c, d = plane_model
        norm = np.sqrt(a * a + b * b + c * c)
        if norm > 1e-8:
            a, b, c, d = a / norm, b / norm, c / norm, d / norm

        if d > 0:
            a, b, c, d = -a, -b, -c, -d

        return {"a": float(a), "b": float(b), "c": float(c), "d": float(d)}, inlier_ratio

    def integrate_height_difference(
        self,
        z_table: np.ndarray,
        z_food: np.ndarray,
        mask: np.ndarray,
        pixel_area_m2: float,
    ) -> float:
        """식품 높이 차분 수치 적분: V = ∬ (z_table - z_food) dx dy (단위: cm³)"""
        height_diff_m = np.maximum(0.0, z_table - z_food)
        masked_diff = height_diff_m[mask]

        volume_m3 = float(np.sum(masked_diff) * pixel_area_m2)
        volume_cm3 = volume_m3 * 1e6  # 1 m³ = 1,000,000 cm³

        return self.validate_volume_bounds(volume_cm3)

    def validate_volume_bounds(self, volume_cm3: float) -> float:
        """[BR-VAL-003] 최소/최대 체적 유효 범위 검증 (5cm³ ~ 5000cm³)"""
        if not np.isfinite(volume_cm3) or volume_cm3 < 5.0 or volume_cm3 > 5000.0:
            raise VolumeOutOfBoundsException(volume_cm3)
        return volume_cm3

    def compute_3d_oriented_bounding_box(self, points: np.ndarray) -> Dict[str, Any]:
        """Three.js 렌더링용 3D Bounding Box (중심, 크기, 8개 정점 좌표) 연산"""
        if len(points) == 0:
            zeros = {"x": 0.0, "y": 0.0, "z": 0.0}
            return {"center": zeros, "dimensions": zeros, "rotations": zeros, "vertices": []}

        min_bound = np.min(points, axis=0)
        max_bound = np.max(points, axis=0)
        center = (min_bound + max_bound) / 2.0
        dimensions = max_bound - min_bound

        x_min, y_min, z_min = min_bound
        x_max, y_max, z_max = max_bound
        vertices = [
            {"x": float(x_min), "y": float(y_min), "z": float(z_min)},
            {"x": float(x_max), "y": float(y_min), "z": float(z_min)},
            {"x": float(x_max), "y": float(y_max), "z": float(z_min)},
            {"x": float(x_min), "y": float(y_max), "z": float(z_min)},
            {"x": float(x_min), "y": float(y_min), "z": float(z_max)},
            {"x": float(x_max), "y": float(y_min), "z": float(z_max)},
            {"x": float(x_max), "y": float(y_max), "z": float(z_max)},
            {"x": float(x_min), "y": float(y_max), "z": float(z_max)},
        ]

        return {
            "center": {"x": float(center[0]), "y": float(center[1]), "z": float(center[2])},
            "dimensions": {"x": float(dimensions[0]), "y": float(dimensions[1]), "z": float(dimensions[2])},
            "rotations": {"x": 0.0, "y": 0.0, "z": 0.0},
            "vertices": vertices,
        }

    def downsample_voxel_grid(
        self,
        points: np.ndarray,
        colors: Optional[np.ndarray] = None,
        leaf_size: float = 0.005,
        max_points: int = 5000,
    ) -> Dict[str, Any]:
        """WebGL 메모리 보호를 위한 Open3D Voxel Grid 필터링 (최대 5,000점) [FR-006]"""
        if len(points) == 0:
            return {"count": 0, "positions": [], "colors": []}

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))

        if colors is not None and len(colors) == len(points):
            pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64))
        else:
            default_colors = np.full((len(points), 3), 0.8, dtype=np.float64)
            pcd.colors = o3d.utility.Vector3dVector(default_colors)

        downsampled = pcd.voxel_down_sample(voxel_size=leaf_size)
        down_points = np.asarray(downsampled.points, dtype=np.float32)
        down_colors = np.asarray(downsampled.colors, dtype=np.float32)

        if len(down_points) > max_points:
            stride = int(np.ceil(len(down_points) / max_points))
            down_points = down_points[::stride][:max_points]
            down_colors = down_colors[::stride][:max_points]

        return {
            "count": int(len(down_points)),
            "positions": down_points.flatten().tolist(),
            "colors": down_colors.flatten().tolist(),
        }


# ==============================================================================
# VoluMeal-Align 서비스 레이어 연동 표준 3D 기하 체적 적분 인터페이스 (최상위 함수)
# ==============================================================================
def compute_food_volume_and_mass(
    depth_map: np.ndarray,
    mask: np.ndarray,
    intrinsics: dict,
    density_g_per_cm3: float = 0.80,
) -> dict:
    """단안 깊이 맵과 2D 분할 마스크를 기반으로 3D 미소 체적(Riemann sum) 적분을 수행합니다."""
    fx = float(intrinsics.get("fx", 600.0))
    fy = float(intrinsics.get("fy", 600.0))

    active_indices = np.argwhere(mask)
    if len(active_indices) == 0:
        return {"volume_cm3": 0.0, "mass_g": 0.0, "valid_voxels": 0}

    masked_depths = depth_map[mask]
    valid_depth_mask = masked_depths > 0.05
    valid_depths = masked_depths[valid_depth_mask]

    if len(valid_depths) == 0:
        return {"volume_cm3": 0.0, "mass_g": 0.0, "valid_voxels": 0}

    # 기준 바닥면 깊이 추정 (상위 95 백분위수)
    z_floor = float(np.percentile(valid_depths, 95))
    delta_h = np.maximum(0.0, z_floor - valid_depths)

    # 핀홀 투영 기하 기반 미소 단면적: dA = (Z^2 / (fx * fy))
    pixel_area_m2 = (valid_depths ** 2) / (fx * fy)
    volume_m3 = np.sum(delta_h * pixel_area_m2)

    volume_cm3 = float(volume_m3 * 1.0e6)
    mass_g = float(volume_cm3 * density_g_per_cm3)

    return {
        "volume_cm3": volume_cm3,
        "mass_g": mass_g,
        "valid_voxels": int(len(valid_depths)),
    }
