"""Validate the real-photo YOLO segmentation dataset contract."""
from __future__ import annotations
import math
from collections import Counter
from pathlib import Path
from typing import Any
import yaml

SPLITS = ("train", "val", "test")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


class DatasetValidationError(ValueError):
    pass


def _names(raw: Any) -> dict[int, str]:
    if isinstance(raw, list):
        names = dict(enumerate(map(str, raw)))
    elif isinstance(raw, dict):
        try:
            names = {int(key): str(value) for key, value in raw.items()}
        except (TypeError, ValueError) as exc:
            raise DatasetValidationError("Class IDs must be integers.") from exc
    else:
        raise DatasetValidationError("names must be a list or mapping.")
    expected = list(range(len(names)))
    if sorted(names) != expected:
        raise DatasetValidationError(
            f"Class IDs must be contiguous from zero: expected={expected}, actual={sorted(names)}"
        )
    if len(set(names.values())) != len(names):
        raise DatasetValidationError("Class names must be unique.")
    return names


def _label_counts(path: Path, names: dict[int, str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    rows = path.read_text(encoding="utf-8").splitlines()
    if not rows:
        raise DatasetValidationError(f"Empty label file: {path}")
    for number, row in enumerate(rows, 1):
        fields = row.split()
        if len(fields) < 7 or len(fields[1:]) % 2:
            raise DatasetValidationError(f"Invalid YOLO polygon: {path}:{number}")
        try:
            class_id = int(fields[0])
            coords = [float(value) for value in fields[1:]]
        except ValueError as exc:
            raise DatasetValidationError(f"Non-numeric label value: {path}:{number}") from exc
        if class_id not in names:
            raise DatasetValidationError(f"Unknown class ID {class_id}: {path}:{number}")
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in coords):
            raise DatasetValidationError(f"Polygon coordinates must be finite and within 0..1: {path}:{number}")
        counts[names[class_id]] += 1
    return counts


def validate_dataset(data_yaml: str | Path) -> dict[str, Any]:
    manifest_path = Path(data_yaml).expanduser().resolve()
    if not manifest_path.is_file():
        raise DatasetValidationError(f"Dataset manifest not found: {manifest_path}")
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DatasetValidationError(f"Invalid YAML: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise DatasetValidationError("Dataset manifest must be an object.")
    names = _names(manifest.get("names"))
    root = Path(str(manifest.get("path") or manifest_path.parent)).expanduser()
    root = (root if root.is_absolute() else manifest_path.parent / root).resolve()
    report = {}
    for split in SPLITS:
        configured = manifest.get(split)
        if not configured:
            raise DatasetValidationError(f"Missing split path: {split}")
        image_dir = Path(str(configured))
        image_dir = (image_dir if image_dir.is_absolute() else root / image_dir).resolve()
        label_dir = root / "labels" / split
        if not image_dir.is_dir() or not label_dir.is_dir():
            raise DatasetValidationError(f"Missing {split} image or label directory.")
        images = sorted(p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
        if not images:
            raise DatasetValidationError(f"No images in {split}: {image_dir}")
        image_stems = {p.stem for p in images}
        label_stems = {p.stem for p in label_dir.glob("*.txt")}
        if image_stems != label_stems:
            raise DatasetValidationError(
                f"{split} image-label mismatch: missing_labels={sorted(image_stems-label_stems)}, "
                f"orphan_labels={sorted(label_stems-image_stems)}"
            )
        counts: Counter[str] = Counter()
        for image in images:
            counts.update(_label_counts(label_dir / f"{image.stem}.txt", names))
        report[split] = {"images": len(images), "instancesByClass": dict(sorted(counts.items()))}
    return {"classes": names, "root": str(root), "splits": report}
