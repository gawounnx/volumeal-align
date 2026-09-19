"""ONNX image embedder for labeled food-reference retrieval [FR-004]."""
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort


class PatchEmbedder:
    def __init__(self, model_path: str, use_cuda: bool = False):
        if not Path(model_path).is_file():
            raise FileNotFoundError(model_path)
        # Ref: FR-004, keep CPU fallback for quantized operators without CUDA kernels.
        if use_cuda and hasattr(ort, "preload_dlls"):
            ort.preload_dlls(directory="")
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_cuda else ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(model_path, providers=providers)
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        shape = model_input.shape
        self.height = int(shape[-2]) if isinstance(shape[-2], int) else 224
        self.width = int(shape[-1]) if isinstance(shape[-1], int) else 224

    def encode(self, image_bgr: np.ndarray) -> np.ndarray:
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3 or image_bgr.size == 0:
            raise ValueError("음식 크롭은 비어 있지 않은 BGR 이미지여야 합니다.")
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.width, self.height), interpolation=cv2.INTER_AREA)
        tensor = resized.astype(np.float32) / 255.0
        tensor = (tensor - np.array([0.485, 0.456, 0.406], np.float32)) / np.array(
            [0.229, 0.224, 0.225], np.float32
        )
        tensor = np.transpose(tensor, (2, 0, 1))[None]
        output = np.asarray(self.session.run(None, {self.input_name: tensor})[0])
        if output.ndim == 3:
            vector = output[0, 0]
        elif output.ndim == 2:
            vector = output[0]
        elif output.ndim == 4:
            vector = output[0].reshape(output.shape[1], -1).mean(axis=1)
        else:
            raise ValueError("지원하지 않는 임베딩 모델 출력 차원입니다.")
        vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(vector).all() or norm <= 0:
            raise ValueError("임베딩 모델 출력이 유효하지 않습니다.")
        return vector / norm
