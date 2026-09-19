"""YOLOv8-seg ONNX 런타임 추론 엔진."""
import ast
import json
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np
import onnxruntime as ort

class ONNXSegmentor:
    def __init__(self, model_path: str = "/workspace/backend/weights/best.onnx", conf_threshold: float = 0.05, iou_threshold: float = 0.45, use_cuda: bool = False):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        # Ref: FR-002, discover pip-installed CUDA/cuDNN before session creation.
        if use_cuda and hasattr(ort, "preload_dlls"):
            ort.preload_dlls(directory="")
        requested = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_cuda else ["CPUExecutionProvider"]
        providers = [p for p in requested if p in ort.get_available_providers()]
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.classes = self._parse_class_names(
            self.session.get_modelmeta().custom_metadata_map.get("names")
        )

    @staticmethod
    def _parse_class_names(raw_names: str) -> List[str]:
        """Read class IDs from the exported model, never from a separate label list."""
        if not raw_names:
            raise ValueError("ONNX 모델에 클래스 names 메타데이터가 없습니다.")
        try:
            try:
                names = json.loads(raw_names)
            except json.JSONDecodeError:
                names = ast.literal_eval(raw_names)
        except (ValueError, SyntaxError) as exc:
            raise ValueError("ONNX 클래스 names 메타데이터를 해석할 수 없습니다.") from exc

        if isinstance(names, dict):
            indexed = {}
            for key, value in names.items():
                if type(key) is int:
                    index = key
                elif isinstance(key, str) and key.isdecimal():
                    index = int(key)
                else:
                    raise ValueError("ONNX 클래스 ID는 0부터 연속된 정수여야 합니다.")
                if index in indexed:
                    raise ValueError("ONNX 클래스 ID가 중복되었습니다.")
                indexed[index] = value
            if set(indexed) != set(range(len(indexed))):
                raise ValueError("ONNX 클래스 ID는 0부터 연속된 정수여야 합니다.")
            names = [indexed[index] for index in range(len(indexed))]
        if not isinstance(names, list) or not names or any(
            not isinstance(name, str) or not name.strip() for name in names
        ):
            raise ValueError("ONNX 클래스 이름은 비어 있지 않은 문자열 목록이어야 합니다.")
        return names

    def preprocess(self, img_bgr: np.ndarray):
        h, w = img_bgr.shape[:2]
        scale = min(640 / h, 640 / w)
        nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
        resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        pad_w, pad_h = (640 - nw) // 2, (640 - nh) // 2
        padded = np.full((640, 640, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + nh, pad_w:pad_w + nw] = resized
        blob = np.transpose(cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
        return blob, scale, (pad_w, pad_h)

    def postprocess(self, preds, orig_shape, scale, pad, conf_threshold=None):
        thresh = conf_threshold if conf_threshold is not None else self.conf_threshold
        output0, proto = preds[0], preds[1]
        if output0.ndim != 3 or output0.shape[0] != 1 or proto.ndim != 4 or proto.shape[0] != 1:
            raise ValueError("지원하지 않는 ONNX 세그멘테이션 출력 차원입니다.")
        class_end = 4 + len(self.classes)
        expected_channels = class_end + proto.shape[1]
        if output0.shape[1] != expected_channels:
            raise ValueError("ONNX 출력 채널 수와 클래스 메타데이터가 일치하지 않습니다.")
        predictions = output0[0].T
        boxes = predictions[:, :4]
        scores = predictions[:, 4:class_end]
        mask_coeffs = predictions[:, class_end:]

        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        valid = confidences >= thresh
        if not np.any(valid):
            return []

        boxes, confidences, class_ids, mask_coeffs = boxes[valid], confidences[valid], class_ids[valid], mask_coeffs[valid]
        pad_w, pad_h = pad
        orig_h, orig_w = orig_shape

        boxes_xyxy = np.zeros_like(boxes)
        boxes_xyxy[:, 0] = np.clip((boxes[:, 0] - boxes[:, 2] / 2 - pad_w) / scale, 0, orig_w)
        boxes_xyxy[:, 1] = np.clip((boxes[:, 1] - boxes[:, 3] / 2 - pad_h) / scale, 0, orig_h)
        boxes_xyxy[:, 2] = np.clip((boxes[:, 0] + boxes[:, 2] / 2 - pad_w) / scale, 0, orig_w)
        boxes_xyxy[:, 3] = np.clip((boxes[:, 1] + boxes[:, 3] / 2 - pad_h) / scale, 0, orig_h)

        cv_boxes = [[int(b[0]), int(b[1]), int(b[2] - b[0]), int(b[3] - b[1])] for b in boxes_xyxy]
        indices = []
        for class_id in np.unique(class_ids):
            candidates = np.flatnonzero(class_ids == class_id)
            kept = cv2.dnn.NMSBoxes([cv_boxes[i] for i in candidates], confidences[candidates].tolist(), thresh, self.iou_threshold)
            indices.extend(candidates[np.asarray(kept, dtype=int).flatten()].tolist())
        if len(indices) == 0:
            return []

        proto = proto[0]
        results = []
        for idx in np.array(indices).flatten():
            box = boxes_xyxy[idx]
            coeff = mask_coeffs[idx]
            mask_160 = 1 / (1 + np.exp(-np.sum(coeff[:, None, None] * proto, axis=0)))
            # Prototypes include the 640x640 letterbox padding. Restore that
            # canvas first, then undo the exact integer crop used by preprocess.
            # The bottom/right padding can be one pixel larger than top/left.
            resized_h, resized_w = max(1, int(orig_h * scale)), max(1, int(orig_w * scale))
            mask_padded = cv2.resize(mask_160, (640, 640), interpolation=cv2.INTER_LINEAR)
            mask_unpadded = mask_padded[
                pad_h:pad_h + resized_h, pad_w:pad_w + resized_w
            ]
            mask_full = (
                cv2.resize(mask_unpadded, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR) > 0.5
            ).astype(np.uint8)
            
            # 박스 내부 크롭
            x1, y1, x2, y2 = box.astype(int)
            cropped_mask = np.zeros_like(mask_full)
            cropped_mask[max(0, y1):min(orig_h, y2), max(0, x1):min(orig_w, x2)] = mask_full[max(0, y1):min(orig_h, y2), max(0, x1):min(orig_w, x2)]
            
            px_count = int(np.sum(cropped_mask))
            if px_count < 10:
                continue

            results.append({
                "class_id": int(class_ids[idx]),
                "class_name": self.classes[int(class_ids[idx])],
                "confidence": round(float(confidences[idx]), 4),
                "box": [round(float(c), 1) for c in box],
                "mask": cropped_mask,
                "mask_pixel_count": px_count,
            })
        return results

    def segment(self, img_bgr, conf_threshold=None, **kwargs):
        blob, scale, pad = self.preprocess(img_bgr)
        preds = self.session.run(None, {self.input_name: blob})
        return self.postprocess(preds, img_bgr.shape[:2], scale, pad, conf_threshold)

YoloV8Segmentor = ONNXSegmentor
