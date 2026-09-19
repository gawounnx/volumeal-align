import tarfile
import sys
from pathlib import Path

for name in ["Validation.tar", "Training.tar"]:
    tar_path = Path("/workspace") / name
    if not tar_path.exists():
        tar_path = Path(name)
    if not tar_path.exists():
        print(f"File not found: {name}", flush=True)
        continue

    print(f"\n==================== {name} ====================", flush=True)
    size_mb = tar_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.2f} MB", flush=True)

    try:
        with tarfile.open(str(tar_path), "r:*") as tar:
            count = 0
            samples = []
            exts = {}
            for member in tar:
                count += 1
                if count <= 25:
                    samples.append(member.name)
                ext = Path(member.name).suffix.lower()
                exts[ext] = exts.get(ext, 0) + 1
            
            print(f"Total entries: {count}", flush=True)
            print("Sample paths:", flush=True)
            for s in samples:
                print(f"  - {s}", flush=True)
            print("Extensions:", exts, flush=True)
    except Exception as e:
        print(f"Error reading {name}: {e}", flush=True)
