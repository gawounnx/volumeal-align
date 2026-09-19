"""Deploy and standardize Apple & Banana datasets from Roboflow YOLOv8 segmentation zip.

Specification Mapping:
- Class ID 4: banana
- Class ID 5: apple
- Output paths:
  backend/data/real_food/images/{train,val,test}/B_{class}_{번호:03d}.jpg
  backend/data/real_food/labels/{train,val,test}/B_{class}_{번호:03d}.txt
"""

import os
import shutil
import zipfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = BACKEND_ROOT.parent / "aihub_data" / "Fruit segmentation.v2i.yolov8.zip"
REAL_FOOD_DIR = BACKEND_ROOT / "data" / "real_food"


def deploy_fruits():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Zip archive not found at: {ZIP_PATH}")

    print(f"Reading from {ZIP_PATH}...")

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        all_files = set(z.namelist())

        # Collect paired image and label files
        apple_pairs = []
        banana_pairs = []

        for f in sorted(all_files):
            if "/images/" in f and f.endswith(".jpg"):
                label_f = f.replace("/images/", "/labels/").replace(".jpg", ".txt")
                if label_f in all_files:
                    filename = f.split("/")[-1].lower()
                    if filename.startswith("apple") and "pineapple" not in filename:
                        apple_pairs.append((f, label_f))
                    elif filename.startswith("banana"):
                        banana_pairs.append((f, label_f))

        print(f"Found {len(apple_pairs)} valid apple pairs and {len(banana_pairs)} valid banana pairs.")

        # Class configuration: (name, new_class_id, pairs, train_cnt, val_cnt, test_cnt)
        # Apple: 40 train, 10 val, 10 test (total 60)
        # Banana: 17 train, 5 val, 5 test (total 27 available)
        fruit_configs = [
            ("apple", 5, apple_pairs, 40, 10, 10),
            ("banana", 4, banana_pairs, min(17, len(banana_pairs)), 5, min(5, max(0, len(banana_pairs) - 22))),
        ]

        summary = {}

        for cls_name, cls_id, pairs, n_train, n_val, n_test in fruit_configs:
            summary[cls_name] = {"train": 0, "val": 0, "test": 0, "total": 0}

            # Define splits
            train_items = pairs[:n_train]
            val_items = pairs[n_train : n_train + n_val]
            test_items = pairs[n_train + n_val : n_train + n_val + n_test]

            splits = [
                ("train", train_items, 1),
                ("val", val_items, 41),
                ("test", test_items, 51),
            ]

            for split_name, items, start_idx in splits:
                img_dest_dir = REAL_FOOD_DIR / "images" / split_name
                lbl_dest_dir = REAL_FOOD_DIR / "labels" / split_name
                img_dest_dir.mkdir(parents=True, exist_ok=True)
                lbl_dest_dir.mkdir(parents=True, exist_ok=True)

                for offset, (img_src, lbl_src) in enumerate(items):
                    idx = start_idx + offset
                    target_base = f"B_{cls_name}_{idx:03d}"
                    target_img = img_dest_dir / f"{target_base}.jpg"
                    target_lbl = lbl_dest_dir / f"{target_base}.txt"

                    # 1. Write image
                    img_data = z.read(img_src)
                    target_img.write_bytes(img_data)

                    # 2. Process and write label with converted class ID
                    raw_lines = z.read(lbl_src).decode("utf-8").strip().splitlines()
                    converted_lines = []
                    for line in raw_lines:
                        tokens = line.strip().split()
                        if tokens:
                            tokens[0] = str(cls_id)
                            converted_lines.append(" ".join(tokens))

                    target_lbl.write_text("\n".join(converted_lines) + "\n", encoding="utf-8")
                    summary[cls_name][split_name] += 1
                    summary[cls_name]["total"] += 1

    return summary


def main():
    summary = deploy_fruits()
    print("\n================ Deployment Summary ================")
    print(f"{'Class':<10} | {'Train':<7} | {'Val':<7} | {'Test':<7} | {'Total':<7}")
    print("-" * 50)
    for cls_name, counts in summary.items():
        print(
            f"{cls_name:<10} | {counts['train']:<7} | {counts['val']:<7} | {counts['test']:<7} | {counts['total']:<7}"
        )
    print("====================================================\n")


if __name__ == "__main__":
    main()
