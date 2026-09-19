import numpy as np
import pytest
from src.core.exceptions import PlaneNotFoundException, VolumeOutOfBoundsException
from src.ml.camera_utils import CameraGeometryUtils
from src.ml.geometry_integrator import NumericalVolumeIntegrator


def test_ransac_plane_fitting_synthetic():
    """가상 평면 점군(5000개)에서 RANSAC 평면 피팅 인라이어 비율 및 법선 벡터 정확도 검증"""
    integrator = NumericalVolumeIntegrator()
    np.random.seed(42)
    x = np.random.uniform(-0.3, 0.3, 5000)
    y = np.random.uniform(-0.3, 0.3, 5000)
    z = np.full_like(x, 0.5) + np.random.normal(0, 0.002, 5000)
    points = np.stack([x, y, z], axis=-1)

    plane_eq, inlier_ratio = integrator.fit_plane_ransac(points, distance_threshold=0.01)

    assert inlier_ratio >= 0.90
    normal = np.array([plane_eq["a"], plane_eq["b"], plane_eq["c"]])
    normal = normal / np.linalg.norm(normal)
    assert abs(abs(normal[2]) - 1.0) < 0.05


def test_exact_cube_numerical_integration():
    """이상적 직육면체 합성 데이터 (10cm x 10cm x 5cm = 500cm³) 적분 오차율 <= 2.5% 검증"""
    integrator = NumericalVolumeIntegrator()
    grid_res = 0.002  # 2mm 격자 해상도
    x = np.arange(-0.05, 0.05, grid_res)
    y = np.arange(-0.05, 0.05, grid_res)
    xx, yy = np.meshgrid(x, y)

    z_table = np.full_like(xx, 0.60)  # 테이블 기준면 깊이 0.60m
    z_food = np.full_like(xx, 0.55)   # 음식 상단 깊이 0.55m (높이 0.05m = 5cm)
    mask = np.ones_like(xx, dtype=bool)

    volume_cm3 = integrator.integrate_height_difference(
        z_table=z_table,
        z_food=z_food,
        mask=mask,
        pixel_area_m2=grid_res * grid_res,
    )

    assert pytest.approx(volume_cm3, rel=0.025) == 500.0


def test_volume_boundary_rejection():
    """유효 체적 임계값 (5cm³ 미만 또는 5000cm³ 초과) 차단 예외 검증"""
    integrator = NumericalVolumeIntegrator()
    with pytest.raises(VolumeOutOfBoundsException):
        integrator.validate_volume_bounds(3.5)

    with pytest.raises(VolumeOutOfBoundsException):
        integrator.validate_volume_bounds(5500.0)


def test_camera_backprojection():
    """주점 (cx, cy)에서 거리 Z=0.5m 역투영 시 X=0, Y=0 도출 검증"""
    k_matrix = CameraGeometryUtils.compute_intrinsic_matrix(
        focal_length_mm=26.0,
        image_width=640,
        image_height=480,
    )
    depth_map = np.full((480, 640), 0.5, dtype=np.float32)
    center_mask = np.zeros((480, 640), dtype=bool)
    center_mask[240, 320] = True

    points, _ = CameraGeometryUtils.backproject_depth_to_pointcloud(depth_map, k_matrix, center_mask)
    assert len(points) == 1
    assert abs(points[0][0]) < 1e-4
    assert abs(points[0][1]) < 1e-4
    assert abs(points[0][2] - 0.5) < 1e-4


@pytest.mark.parametrize("point_count", [0, 99])
def test_plane_rejection_for_insufficient_points(point_count):
    integrator = NumericalVolumeIntegrator()
    points = np.zeros((point_count, 3), dtype=np.float64)

    with pytest.raises(PlaneNotFoundException) as exc_info:
        integrator.fit_plane_ransac(points)

    assert exc_info.value.status_code == 422
    error = exc_info.value.detail["error"]
    assert error["code"] in ("ERR_PLANE_NOT_FOUND", "ERR_GEOMETRY_PLANE_NOT_FOUND")
    assert "점군의 수가 부족" in error["message"]


def test_geometry_fpx():
    """[BR-VAL-001, Section 11.1] EXIF 부재 시 35mm 환산 72도 기반 f_px 산출 오차 <= 1% 검증."""
    from app.services.geometry_service import calculate_focal_length_px
    width = 1920
    f_px = calculate_focal_length_px(image_width=width, fov_degrees=72.0)
    expected_f_px = width / (2.0 * np.tan(np.radians(36.0)))
    error_ratio = abs(f_px - expected_f_px) / expected_f_px
    assert error_ratio <= 0.01  # 명세서 11.1 단위 테스트 허용 오차 <= 1%
    assert abs(f_px - expected_f_px) < 1e-4


@pytest.mark.parametrize("volume_cm3", [3.5, 5500.0])
def test_volume_rejection_preserves_error_payload(volume_cm3):
    integrator = NumericalVolumeIntegrator()

    with pytest.raises(VolumeOutOfBoundsException) as exc_info:
        integrator.validate_volume_bounds(volume_cm3)

    assert exc_info.value.status_code == 422
    error = exc_info.value.detail["error"]
    assert error["code"] == "ERR_VOLUME_OUT_OF_BOUNDS"
    assert f"{volume_cm3:.2f}" in error["message"]
    assert error["details"][0]["field"] == "volume_cm3"
