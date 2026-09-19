"""Deploy and synthesize a balanced 400+ real photo segmentation dataset for 6 target food classes.

Target Food Classes:
- 0: white_rice (쌀밥 + 콩밥 from AI-Hub)
- 1: spinach_namul (시금치나물 from AI-Hub)
- 2: kimchi_stew (부대찌개 + 두부김치 from AI-Hub)
- 3: bulgogi (돼지갈비 + 제육덮밥 from AI-Hub)
- 4: banana (Roboflow real photos + horizontal flip augmentation)
- 5: apple (Roboflow real photos)
"""

import io
import os
import shutil
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parent.parent
AIHUB_DIR = BACKEND_ROOT.parent / "aihub_data"
FRUIT_ZIP_PATH = AIHUB_DIR / "Fruit segmentation.v2i.yolov8.zip"
PORTION_IMG_ZIP_PATH = AIHUB_DIR / "portion_val_images.zip"
PORTION_LBL_TAR_PATH = AIHUB_DIR / "portion_val_labels.tar"
REAL_FOOD_DIR = BACKEND_ROOT / "data" / "real_food"


def decode_cp949(name: str) -> str:
    try:
        return name.encode("cp437").decode("cp949")
    except Exception:
        return name


def bbox_to_polygon(img_bgr: np.ndarray, xmin: int, ymin: int, xmax: int, ymax: int) -> np.ndarray:
    """Extract a fine polygon contour inside the target bounding box ROI."""
    h_img, w_img = img_bgr.shape[:2]
    xmin = max(0, min(xmin, w_img - 1))
    xmax = max(0, min(xmax, w_img))
    ymin = max(0, min(ymin, h_img - 1))
    ymax = max(0, min(ymax, h_img))

    if (xmax - xmin) < 10 or (ymax - ymin) < 10:
        w_b = max(1.0, float(xmax - xmin))
        h_b = max(1.0, float(ymax - ymin))
        dx, dy = w_b * 0.15, h_b * 0.15
        pts = np.array([
            [xmin + dx, ymin], [xmax - dx, ymin],
            [xmax, ymin + dy], [xmax, ymax - dy],
            [xmax - dx, ymax], [xmin + dx, ymax],
            [xmin, ymax - dy], [xmin, ymin + dy],
        ], dtype=float)
        pts[:, 0] /= w_img
        pts[:, 1] /= h_img
        return np.clip(pts, 0.0, 1.0)

    roi = img_bgr[ymin:ymax, xmin:xmax]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_cnt = None
    max_area = 0
    roi_area = (xmax - xmin) * (ymax - ymin)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 0.12 * roi_area:
            if area > max_area:
                max_area = area
                best_cnt = cnt

    if best_cnt is not None and len(best_cnt) >= 4:
        epsilon = 0.015 * cv2.arcLength(best_cnt, True)
        approx = cv2.approxPolyDP(best_cnt, epsilon, True)
        if len(approx) >= 4:
            pts = approx.reshape(-1, 2).astype(float)
            pts[:, 0] += xmin
            pts[:, 1] += ymin
            pts[:, 0] /= w_img
            pts[:, 1] /= h_img
            return np.clip(pts, 0.0, 1.0)

    w_b = float(xmax - xmin)
    h_b = float(ymax - ymin)
    dx = w_b * 0.15
    dy = h_b * 0.15
    pts = np.array([
        [xmin + dx, ymin], [xmax - dx, ymin],
        [xmax, ymin + dy], [xmax, ymax - dy],
        [xmax - dx, ymax], [xmin + dx, ymax],
        [xmin, ymax - dy], [xmin, ymin + dy],
    ], dtype=float)
    pts[:, 0] /= w_img
    pts[:, 1] /= h_img
    return np.clip(pts, 0.0, 1.0)


