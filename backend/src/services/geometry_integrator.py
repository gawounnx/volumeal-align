"""3D 핀홀 카메라 기하 체적 적분기 (레거시 호환 및 물리적 상한선 가드레일) [FR-003, BR-VAL-003]."""
import numpy as np
from src.ml.geometry_integrator import NumericalVolumeIntegrator


class GeometryIntegrator:
    """단안 깊이 맵과 세그멘테이션 마스크 기반 체적 수치 적분기 (레거시 호환)."""

    def __init__(self, fx: float = 600.0, fy: float = 600.0, max_valid_volume: float = 5000.0) -> None:
        self.fx = fx
        self.fy = fy
        self.max_valid_volume = max_valid_volume  # 1인분 식단 최대 허용 체적 (cm^3)
        self.numerical_integrator = NumericalVolumeIntegrator()

        # 식품별 기준 밀도 (g/cm^3)
        self.density_map = {
            "apple": 0.85,
            "banana": 0.92,
            "bibimbap": 1.15,
            "bulgogi": 1.20,
            "kimchi_stew": 1.05,
            "pork_belly": 1.10,
            "ramen": 1.02,
            "soybean_paste_stew": 1.05,
            "spinach_namul": 0.80,
        }

    def compute_volume_and_mass(
        self,
        depth_map: np.ndarray,
        mask: np.ndarray,
        class_name: str,
    ) -> tuple[float, float]:
        """핀홀 투영 기하 적분 및 밀도 기반 질량 산출 [Ref: BR-VAL-003]."""
        valid_pixels = np.where(mask > 0)
        if len(valid_pixels[0]) == 0:
            return 0.0, 0.0

        depth_values = depth_map[valid_pixels]
        # 깊이 이상치 클리핑 (0.2m ~ 1.5m)
        clipped_depth_m = np.clip(depth_values, 0.2, 1.5)

        # Ref: FR-003, 임의 15% 두께 휴리스틱을 제거하고, 픽셀별 카메라 광선 절두체 미소 체적 적분 수행
        # 미소 면적 dx*dy = (z/fx) * (z/fy), 높이 차분을 반영한 체적 수치 적분 (m^3 -> cm^3)
        pixel_area_m2 = (clipped_depth_m / self.fx) * (clipped_depth_m / self.fy)
        max_depth_m = np.max(clipped_depth_m)
        height_diff_m = np.maximum(max_depth_m - clipped_depth_m, 0.01)  # 최소 1cm 표면 기복 반영
        volume_m3 = float(np.sum(pixel_area_m2 * height_diff_m))
        raw_volume = volume_m3 * 1e6  # m^3 -> cm^3

        # [BR-VAL-003] 정규 NumericalVolumeIntegrator 가드레일 유효 범위 검증 (5 ~ 5000 cm^3)
        self.numerical_integrator.validate_volume_bounds(raw_volume)

        density = self.density_map.get(class_name.lower(), 1.0)
        mass_g = raw_volume * density

        return round(raw_volume, 2), round(mass_g, 2)
