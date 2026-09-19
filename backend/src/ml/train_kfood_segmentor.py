"""RTX 5090 real-photo YOLOv8-Seg fine-tuning pipeline."""
import argparse
from pathlib import Path

import torch

from src.ml.real_food_dataset import DatasetValidationError, validate_dataset


def execute_training(
    data_yaml: str = "/workspace/backend/data/real_food.yaml",
    model_size: str = "yolov8x-seg.pt",
    epochs: int = 40,
    batch_size: int = 16,
    imgsz: int = 640,
    project: str = "/workspace/backend/weights",
    run_name: str = "real_food_seg_run",
    freeze: int = 10,
):
    report = validate_dataset(data_yaml)
    print(f">> [Dataset] validated: {report['splits']}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA device is unavailable; training stopped.")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("The ultralytics package is required.") from exc

    # Resolve local weight file if available
    local_candidate = Path("/workspace/backend") / Path(model_size).name
    if Path(model_size).is_file():
        resolved_model = str(Path(model_size).resolve())
    elif local_candidate.is_file():
        resolved_model = str(local_candidate.resolve())
    else:
        resolved_model = model_size

    print(f">> [Hardware] GPU: {torch.cuda.get_device_name(0)}")
    print(f">> [Model] Base weight: {resolved_model} (freeze={freeze})")
    model = YOLO(resolved_model)
    results = model.train(
        data=str(Path(data_yaml).resolve()),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=0,
        workers=4,
        amp=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        project=project,
        name=run_name,
        exist_ok=True,
        freeze=freeze,
    )
    best_weight = Path(project) / run_name / "weights" / "best.pt"
    if not best_weight.is_file():
        raise RuntimeError(f"Training did not produce best.pt: {best_weight}")
    print(f">> [Training Completed] Best weight: {best_weight}")
    onnx_path = YOLO(str(best_weight)).export(
        format="onnx", opset=17, dynamic=False, simplify=True
    )
    print(f">> [SUCCESS] ONNX exported: {onnx_path}")
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train real-photo food segmentation")
    parser.add_argument("--data-yaml", default="/workspace/backend/data/real_food.yaml")
    parser.add_argument("--model-size", default="/workspace/backend/yolov8x-seg.pt")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--project", default="/workspace/backend/weights")
    parser.add_argument("--run-name", default="real_food_seg_run")
    parser.add_argument("--freeze", type=int, default=10)
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.validate_only:
            print(validate_dataset(args.data_yaml))
        else:
            execute_training(
                args.data_yaml, args.model_size, args.epochs, args.batch_size,
                args.imgsz, args.project, args.run_name
            )
    except (DatasetValidationError, RuntimeError) as exc:
        print(f"[-] [Error] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