def extract_aihub_foods():
    """Extract Korean foods from AI-Hub with refined segmentation polygons."""
    print(">> [AI-Hub] Loading portion labels tar...")
    with tarfile.open(str(PORTION_LBL_TAR_PATH), "r") as t:
        m = t.getmember("122.음식_분류를_위한_음식종류_및_양에_따른_칼로리_데이터셋(재료,_양념,_완제품_등)/01.데이터/2.Validation/라벨링데이터/양추정_라벨링_VAL.zip.part0")
        lbl_bytes = t.extractfile(m).read()

    lbl_z = zipfile.ZipFile(io.BytesIO(lbl_bytes))
    img_z = zipfile.ZipFile(str(PORTION_IMG_ZIP_PATH))

    lbl_map = {decode_cp949(n): n for n in lbl_z.namelist()}
    img_map = {decode_cp949(n): n for n in img_z.namelist()}

    food_specs = {
        0: [("쌀밥", "쌀밥", 55), ("콩밥", "콩밥", 25)],
        1: [("시금치나물", "시금치나물", 55)],
        2: [("부대찌개", "부대찌개", 54), ("두부김치", "두부김치", 26)],
        3: [("돼지갈비", "돼지갈비", 56), ("제육덮밥", "제육덮밥", 24)],
    }

    extracted = {0: [], 1: [], 2: [], 3: []}
    cached_q_zips = {}

    for cls_id, sources in food_specs.items():
        for folder, obj_name, max_cnt in sources:
            xml_keys = [k for k in lbl_map if f"xml/{folder}/" in k and k.endswith(".xml")]
            count = 0

            q_zip_names = [k for k in img_map if f"image/{folder}/" in k and k.endswith(".zip")]

            for q_k in q_zip_names:
                if q_k not in cached_q_zips:
                    raw_name = img_map[q_k]
                    q_bytes = img_z.read(raw_name)
                    sub_z = zipfile.ZipFile(io.BytesIO(q_bytes))
                    sub_map = {decode_cp949(n): n for n in sub_z.namelist()}
                    cached_q_zips[q_k] = (sub_z, sub_map)

            for xml_k in xml_keys:
                if count >= max_cnt:
                    break
                raw_xml = lbl_map[xml_k]
                try:
                    xml_content = lbl_z.read(raw_xml).decode("utf-8", errors="ignore")
                    root = ET.fromstring(xml_content)
                    filename = root.find("filename").text

                    target_bbox = None
                    for obj in root.findall("object"):
                        name_tag = obj.find("name")
                        if name_tag is not None and name_tag.text == obj_name:
                            b = obj.find("bndbox")
                            target_bbox = (
                                int(float(b.find("xmin").text)),
                                int(float(b.find("ymin").text)),
                                int(float(b.find("xmax").text)),
                                int(float(b.find("ymax").text)),
                            )
                            break

                    if target_bbox is None:
                        continue

                    img_data = None
                    for q_k in q_zip_names:
                        sub_z, sub_map = cached_q_zips[q_k]
                        matching = [k for k in sub_map if filename.lower() in k.lower()]
                        if matching:
                            img_data = sub_z.read(sub_map[matching[0]])
                            break

                    if img_data is None:
                        continue

                    nparr = np.frombuffer(img_data, np.uint8)
                    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img_bgr is None:
                        continue

                    poly_pts = bbox_to_polygon(img_bgr, *target_bbox)
                    extracted[cls_id].append((img_data, poly_pts))
                    count += 1
                except Exception:
                    continue

            print(f"  [+] Extracted {count} items for {folder} ({obj_name})")

    return extracted


def extract_fruits():
    """Extract and augment fruits from Roboflow dataset."""
    print(">> [Roboflow] Loading Fruit dataset...")
    extracted = {4: [], 5: []}

    with zipfile.ZipFile(str(FRUIT_ZIP_PATH), "r") as z:
        all_files = set(z.namelist())
        apple_pairs = []
        banana_pairs = []

        for f in sorted(all_files):
            if "/images/" in f and f.endswith(".jpg"):
                lbl_f = f.replace("/images/", "/labels/").replace(".jpg", ".txt")
                if lbl_f in all_files:
                    fname = f.split("/")[-1].lower()
                    if fname.startswith("apple") and "pineapple" not in fname:
                        apple_pairs.append((f, lbl_f))
                    elif fname.startswith("banana"):
                        banana_pairs.append((f, lbl_f))

        # 1. Apple: up to 80
        for img_src, lbl_src in apple_pairs[:80]:
            img_data = z.read(img_src)
            lbl_lines = z.read(lbl_src).decode("utf-8").strip().splitlines()
            polygons = []
            for line in lbl_lines:
                tokens = line.strip().split()
                if len(tokens) >= 7 and (len(tokens) - 1) % 2 == 0:
                    coords = [float(v) for v in tokens[1:]]
                    pts = np.array(coords).reshape(-1, 2)
                    polygons.append(pts)
            if polygons:
                extracted[5].append((img_data, polygons))

        # 2. Banana: 27 original + 27 horizontal flip = 54
        for img_src, lbl_src in banana_pairs:
            img_data = z.read(img_src)
            lbl_lines = z.read(lbl_src).decode("utf-8").strip().splitlines()
            orig_polys = []
            for line in lbl_lines:
                tokens = line.strip().split()
                if len(tokens) >= 7 and (len(tokens) - 1) % 2 == 0:
                    coords = [float(v) for v in tokens[1:]]
                    pts = np.array(coords).reshape(-1, 2)
                    orig_polys.append(pts)

            if orig_polys:
                extracted[4].append((img_data, orig_polys))

                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    flipped_img = cv2.flip(img, 1)
                    _, enc = cv2.imencode(".jpg", flipped_img)
                    flipped_bytes = enc.tobytes()

                    flipped_polys = []
                    for poly in orig_polys:
                        f_poly = poly.copy()
                        f_poly[:, 0] = 1.0 - f_poly[:, 0]
                        flipped_polys.append(f_poly)
                    extracted[4].append((flipped_bytes, flipped_polys))

    print(f"  [+] Extracted {len(extracted[5])} apples and {len(extracted[4])} bananas")
    return extracted


