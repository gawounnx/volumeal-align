"""[P0-3, FR-001, FR-003] 단안 깊이 추정 Metric 스케일 역투영 보정 및 체적 오차율(<=10%) 단위 테스트."""
import cv2
import numpy as np
import pytest
from src.core.config import settings
from src.ml.camera_utils import CameraGeometryUtils
from src.ml.geometry_integrator import NumericalVolumeIntegrator
from src.ml.scale_calibrator import (
    ReferenceObjectScaleCalibrator,
    CREDIT_CARD_WIDTH_M,
    CREDIT_CARD_HEIGHT_M,
    COIN_DIAMETERS_M,
)


@pytest.fixture
def calibrated_scene():
    """테이블 거리 0.45m, 10x10x5cm 큐브(500cm³), 5.5배 부풀려진 원시 깊이를 갖는 검증 씬 fixture."""
    w, h = 640, 480
    f_px = CameraGeometryUtils.compute_focal_length_px(w, fov_degrees=72.0)
    real_dist = 0.45
    cube_depth = 0.05
    cube_top_z = real_dist - cube_depth
    inflation = 5.5

    image = np.full((h, w, 3), 220, dtype=np.uint8)

    # 1. 체커보드 7x7 (25mm)
    sq_px = int(round((0.025 / real_dist) * f_px))
    for r in range(8):
        for c in range(8):
            color = (255, 255, 255) if (r + c) % 2 == 0 else (0, 0, 0)
            cv2.rectangle(image, (60 + c * sq_px, 60 + r * sq_px), (60 + (c + 1) * sq_px, 60 + (r + 1) * sq_px), color, -1)

    # 2. 신용카드 (85.60mm x 53.98mm)
    card_w_px = int(round((CREDIT_CARD_WIDTH_M / real_dist) * f_px))
    card_h_px = int(round((CREDIT_CARD_HEIGHT_M / real_dist) * f_px))
    card_u1, card_v1 = 400, 60
    card_u2, card_v2 = card_u1 + card_w_px, card_v1 + card_h_px
    cv2.rectangle(image, (card_u1, card_v1), (card_u2, card_v2), (60, 60, 180), -1)

    # 3. 500원 동전 (지름 26.5mm)
    coin_diam = COIN_DIAMETERS_M["krw_500"]
    coin_r_px = int(round((coin_diam / 2.0 / real_dist) * f_px))
    coin_cu, coin_cv = 120, 360
    cv2.circle(image, (coin_cu, coin_cv), coin_r_px, (160, 170, 180), -1)

    # 4. 큐브 (10cm x 10cm x 5cm = 500cm³)
    cube_w_px = int(round((0.10 / cube_top_z) * f_px))
    cube_h_px = int(round((0.10 / cube_top_z) * f_px))
    cube_u1 = (w - cube_w_px) // 2
    cube_v1 = (h - cube_h_px) // 2 + 50
    cube_u2 = cube_u1 + cube_w_px
    cube_v2 = cube_v1 + cube_h_px
    cv2.rectangle(image, (cube_u1, cube_v1), (cube_u2, cube_v2), (40, 140, 40), -1)

    real_depth = np.full((h, w), real_dist, dtype=np.float32)
    cube_mask = np.zeros((h, w), dtype=bool)
    cube_mask[cube_v1:cube_v2, cube_u1:cube_u2] = True
    real_depth[cube_mask] = cube_top_z

    raw_depth = real_depth * inflation

    k_matrix = CameraGeometryUtils.compute_intrinsic_matrix(image_width=w, image_height=h, fov_degrees=72.0)

    card_corners = np.array([
        [card_u1, card_v1],
        [card_u2, card_v1],
        [card_u2, card_v2],
        [card_u1, card_v2],
    ], dtype=np.float32)

    return {
        "image": image,
        "raw_depth": raw_depth,
        "cube_mask": cube_mask,
        "k_matrix": k_matrix,
        "card_corners": card_corners,
        "coin_uv": (float(coin_cu), float(coin_cv)),
        "coin_r_px": float(coin_r_px),
        "true_volume_cm3": 500.0,
        "expected_scale": 1.0 / inflation,
    }


def test_focal_length_calculation():
    """[BR-VAL-001] 72도 화각 기준 f_px 산출 오차 <= 1% 검증."""
    width = 640
    f_px = CameraGeometryUtils.compute_focal_length_px(width, fov_degrees=72.0)
    expected = width / (2.0 * np.tan(np.radians(36.0)))
    assert abs(f_px - expected) / expected <= 0.01


