"""참조 물체(체커보드, 신용카드, 동전) 기반 카메라 초점거리 및 깊이 스케일 인자(s) 수치 역투영 캘리브레이터 [FR-001, FR-003]."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from src.ml.camera_utils import CameraGeometryUtils


# ISO/IEC 7810 ID-1 표준 신용카드 규격 (단위: 미터)
CREDIT_CARD_WIDTH_M = 0.08560
CREDIT_CARD_HEIGHT_M = 0.05398
CREDIT_CARD_DIAG_M = float(np.sqrt(CREDIT_CARD_WIDTH_M ** 2 + CREDIT_CARD_HEIGHT_M ** 2))

# 표준 동전 규격 (지름, 단위: 미터)
COIN_DIAMETERS_M = {
    "krw_500": 0.0265,
    "krw_100": 0.0240,
    "krw_50": 0.0216,
    "krw_10": 0.0180,
    "us_quarter": 0.02426,
    "us_nickel": 0.02121,
    "us_penny": 0.01905,
}


@dataclass
class ScaleCalibrationResult:
    """깊이 스케일 보정 결과 DTO."""
    scale_factor: float
    reference_type: str
    focal_length_px: float
    raw_reference_size_m: float
    known_reference_size_m: float
    confidence: float
    details: Dict[str, Union[float, str, List[float]]]


class ReferenceObjectScaleCalibrator:
    """단안 깊이 맵의 미터/cm 스케일 보정 코어 엔진 [FR-001, FR-003].

    카메라 광학계(Pinhole) 역투영 기하학을 바탕으로, 이미지 내에 포함된
    체커보드, 신용카드, 동전 등의 알려진 물리적 치수를 기준으로
    원시 깊이 추정치 Z_raw를 실제 물리적 거리 Z_metric = s * Z_raw로 변환하는
    스케일 인자 s를 수치적으로 역투영 도출합니다.
    """

    def __init__(self, default_fov_degrees: float = 72.0):
        self.default_fov_degrees = default_fov_degrees

    @staticmethod
    def backproject_pixel(
        u: float,
        v: float,
        z: float,
        k_matrix: np.ndarray,
    ) -> np.ndarray:
        """단일 픽셀 좌표 (u, v)와 깊이 Z를 3D 카메라 좌표계 점 (X, Y, Z)로 역투영."""
        fx = k_matrix[0, 0]
        fy = k_matrix[1, 1]
        cx = k_matrix[0, 2]
        cy = k_matrix[1, 2]
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy
        return np.array([x, y, z], dtype=np.float64)

    def calibrate_from_checkerboard(
        self,
        image_bgr: np.ndarray,
        depth_map: np.ndarray,
        pattern_size: Tuple[int, int] = (7, 7),
        square_size_m: float = 0.025,
        k_matrix: Optional[np.ndarray] = None,
    ) -> Optional[ScaleCalibrationResult]:
        """체커보드 격자 패턴 기반 정밀 카메라 f_px 및 깊이 스케일 인자(s) 역투영 도출.

        Args:
            image_bgr: BGR 입력 이미지
            depth_map: Depth Anything v2 원시 깊이 맵
            pattern_size: 체커보드 내부 코너 수 (cols, rows)
            square_size_m: 격자 한 칸의 물리적 크기 (m)
            k_matrix: 카메라 내부 행렬 (없을 경우 72도 화각 기준 자동 산출)
        """
        h, w = depth_map.shape
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        found, corners = cv2.findChessboardCorners(
            gray,
            pattern_size,
            flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE,
        )

        if not found or corners is None:
            return None

        # 코너 서브픽셀 정밀화
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        corners = corners.reshape(-1, 2)

        if k_matrix is None:
            f_px = CameraGeometryUtils.compute_focal_length_px(w, fov_degrees=self.default_fov_degrees)
            k_matrix = CameraGeometryUtils.compute_intrinsic_matrix(
                image_width=w,
                image_height=h,
                fov_degrees=self.default_fov_degrees,
            )
        else:
            f_px = float(k_matrix[0, 0])

        cols, rows = pattern_size
        # 3D 점 역투영
        pts_3d = []
        for u, v in corners:
            ui = int(np.clip(round(u), 0, w - 1))
            vi = int(np.clip(round(v), 0, h - 1))
            z_val = float(depth_map[vi, ui])
            pt = self.backproject_pixel(u, v, z_val, k_matrix)
            pts_3d.append(pt)
        pts_3d = np.array(pts_3d)  # (N, 3)

        # 인접 코너 사이의 3D 유클리드 거리 수집
        raw_distances = []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                # 가로 인접
                if c + 1 < cols:
                    idx_right = r * cols + (c + 1)
                    d = np.linalg.norm(pts_3d[idx] - pts_3d[idx_right])
                    if d > 1e-6:
                        raw_distances.append(d)
                # 세로 인접
                if r + 1 < rows:
                    idx_down = (r + 1) * cols + c
                    d = np.linalg.norm(pts_3d[idx] - pts_3d[idx_down])
                    if d > 1e-6:
                        raw_distances.append(d)

        if not raw_distances:
            return None

        raw_dist_arr = np.array(raw_distances)
        # 최소자승법(Least-Squares): s * L_raw = square_size_m
        # s = sum(L_raw * square_size_m) / sum(L_raw^2)
        scale_factor = float(np.sum(raw_dist_arr * square_size_m) / np.sum(raw_dist_arr ** 2))
        avg_raw_dist = float(np.mean(raw_dist_arr))

        return ScaleCalibrationResult(
            scale_factor=scale_factor,
            reference_type="checkerboard",
            focal_length_px=f_px,
            raw_reference_size_m=avg_raw_dist,
            known_reference_size_m=square_size_m,
            confidence=0.98,
            details={
                "num_corners": int(len(corners)),
                "pattern_size": f"{cols}x{rows}",
                "mean_raw_edge_m": avg_raw_dist,
                "target_square_size_m": square_size_m,
            },
        )

    def calibrate_from_card_quad(
        self,
        corners_2d: np.ndarray,
        depth_map: np.ndarray,
        k_matrix: Optional[np.ndarray] = None,
    ) -> ScaleCalibrationResult:
        """4개 모서리(2D)를 갖는 표준 신용카드 기반 깊이 스케일 인자(s) 역투영 도출.

        corners_2d: shape (4, 2) 시계방향 또는 반시계방향 4개 꼭짓점 [[u0, v0], [u1, v1], [u2, v2], [u3, v3]]
        """
        h, w = depth_map.shape
        if k_matrix is None:
            f_px = CameraGeometryUtils.compute_focal_length_px(w, fov_degrees=self.default_fov_degrees)
            k_matrix = CameraGeometryUtils.compute_intrinsic_matrix(
                image_width=w,
                image_height=h,
                fov_degrees=self.default_fov_degrees,
            )
        else:
            f_px = float(k_matrix[0, 0])

        corners_3d = []
        for u, v in corners_2d:
            ui = int(np.clip(round(u), 0, w - 1))
            vi = int(np.clip(round(v), 0, h - 1))
            z = float(depth_map[vi, ui])
            corners_3d.append(self.backproject_pixel(u, v, z, k_matrix))
        corners_3d = np.array(corners_3d)

        # 4개 변 및 2개 대각선 길이 산출
        edge_01 = np.linalg.norm(corners_3d[0] - corners_3d[1])
        edge_12 = np.linalg.norm(corners_3d[1] - corners_3d[2])
        edge_23 = np.linalg.norm(corners_3d[2] - corners_3d[3])
        edge_30 = np.linalg.norm(corners_3d[3] - corners_3d[0])
        diag_02 = np.linalg.norm(corners_3d[0] - corners_3d[2])
        diag_13 = np.linalg.norm(corners_3d[1] - corners_3d[3])

        # 가로(긴 변), 세로(짧은 변) 분리 매칭
        edges = [edge_01, edge_12, edge_23, edge_30]
        edges.sort()
        raw_height = (edges[0] + edges[1]) / 2.0
        raw_width = (edges[2] + edges[3]) / 2.0
        raw_diag = (diag_02 + diag_13) / 2.0

        scales = [
            CREDIT_CARD_WIDTH_M / max(raw_width, 1e-6),
            CREDIT_CARD_HEIGHT_M / max(raw_height, 1e-6),
            CREDIT_CARD_DIAG_M / max(raw_diag, 1e-6),
        ]
        scale_factor = float(np.median(scales))

        return ScaleCalibrationResult(
            scale_factor=scale_factor,
            reference_type="credit_card",
            focal_length_px=f_px,
            raw_reference_size_m=float(raw_width),
            known_reference_size_m=CREDIT_CARD_WIDTH_M,
            confidence=0.95,
            details={
                "raw_width_m": float(raw_width),
                "raw_height_m": float(raw_height),
                "raw_diag_m": float(raw_diag),
                "width_scale": scales[0],
                "height_scale": scales[1],
                "diag_scale": scales[2],
            },
        )

    def calibrate_from_coin_circle(
        self,
        center_uv: Tuple[float, float],
        radius_px: float,
        depth_map: np.ndarray,
        coin_type: str = "krw_500",
        k_matrix: Optional[np.ndarray] = None,
    ) -> ScaleCalibrationResult:
        """원형 동전(중심, 픽셀 반지름) 기반 깊이 스케일 인자(s) 역투영 도출."""
        h, w = depth_map.shape
        known_diameter_m = COIN_DIAMETERS_M.get(coin_type, COIN_DIAMETERS_M["krw_500"])

        if k_matrix is None:
            f_px = CameraGeometryUtils.compute_focal_length_px(w, fov_degrees=self.default_fov_degrees)
            k_matrix = CameraGeometryUtils.compute_intrinsic_matrix(
                image_width=w,
                image_height=h,
                fov_degrees=self.default_fov_degrees,
            )
        else:
            f_px = float(k_matrix[0, 0])

        u_c, v_c = center_uv
        angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        pts_3d = []
        for th in angles:
            u = u_c + radius_px * np.cos(th)
            v = v_c + radius_px * np.sin(th)
            ui = int(np.clip(round(u), 0, w - 1))
            vi = int(np.clip(round(v), 0, h - 1))
            z = float(depth_map[vi, ui])
            pts_3d.append(self.backproject_pixel(u, v, z, k_matrix))
        pts_3d = np.array(pts_3d)

        diameters = []
        for i in range(4):
            d = np.linalg.norm(pts_3d[i] - pts_3d[i + 4])
            diameters.append(d)

        raw_diameter_m = float(np.mean(diameters))
        scale_factor = float(known_diameter_m / max(raw_diameter_m, 1e-6))

        return ScaleCalibrationResult(
            scale_factor=scale_factor,
            reference_type=f"coin_{coin_type}",
            focal_length_px=f_px,
            raw_reference_size_m=raw_diameter_m,
            known_reference_size_m=known_diameter_m,
            confidence=0.92,
            details={
                "coin_type": coin_type,
                "radius_px": float(radius_px),
                "raw_diameter_m": raw_diameter_m,
                "known_diameter_m": known_diameter_m,
            },
        )

    def detect_and_calibrate(
        self,
        image_bgr: np.ndarray,
        depth_map: np.ndarray,
        k_matrix: Optional[np.ndarray] = None,
    ) -> Optional[ScaleCalibrationResult]:
        """이미지 내에서 참조 물체를 순차 자동 탐색하여 깊이 스케일 인자(s)를 도출."""
        # 1. 체커보드 패턴 시도
        for pattern in [(7, 7), (6, 9), (8, 6), (5, 5), (6, 8)]:
            res = self.calibrate_from_checkerboard(
                image_bgr, depth_map, pattern_size=pattern, k_matrix=k_matrix
            )
            if res is not None:
                return res

        # 2. 동전 형태 원형 탐색 (Hough Circles)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=50,
            param1=100,
            param2=40,
            minRadius=15,
            maxRadius=120,
        )
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (cx, cy, r) in circles:
                if 15 <= r <= 100:
                    return self.calibrate_from_coin_circle(
                        (float(cx), float(cy)), float(r), depth_map, coin_type="krw_500", k_matrix=k_matrix
                    )

        return None
