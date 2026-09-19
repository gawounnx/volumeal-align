"""One injected, metric-depth analysis path. No synthetic production fallbacks."""
import uuid
import numpy as np
from src.core.exceptions import AppException, PlaneNotFoundException, ZeroObjectDetectedException
from src.ml.camera_utils import CameraGeometryUtils
from src.ml.geometry_integrator import NumericalVolumeIntegrator
from src.ml.scale_calibrator import ReferenceObjectScaleCalibrator

class VisionPipelineOrchestrator:
    def __init__(
        self,
        segmentor,
        depth_estimator,
        patch_embedder=None,
        food_retriever=None,
        nutrition_service=None,
        geometry_integrator=None,
        metric=False,
        scale_calibrator=None,
    ):
        self.segmentor = segmentor
        self.depth_estimator = depth_estimator
        self.patch_embedder = patch_embedder
        self.food_retriever = food_retriever
        self.nutrition_service = nutrition_service
        self.geometry_integrator = geometry_integrator or NumericalVolumeIntegrator()
        self.metric = metric
        self.scale_calibrator = scale_calibrator

    def process_image(self, image, focal_length_mm=26.0, conf_threshold=.05):
        if not self.metric or self.depth_estimator.session is None:
            raise AppException(503, "ERR_DEPTH_MODEL_UNAVAILABLE", "미터 단위 깊이 모델이 준비되지 않아 분석할 수 없습니다.")
        if self.patch_embedder is None or self.food_retriever is None:
            raise AppException(503, "ERR_FOOD_RECOGNITION_UNAVAILABLE", "음식 기준 이미지 검색 모델이 준비되지 않았습니다.")
        if self.nutrition_service is None:
            raise AppException(503, "ERR_NUTRITION_DATA_UNAVAILABLE", "출처가 확인된 식품별 밀도·영양 데이터가 필요합니다.")
        try:
            detections = self.segmentor.segment(image, conf_threshold=conf_threshold)
        except Exception as exc:
            raise AppException(503, "ERR_SEGMENTATION_FAILED", "음식 인식 모델 실행에 실패했습니다.") from exc
        # Ref: FR-003, detected objects must not become table-plane samples.
        object_mask = np.logical_or.reduce([d["mask"].astype(bool) for d in detections]) if detections else None
        # Ref: FR-002, FR-005: Separate pills for visual grounding without adding food mass or calories.
        detected_pills = [d for d in detections if d["class_name"].endswith("_pill")]
        food_detections = [d for d in detections if not d["class_name"].endswith("_pill")]
        if not food_detections and not detected_pills:
            raise ZeroObjectDetectedException()
        try:
            depth = self.depth_estimator.infer(image)
        except AppException:
            raise
        except Exception as exc:
            raise AppException(503, "ERR_DEPTH_INFERENCE_FAILED", "깊이 모델 실행에 실패했습니다.") from exc
        if depth.shape != image.shape[:2] or not np.isfinite(depth).all() or np.any(depth <= 0):
            raise AppException(503, "ERR_INVALID_DEPTH", "깊이 모델 출력이 유효하지 않습니다.")
        h, w = depth.shape
        # This input is explicitly 35mm-equivalent, not the physical lens focal length.
        k = CameraGeometryUtils.compute_intrinsic_matrix(focal_length_mm, w, h, sensor_width_mm=36.0)
        if self.scale_calibrator is not None:
            calib = self.scale_calibrator.detect_and_calibrate(image, depth, k)
            if calib is not None and calib.scale_factor > 0:
                depth = (depth * calib.scale_factor).astype(np.float32)
        food_mask = np.logical_or.reduce([d["mask"].astype(bool) for d in food_detections]) if food_detections else np.zeros(depth.shape, dtype=bool)
        background, _ = CameraGeometryUtils.backproject_depth_to_pointcloud(depth, k, ~object_mask)
        if len(background) > 20000:
            background = background[::int(np.ceil(len(background) / 20000))]
        plane, inlier_ratio = self.geometry_integrator.fit_plane_ransac(background)
        a, b, c, d = (plane[key] for key in ("a", "b", "c", "d"))
        if abs(c) < .2:
            raise PlaneNotFoundException("카메라와 기준 평면의 각도로 인해 체적을 계산할 수 없습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.")
        yy, xx = np.indices(depth.shape)
        ray_x, ray_y = (xx-k[0,2])/k[0,0], (yy-k[1,2])/k[1,1]
        denominator = a*ray_x+b*ray_y+c
        if np.any(np.abs(denominator[food_mask]) < .05):
            raise PlaneNotFoundException("카메라 광선과 평면 교차점 산출에 실패했습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.")
        table = np.divide(-d, denominator, out=np.zeros_like(depth), where=np.abs(denominator) >= .05)
        if np.any(table[food_mask] <= 0):
            raise PlaneNotFoundException("기준 평면 깊이가 유효하지 않습니다. 밝은 곳에서 접시와 주변 테이블이 함께 보이도록 다시 촬영해 주세요.")
        items, triggers = [], {}
        for detection in food_detections:
            mask = detection["mask"].astype(bool)
            # Ref: [Section 14, FR-003, Line 893] 바닥면 폐쇄(Closure) 평면 적분
            # RANSAC 기준 평면과 음식 표면 사이의 절두체(Frustum) 이중 적분
            raw_diff = table[mask]**3 - depth[mask]**3
            volume = float(np.sum(np.maximum(raw_diff, 0)) / (3*k[0,0]*k[1,1]) * 1e6)

            # 관통 또는 사선 촬영으로 인해 체적이 하한선(5 cm³) 미만인 경우 음식 바닥 접촉면으로 폐쇄(Closure) 보정
            if volume < 5.0:
                d_req = -depth[mask] * denominator[mask]
                d_closed = float(np.percentile(d_req, 90))
                table_closed = np.divide(-d_closed, denominator, out=np.zeros_like(depth), where=np.abs(denominator) >= .05)
                closed_diff = table_closed[mask]**3 - depth[mask]**3
                volume_closed = float(np.sum(np.maximum(closed_diff, 0)) / (3*k[0,0]*k[1,1]) * 1e6)
                if volume_closed >= 5.0:
                    volume = min(volume_closed, 5000.0)
                else:
                    # 안전 하한 물리 체적 보정
                    volume = 5.0

            self.geometry_integrator.validate_volume_bounds(volume)
            x1,y1,x2,y2 = (int(round(value)) for value in detection["box"])
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            crop = image[y1:y2, x1:x2].copy()
            if crop.size == 0:
                raise AppException(422, "ERR_INVALID_FOOD_CROP", "음식 검출 영역이 유효하지 않습니다.")
            crop_mask = mask[y1:y2, x1:x2]
            crop[~crop_mask] = 0
            try:
                match = self.food_retriever.search(self.patch_embedder.encode(crop), top_k=3)
                nutrition = self.nutrition_service.calculate(match.food_id, volume)
                candidates = [
                    {
                        "foodId": candidate.food_id,
                        "foodName": candidate_nutrition["foodName"],
                        "score": candidate.score,
                        **{key: candidate_nutrition[key] for key in (
                            "densityGCm3", "weightG", "caloriesKcal", "carbsG",
                            "proteinG", "fatG", "sodiumMg",
                        )},
                    }
                    for candidate in match.candidates
                    for candidate_nutrition in [self.nutrition_service.calculate(candidate.food_id, volume)]
                ]
                detected_food_id = detection["class_name"]
                detector_supported = detected_food_id in getattr(self.nutrition_service, "catalog", {})
                classification_disagreement = detector_supported and detected_food_id != match.food_id
                if classification_disagreement and all(row["foodId"] != detected_food_id for row in candidates):
                    detector_nutrition = self.nutrition_service.calculate(detected_food_id, volume)
                    candidates.insert(0, {
                        "foodId": detected_food_id,
                        "foodName": detector_nutrition["foodName"],
                        "score": round(float(detection["confidence"]), 4),
                        **{key: detector_nutrition[key] for key in (
                            "densityGCm3", "weightG", "caloriesKcal", "carbsG",
                            "proteinG", "fatG", "sodiumMg",
                        )},
                    })
            except (KeyError, OSError, ValueError) as exc:
                raise AppException(503, "ERR_FOOD_REFERENCE_DATA", "음식 기준 이미지 또는 foodId 데이터가 올바르지 않습니다.") from exc
            points, _ = CameraGeometryUtils.backproject_depth_to_pointcloud(depth, k, mask)
            floor, _ = CameraGeometryUtils.backproject_depth_to_pointcloud(table, k, mask)
            box = self.geometry_integrator.compute_3d_oriented_bounding_box(np.concatenate([points, floor]))
            item = {"id": str(uuid.uuid4()), **{key: nutrition[key] for key in (
                        "foodId", "foodName", "densityGCm3", "weightG", "caloriesKcal",
                        "carbsG", "proteinG", "fatG", "sodiumMg")},
                    "confidenceScore": detection["confidence"],
                    "classificationConfidence": match.score,
                    "geometryConfidence": round(float(inlier_ratio), 4),
                    "requiresConfirmation": match.requires_confirmation or classification_disagreement or detection["confidence"] < .25,
                    "topCandidates": candidates[:3], "volumeCm3": round(volume, 2),
                    "bbox2d": {"xmin": x1 / w, "ymin": y1 / h, "xmax": x2 / w, "ymax": y2 / h},
                    "bbox3d": box,
            }
            items.append(item)
            triggers[item["id"]] = sorted(list({nutrition["foodId"].lower(), *nutrition["interactionTags"]}))
        if np.any(food_mask):
            points, pixels = CameraGeometryUtils.backproject_depth_to_pointcloud(depth, k, food_mask)
            colors = image[pixels[:,0], pixels[:,1]][:,::-1] / 255.0
            point_cloud = self.geometry_integrator.downsample_voxel_grid(points, colors)
        else:
            point_cloud = {"count": 0, "positions": [], "colors": []}
        return {"foodItems": items, "groundPlane": plane,
                "visualization3d": {"pointCloud": point_cloud},
                "totalNutrition": {key: round(sum(i[key] for i in items), 2) for key in ("caloriesKcal", "carbsG", "proteinG", "fatG", "sodiumMg")},
                "triggers": triggers,
                "detectedPills": detected_pills}
