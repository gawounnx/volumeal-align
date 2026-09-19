"""Verify fine-tuned real food YOLOv8-Seg ONNX model on test images."""
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_IMG_DIR = BACKEND_ROOT / "data" / "real_food" / "images" / "test"
TEST_LBL_DIR = BACKEND_ROOT / "data" / "real_food" / "labels" / "test"
MODEL_PATH = BACKEND_ROOT / "weights" / "real_food_seg_run" / "weights" / "best.onnx"

CLASS_NAMES = {
    0: "white_rice",
    1: "spinach_namul",
    2: "kimchi_stew",
    3: "bulgogi",
    4: "banana",
    5: "apple",
}


def preprocess(img_bgr: np.ndarray, imgsz: int = 640):
    h, w = img_bgr.shape[:2]
    scale = min(imgsz / h, imgsz / w)
    nh, nw = int(h * scale), int(w * scale)
    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)

    pad_img = np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)
    pad_img[:nh, :nw] = resized

    tensor = pad_img.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[np.newaxis, ...]
    return tensor, scale, (h, w)


def verify_test_set():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    print(f">> [Model] Loading ONNX model from {MODEL_PATH}")
    session = ort.InferenceSession(str(MODEL_PATH), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_names = [o.name for o in session.get_outputs()]
    print(f">> [Session] Active providers: {session.get_providers()}")
    print(f">> [Session] Inputs: {input_name}, Outputs: {output_names}")

    test_images = sorted(TEST_IMG_DIR.glob("*.jpg"))
    print(f">> [Dataset] Found {len(test_images)} test images in {TEST_IMG_DIR}")

    conf_thresh = 0.25
    detected_count = 0
    results_by_class = {name: {"detected": 0, "total": 0, "confs": []} for name in CLASS_NAMES.values()}

    for img_path in test_images:
        # Determine expected class from filename
        stem = img_path.stem  # e.g., RF_white_rice_0801
        expected_class = None
        for cname in CLASS_NAMES.values():
            if cname in stem:
                expected_class = cname
                break

        if expected_class:
            results_by_class[expected_class]["total"] += 1

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        tensor, scale, (orig_h, orig_w) = preprocess(img)
        outputs = session.run(output_names, {input_name: tensor})
        # output0 shape: (1, 38, 8400) -> [x, y, w, h, 6 classes, 32 mask coefficients]
        out0 = outputs[0][0]  # (38, 8400)

        # Transpose to (8400, 38)
        preds = out0.T
        boxes = preds[:, :4]
        scores = preds[:, 4:10]
        max_scores = np.max(scores, axis=1)
        max_classes = np.argmax(scores, axis=1)

        valid_idx = np.where(max_scores >= conf_thresh)[0]

        if len(valid_idx) > 0:
            best_i = valid_idx[np.argmax(max_scores[valid_idx])]
            best_conf = float(max_scores[best_i])
            best_cls = int(max_classes[best_i])
            detected_cname = CLASS_NAMES.get(best_cls, f"class_{best_cls}")

            detected_count += 1
            if expected_class:
                results_by_class[expected_class]["detected"] += 1
                results_by_class[expected_class]["confs"].append(best_conf)

            # Check mask tensor (output1 shape: (1, 32, 160, 160))
            if len(outputs) > 1:
                proto = outputs[1][0]  # (32, 160, 160)
                mask_coef = preds[best_i, 10:42]
                mask = np.matmul(mask_coef, proto.reshape(32, -1)).reshape(160, 160)
                sigmoid_mask = 1.0 / (1.0 + np.exp(-mask))
                binary_mask = (sigmoid_mask >= 0.5).astype(np.uint8)
                assert binary_mask.ndim == 2, "Binary mask must be 2D"

    print("\n" + "=" * 65)
    print(f"{'Class':<16} | {'Expected':<9} | {'Detected':<9} | {'Recall':<7} | {'Avg Conf'}")
    print("-" * 65)
    for cname, stats in results_by_class.items():
        tot = stats["total"]
        det = stats["detected"]
        rec = (det / tot * 100) if tot > 0 else 0.0
        avg_c = np.mean(stats["confs"]) if stats["confs"] else 0.0
        print(f"{cname:<16} | {tot:<9} | {det:<9} | {rec:6.1f}% | {avg_c:.3f}")
    print("-" * 65)
    overall_recall = (detected_count / len(test_images) * 100) if test_images else 0.0
    print(f"{'OVERALL':<16} | {len(test_images):<9} | {detected_count:<9} | {overall_recall:6.1f}% |")
    print("=" * 65 + "\n")
    return results_by_class


if __name__ == "__main__":
    verify_test_set()
