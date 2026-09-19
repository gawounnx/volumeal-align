from pathlib import Path
import pytest
import yaml
from src.ml.real_food_dataset import DatasetValidationError, validate_dataset

NAMES = {0: "white_rice", 1: "banana"}


def _dataset(tmp_path: Path, label="1 0.1 0.1 0.9 0.1 0.5 0.9\n") -> Path:
    root = tmp_path / "real_food"
    for split in ("train", "val", "test"):
        images, labels = root/"images"/split, root/"labels"/split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        (images/"banana_001.jpg").write_bytes(b"test")
        (labels/"banana_001.txt").write_text(label, encoding="utf-8")
    manifest = tmp_path/"real_food.yaml"
    manifest.write_text(yaml.safe_dump({
        "path": str(root), "train": "images/train", "val": "images/val",
        "test": "images/test", "names": NAMES,
    }, sort_keys=False), encoding="utf-8")
    return manifest


def test_accepts_paired_segmentation_data(tmp_path):
    report = validate_dataset(_dataset(tmp_path))
    assert report["classes"] == NAMES
    assert report["splits"]["train"] == {"images": 1, "instancesByClass": {"banana": 1}}


def test_rejects_missing_label(tmp_path):
    manifest = _dataset(tmp_path)
    (tmp_path/"real_food/labels/val/banana_001.txt").unlink()
    with pytest.raises(DatasetValidationError, match="mismatch"):
        validate_dataset(manifest)


def test_rejects_out_of_range_polygon(tmp_path):
    manifest = _dataset(tmp_path, "1 0.1 0.1 1.1 0.1 0.5 0.9\n")
    with pytest.raises(DatasetValidationError, match="0..1"):
        validate_dataset(manifest)


def test_rejects_non_contiguous_ids(tmp_path):
    manifest = _dataset(tmp_path)
    data = yaml.safe_load(manifest.read_text())
    data["names"] = {0: "white_rice", 2: "banana"}
    manifest.write_text(yaml.safe_dump(data))
    with pytest.raises(DatasetValidationError, match="contiguous"):
        validate_dataset(manifest)
