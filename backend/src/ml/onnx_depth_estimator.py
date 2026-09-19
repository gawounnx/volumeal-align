import os
import cv2
import numpy as np
import onnxruntime as ort


class DepthAnythingV2Estimator:
    """Depth Anything v2 Metric ONNX CPU 추론기 [FR-001]"""

    def __init__(self, model_path: str, use_cuda: bool = False, scale_factor: float = 1.0):
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.input_size = 518
        self.scale_factor = scale_factor

        if os.path.exists(model_path):
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.inter_op_num_threads = 1
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            # Ref: FR-001, load CUDA libraries only for the GPU execution path.
            if use_cuda and hasattr(ort, "preload_dlls"):
                ort.preload_dlls(directory="")
            self.session = ort.InferenceSession(
                model_path,
                sess_options=opts,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"] if use_cuda else ["CPUExecutionProvider"],
            )
            self.input_name = self.session.get_inputs()[0].name

    def infer(self, image_bgr: np.ndarray, scale_factor: float = None) -> np.ndarray:
        orig_h, orig_w = image_bgr.shape[:2]

        if self.session is not None:
            resized = cv2.resize(image_bgr, (self.input_size, self.input_size), interpolation=cv2.INTER_CUBIC)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            normalized = (rgb - mean) / std

            input_tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
            outputs = self.session.run(None, {self.input_name: input_tensor})
            depth_pred = outputs[0].squeeze()
            depth_restored = cv2.resize(depth_pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            s = self.scale_factor if scale_factor is None else scale_factor
            return (depth_restored * s).astype(np.float32)

        from src.core.exceptions import AppException
        raise AppException(503, "ERR_DEPTH_MODEL_UNAVAILABLE", "실측 깊이 모델이 준비되지 않았습니다.")
