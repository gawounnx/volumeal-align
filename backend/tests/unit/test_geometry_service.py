"""단위 테스트: 기하 연산, RANSAC 체적 적분 및 영양소 비례 계산 [FR-001, FR-003, FR-004, Section 11.1]."""
import json
import numpy as np
import pytest
from app.services.geometry_service import calculate_focal_length_px
from app.ml.ransac_integrator import RansacIntegrator
from src.core.exceptions import PlaneNotFoundException
from src.services.nutrition_service import NutritionService


def test_geometry_fpx():
    """[BR-VAL-001, Section 11.1] 72도 화각 기준 f_px 산출 오차 <= 1% 검증."""
    width = 1920
    f_px = calculate_focal_length_px(image_width=width, fov_degrees=72.0)
    expected_f_px = width / (2.0 * np.tan(np.radians(36.0)))
    error_ratio = abs(f_px - expected_f_px) / expected_f_px
    assert error_ratio <= 0.01  # 명세서 11.1 단위 테스트 허용 오차 <= 1%
    assert abs(f_px - expected_f_px) < 1e-4


def test_ransac_volume():
    """[FR-003, Section 11.1] RANSAC 피팅 (법선 벡터 오차 <= 1.5도, 체적 오차 <= 2.0%) 및 Inlier 40% 미만 시 422 반환 검증."""
    integrator = RansacIntegrator()

    # 1. 법선 벡터 오차 <= 1.5도 검증 (합성 평면 z = 0.50m)
    np.random.seed(42)
    x = np.random.uniform(-0.3, 0.3, 5000)
    y = np.random.uniform(-0.3, 0.3, 5000)
    z = np.full_like(x, 0.50) + np.random.normal(0, 0.001, 5000)
    points = np.stack([x, y, z], axis=-1)

    plane_eq, inlier_ratio = integrator.fit_plane_ransac(points, distance_threshold=0.01)
    assert inlier_ratio >= 0.90
    normal = np.array([plane_eq["a"], plane_eq["b"], plane_eq["c"]])
    normal = normal / np.linalg.norm(normal)
    dot = abs(np.dot(normal, np.array([0.0, 0.0, 1.0])))
    angle_deg = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
    assert angle_deg <= 1.5  # 기대 결과: 법선 벡터 각도 오차 <= 1.5도

    # 2. 체적 적분 오차 <= 2.0% 검증 (10cm x 10cm x 5cm = 500 cm³)
    grid_res = 0.002
    x_grid = np.arange(-0.05, 0.05, grid_res)
    y_grid = np.arange(-0.05, 0.05, grid_res)
    xx, yy = np.meshgrid(x_grid, y_grid)
    z_table = np.full_like(xx, 0.60)
    z_food = np.full_like(xx, 0.55)  # 높이 0.05m = 5cm
    mask = np.ones_like(xx, dtype=bool)

    volume_cm3 = integrator.integrate_height_difference(
        z_table=z_table,
        z_food=z_food,
        mask=mask,
        pixel_area_m2=grid_res * grid_res,
    )
    vol_error_ratio = abs(volume_cm3 - 500.0) / 500.0
    assert vol_error_ratio <= 0.02  # 기대 결과: 체적 오차 <= 2.0%

    # 3. Inlier 40% 미만 시 422 (ERR_PLANE_NOT_FOUND) 반환 검증
    plane_pts = np.stack([
        np.random.uniform(-0.3, 0.3, 200),
        np.random.uniform(-0.3, 0.3, 200),
        np.full(200, 0.50) + np.random.normal(0, 0.001, 200),
    ], axis=-1)
    noise_pts = np.random.uniform(-1.0, 1.0, (800, 3))
    bad_points = np.vstack([plane_pts, noise_pts])

    with pytest.raises(PlaneNotFoundException) as exc_info:
        integrator.fit_plane_ransac(bad_points, min_inlier_ratio=0.40)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "ERR_PLANE_NOT_FOUND"


def test_nutrition_calc(tmp_path):
    """[FR-004, Section 11.1] 밀도(rho=0.85) 및 V=120 주입 시 중량 102g 및 매크로 영양소 정밀 비례 계산 검증."""
    catalog = [{"foodId": "FOOD_CHICKEN", "canonicalName": "닭가슴살볶음", "aliases": [], "interactionTags": []}]
    densities = [{"foodId": "FOOD_CHICKEN", "densityGCm3": 0.85, "densityStd": 0.05, "preparation": "cooked", "source": "measured"}]
    nutrients = [{
        "foodId": "FOOD_CHICKEN",
        "basisWeightG": 100.0,
        "caloriesKcal": 200.0,
        "carbsG": 30.0,
        "proteinG": 10.0,
        "fatG": 4.0,
        "sodiumMg": 150.0,
        "sourceFoodCode": "TEST_C01",
        "sourceVersion": "1.0",
    }]

    paths = []
    for name, rows in (("catalog", catalog), ("density", densities), ("nutrients", nutrients)):
        p = tmp_path / f"{name}.json"
        p.write_text(json.dumps(rows))
        paths.append(str(p))

    service = NutritionService(*paths)

    # V = 120 cm³, rho = 0.85 g/cm³ -> W = 102.0 g
    result = service.calculate("FOOD_CHICKEN", volume_cm3=120.0)

    assert result["weightG"] == 102.0
    assert result["densityGCm3"] == 0.85
    # 102g / 100g = 1.02 배 정밀 비례
    assert result["caloriesKcal"] == pytest.approx(204.0, abs=0.01)
    assert result["carbsG"] == pytest.approx(30.6, abs=0.01)
    assert result["proteinG"] == pytest.approx(10.2, abs=0.01)
    assert result["fatG"] == pytest.approx(4.08, abs=0.01)
    assert result["sodiumMg"] == pytest.approx(153.0, abs=0.01)

    # [FR-007, BR-VAL-004] 수동 보정 재계산(calculate_by_weight) 동일 일치 검증
    by_weight = service.calculate_by_weight("FOOD_CHICKEN", weight_g=102.0)
    assert by_weight["weightG"] == 102.0
    assert by_weight["volumeCm3"] == pytest.approx(120.0, abs=0.01)
    assert by_weight["caloriesKcal"] == pytest.approx(204.0, abs=0.01)