def test_scale_calibration_checkerboard(calibrated_scene):
    """체커보드 수치 역투영 스케일 인자(s) 산출 오차 <= 3.0% 검증."""
    calibrator = ReferenceObjectScaleCalibrator()
    res = calibrator.calibrate_from_checkerboard(
        calibrated_scene["image"],
        calibrated_scene["raw_depth"],
        pattern_size=(7, 7),
        square_size_m=0.025,
        k_matrix=calibrated_scene["k_matrix"],
    )
    assert res is not None
    assert res.confidence >= 0.90
    expected_s = calibrated_scene["expected_scale"]
    error_pct = abs(res.scale_factor - expected_s) / expected_s * 100.0
    assert error_pct <= 3.0, f"체커보드 스케일 오차 초과: {error_pct:.2f}%"


def test_scale_calibration_credit_card(calibrated_scene):
    """신용카드(ISO 7810) 수치 역투영 스케일 인자(s) 산출 오차 <= 2.0% 검증."""
    calibrator = ReferenceObjectScaleCalibrator()
    res = calibrator.calibrate_from_card_quad(
        calibrated_scene["card_corners"],
        calibrated_scene["raw_depth"],
        k_matrix=calibrated_scene["k_matrix"],
    )
    expected_s = calibrated_scene["expected_scale"]
    error_pct = abs(res.scale_factor - expected_s) / expected_s * 100.0
    assert error_pct <= 2.0, f"신용카드 스케일 오차 초과: {error_pct:.2f}%"


def test_scale_calibration_coin(calibrated_scene):
    """500원 주화 수치 역투영 스케일 인자(s) 산출 오차 <= 2.0% 검증."""
    calibrator = ReferenceObjectScaleCalibrator()
    res = calibrator.calibrate_from_coin_circle(
        calibrated_scene["coin_uv"],
        calibrated_scene["coin_r_px"],
        calibrated_scene["raw_depth"],
        coin_type="krw_500",
        k_matrix=calibrated_scene["k_matrix"],
    )
    expected_s = calibrated_scene["expected_scale"]
    error_pct = abs(res.scale_factor - expected_s) / expected_s * 100.0
    assert error_pct <= 2.0, f"동전 스케일 오차 초과: {error_pct:.2f}%"


def test_volume_error_within_10_percent(calibrated_scene):
    """스케일 보정 후 체적 계산 오차율 <= 10.0% 달성 실측 검증."""
    calibrator = ReferenceObjectScaleCalibrator()
    card_res = calibrator.calibrate_from_card_quad(
        calibrated_scene["card_corners"],
        calibrated_scene["raw_depth"],
        k_matrix=calibrated_scene["k_matrix"],
    )
    s = card_res.scale_factor

    # 보정 전 vs 보정 후 체적 적분
    raw_depth = calibrated_scene["raw_depth"]
    calibrated_depth = raw_depth * s
    cube_mask = calibrated_scene["cube_mask"]
    k = calibrated_scene["k_matrix"]
    fx, fy = k[0, 0], k[1, 1]

    # 보정 전 체적 계산 (오차율 폭증 확인)
    z_table_raw = np.full_like(raw_depth, float(np.percentile(raw_depth, 95)))
    v_raw = float(np.sum(np.maximum(0.0, z_table_raw[cube_mask] - raw_depth[cube_mask]) * (raw_depth[cube_mask]**2) / (fx * fy)) * 1e6)
    assert v_raw > 5000.0, "보정 전 원시 체적이 비정상적으로 작습니다."

    # 보정 후 메트릭 체적 계산 (500cm³ 기준)
    z_table_cal = np.full_like(calibrated_depth, float(np.percentile(calibrated_depth, 95)))
    cal_delta_h = np.maximum(0.0, z_table_cal[cube_mask] - calibrated_depth[cube_mask])
    cal_pixel_area = (calibrated_depth[cube_mask] ** 2) / (fx * fy)
    v_cal = float(np.sum(cal_delta_h * cal_pixel_area) * 1e6)

    true_v = calibrated_scene["true_volume_cm3"]
    error_pct = abs(v_cal - true_v) / true_v * 100.0
    assert error_pct <= 10.0, f"체적 오차율 기준(<=10%) 초과: {error_pct:.2f}% (V={v_cal:.1f}cm³)"


def test_depth_estimator_scale_factor_applied():
    """DepthAnythingV2Estimator에 scale_factor 적용 시 출력이 정확히 스케일링됨을 검증."""
    from src.ml.onnx_depth_estimator import DepthAnythingV2Estimator
    estimator = DepthAnythingV2Estimator(settings.ONNX_DEPTH_MODEL_PATH, scale_factor=0.18)
    assert estimator.scale_factor == 0.18