def build_and_deploy_dataset():
    for split in ("train", "val", "test"):
        img_dir = REAL_FOOD_DIR / "images" / split
        lbl_dir = REAL_FOOD_DIR / "labels" / split
        if img_dir.exists():
            shutil.rmtree(img_dir)
        if lbl_dir.exists():
            shutil.rmtree(lbl_dir)
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

    korean_foods = extract_aihub_foods()
    fruits = extract_fruits()

    all_data = {
        0: korean_foods[0],
        1: korean_foods[1],
        2: korean_foods[2],
        3: korean_foods[3],
        4: fruits[4],
        5: fruits[5],
    }

    class_names = {
        0: "white_rice",
        1: "spinach_namul",
        2: "kimchi_stew",
        3: "bulgogi",
        4: "banana",
        5: "apple",
    }

    summary = {name: {"train": 0, "val": 0, "test": 0, "total": 0} for name in class_names.values()}

    for cls_id, items in all_data.items():
        cls_name = class_names[cls_id]
        total_n = len(items)

        n_test = max(5, int(total_n * 0.15))
        n_val = max(5, int(total_n * 0.15))
        n_train = total_n - n_val - n_test

        train_items = items[:n_train]
        val_items = items[n_train:n_train + n_val]
        test_items = items[n_train + n_val:]

        splits = [
            ("train", train_items, 1),
            ("val", val_items, 501),
            ("test", test_items, 801),
        ]

        for split_name, split_list, start_idx in splits:
            img_dest = REAL_FOOD_DIR / "images" / split_name
            lbl_dest = REAL_FOOD_DIR / "labels" / split_name

            for idx_offset, item in enumerate(split_list):
                file_idx = start_idx + idx_offset
                base_name = f"RF_{cls_name}_{file_idx:04d}"
                out_img = img_dest / f"{base_name}.jpg"
                out_lbl = lbl_dest / f"{base_name}.txt"

                img_data, poly_data = item
                out_img.write_bytes(img_data)

                lbl_lines = []
                if isinstance(poly_data, list):
                    for poly in poly_data:
                        coords_str = " ".join(f"{x:.6f} {y:.6f}" for x, y in poly)
                        lbl_lines.append(f"{cls_id} {coords_str}")
                else:
                    coords_str = " ".join(f"{x:.6f} {y:.6f}" for x, y in poly_data)
                    lbl_lines.append(f"{cls_id} {coords_str}")

                out_lbl.write_text("\n".join(lbl_lines) + "\n", encoding="utf-8")
                summary[cls_name][split_name] += 1
                summary[cls_name]["total"] += 1

    print("\n" + "=" * 60)
    print(f"{'Class Name':<16} | {'Train':<7} | {'Val':<7} | {'Test':<7} | {'Total':<7}")
    print("-" * 60)
    grand_total = {"train": 0, "val": 0, "test": 0, "total": 0}
    for cname, cnts in summary.items():
        print(f"{cname:<16} | {cnts['train']:<7} | {cnts['val']:<7} | {cnts['test']:<7} | {cnts['total']:<7}")
        for k in grand_total:
            grand_total[k] += cnts[k]
    print("-" * 60)
    print(f"{'GRAND TOTAL':<16} | {grand_total['train']:<7} | {grand_total['val']:<7} | {grand_total['test']:<7} | {grand_total['total']:<7}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    build_and_deploy_dataset()
