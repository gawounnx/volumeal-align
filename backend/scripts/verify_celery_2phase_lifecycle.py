"""[P1-2] Celery 2-Phase Commit 파일 수명주기 실서버 E2E 검증 스크립트.

검증 항목:
1. Celery Worker (Redis 6379) 및 실서버 (포트 8001) 연결성 확인
2. [Phase 1 -> Phase 2] 정상 추론 성공 시 .tmp -> meals/ 원자적 이동 (os.rename) 검증
3. [Rollback: OOM] 강제 OOM 주입 시 503(ERR_CELERY_OOM) 응답 및 .tmp 고아 파일 롤백 삭제 (os.unlink) 검증
4. [Rollback: TIMEOUT] 5.0초 타임아웃 주입 시 504(ERR_CELERY_TIMEOUT) 응답 및 .tmp 롤백 삭제 검증
5. [Rollback: Corrupted] 깨진 이미지 전송 시 422 응답 및 .tmp 롤백 삭제 검증
6. [BR-VAL-003: HEIC 415] HEIC 포맷 파일 업로드 시 즉시 415 차단 및 파일 미저장 검증
"""

import io
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from jose import jwt
from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import settings
from src.services.storage_service import StorageService

BASE_URL = "http://localhost:8001/api/v1"
TEST_USER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000002")


def make_token() -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode(
        {"sub": str(TEST_USER_ID), "type": "access", "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_sample_jpeg() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (224, 224), color=(200, 100, 50))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run_all_tests():
    storage = StorageService()
    token = make_token()
    headers_base = {"Authorization": f"Bearer {token}"}
    cookies = {settings.AUTH_COOKIE_NAME: token}

    print("=" * 70)
    print("Celery 2-Phase Commit 파일 수명주기 실서버 검증 시작")
    print("=" * 70)

    # 0. 사전 상태 점검
    print("[1/6] 실서버 및 Celery Worker 상태 확인...")
    try:
        from app.worker.celery_app import celery_app
        ping_res = celery_app.control.inspect(timeout=1.5).ping()
        print(f"  [+] Celery Worker Ping: {ping_res}")
        assert ping_res, "Celery worker is not responding!"
    except Exception as exc:
        print(f"  [-] Celery Worker Ping Error: {exc}")
        raise

    health_res = requests.get(f"{BASE_URL}/health", timeout=3.0)
    assert health_res.status_code == 200, f"Healthcheck failed: {health_res.status_code}"
    print(f"  [+] Backend Server (8001) Healthcheck OK")

    # 1. Happy Path: 정상 이미지 추론 및 Phase 2 원자적 이동
    print("\n[2/6] [Phase 1 -> Phase 2] Celery Worker 실시간 태스크 수신 및 원자적 이동(os.rename) 검증...")
    test_img_path = BACKEND_ROOT / "data" / "real_food" / "images" / "test" / "RF_apple_0801.jpg"
    if test_img_path.is_file():
        img_bytes = test_img_path.read_bytes()
    else:
        img_bytes = create_sample_jpeg()

    # 업로드 전 .tmp 상태 확인
    tmp_before = set(os.listdir(storage.tmp_dir))

    resp = requests.post(
        f"{BASE_URL}/vision/estimate",
        headers={**headers_base, "X-Test-Force-Fail": "MOCK"},
        cookies=cookies,
        files={"file": ("test_meal.jpg", img_bytes, "image/jpeg")},
        data={"focal_length_mm": 26.0, "conf_threshold": 0.25},
        timeout=15.0,
    )

    assert resp.status_code == 200, f"Estimate failed with status {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    img_url = data.get("imageUrl", "")
    assert img_url.startswith("/static/uploads/meals/"), f"Unexpected imageUrl: {img_url}"
    filename = os.path.basename(img_url)

    final_path = storage.meals_dir / filename
    assert final_path.is_file(), f"Final file not found at meals/: {final_path}"
    assert final_path.stat().st_size > 0, "Final file is empty!"

    # .tmp 폴더에는 파일이 남아있지 않아야 함
    tmp_after = set(os.listdir(storage.tmp_dir))
    new_orphans = (tmp_after - tmp_before) - {".gitkeep"}
    assert len(new_orphans) == 0, f"Orphan files left in .tmp: {new_orphans}"

    print(f"  [+] 추론 성공: {data.get('foodItems', [{}])[0].get('foodName', 'food')} 검출")
    print(f"  [+] meals/ 확정 저장 확인: {final_path} ({final_path.stat().st_size:,} bytes)")
    print(f"  [+] .tmp 고아 파일 0개 확인 (원자적 이동 완료)")

    # 2. 강제 OOM 시뮬레이션 및 롤백 검증
    print("\n[3/6] [Rollback: OOM] GPU VRAM 14GB 초과 시 503 응답 및 .tmp 고아 파일 롤백 삭제 검증...")
    tmp_before = set(os.listdir(storage.tmp_dir))
    resp_oom = requests.post(
        f"{BASE_URL}/vision/estimate",
        headers={**headers_base, "X-Test-Force-Fail": "OOM"},
        cookies=cookies,
        files={"file": ("oom_test.jpg", create_sample_jpeg(), "image/jpeg")},
        timeout=10.0,
    )

    assert resp_oom.status_code == 503, f"Expected 503 for OOM, got {resp_oom.status_code}: {resp_oom.text}"
    err_code = resp_oom.json().get("error", {}).get("code")
    assert err_code == "ERR_CELERY_OOM", f"Expected ERR_CELERY_OOM, got {err_code}"

    tmp_after = set(os.listdir(storage.tmp_dir))
    new_orphans = (tmp_after - tmp_before) - {".gitkeep"}
    assert len(new_orphans) == 0, f"Orphan files left in .tmp after OOM: {new_orphans}"
    print(f"  [+] 503 ERR_CELERY_OOM 정상 반환 확인")
    print(f"  [+] .tmp 고아 파일 자동 롤백 삭제(os.unlink) 확인")

    # 3. 타임아웃(5.0초) 시뮬레이션 및 롤백 검증
    print("\n[4/6] [Rollback: TIMEOUT] 5.0초 타임아웃 발생 시 504 응답 및 .tmp 롤백 삭제 검증...")
    tmp_before = set(os.listdir(storage.tmp_dir))
    resp_timeout = requests.post(
        f"{BASE_URL}/vision/estimate",
        headers={**headers_base, "X-Test-Force-Fail": "TIMEOUT"},
        cookies=cookies,
        files={"file": ("timeout_test.jpg", create_sample_jpeg(), "image/jpeg")},
        timeout=15.0,
    )

    assert resp_timeout.status_code == 504, f"Expected 504 for Timeout, got {resp_timeout.status_code}: {resp_timeout.text}"
    err_code = resp_timeout.json().get("error", {}).get("code")
    assert err_code == "ERR_CELERY_TIMEOUT", f"Expected ERR_CELERY_TIMEOUT, got {err_code}"

    tmp_after = set(os.listdir(storage.tmp_dir))
    new_orphans = (tmp_after - tmp_before) - {".gitkeep"}
    assert len(new_orphans) == 0, f"Orphan files left in .tmp after TIMEOUT: {new_orphans}"
    print(f"  [+] 504 ERR_CELERY_TIMEOUT 정상 반환 확인")
    print(f"  [+] .tmp 고아 파일 자동 롤백 삭제(os.unlink) 확인")

    # 4. 손상된 비정상 이미지 파일 전송 및 롤백 검증
    print("\n[5/6] [Rollback: Corrupted] 비정상 이미지(깨진 바이트) 전송 시 422 및 파일 롤백 검증...")
    tmp_before = set(os.listdir(storage.tmp_dir))
    corrupted_bytes = b"NOT_A_VALID_IMAGE_CONTENT_1234567890"

    resp_corrupt = requests.post(
        f"{BASE_URL}/vision/estimate",
        headers=headers_base,
        cookies=cookies,
        files={"file": ("corrupted.jpg", corrupted_bytes, "image/jpeg")},
        timeout=5.0,
    )

    assert resp_corrupt.status_code == 422, f"Expected 422 for corrupted image, got {resp_corrupt.status_code}"
    err_code = resp_corrupt.json().get("error", {}).get("code")
    assert err_code == "ERR_INVALID_IMAGE", f"Expected ERR_INVALID_IMAGE, got {err_code}"

    tmp_after = set(os.listdir(storage.tmp_dir))
    new_orphans = (tmp_after - tmp_before) - {".gitkeep"}
    assert len(new_orphans) == 0, f"Orphan files left in .tmp after 422: {new_orphans}"
    print(f"  [+] 422 ERR_INVALID_IMAGE 정상 반환 확인")
    print(f"  [+] .tmp 고아 파일 0개 확인")

    # 5. [BR-VAL-003] HEIC 포맷 즉시 415 차단 검증
    print("\n[6/6] [BR-VAL-003: HEIC 415] HEIC 포맷 업로드 시 415 즉시 차단 및 미저장 검증...")
    tmp_before = set(os.listdir(storage.tmp_dir))
    heic_signature = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 100

    resp_heic = requests.post(
        f"{BASE_URL}/vision/estimate",
        headers=headers_base,
        cookies=cookies,
        files={"file": ("iphone_photo.heic", heic_signature, "image/heic")},
        timeout=5.0,
    )

    assert resp_heic.status_code == 415, f"Expected 415 for HEIC, got {resp_heic.status_code}"
    err_code = resp_heic.json().get("error", {}).get("code")
    assert err_code == "ERR_HEIC_UNSUPPORTED", f"Expected ERR_HEIC_UNSUPPORTED, got {err_code}"

    tmp_after = set(os.listdir(storage.tmp_dir))
    new_orphans = (tmp_after - tmp_before) - {".gitkeep"}
    assert len(new_orphans) == 0, f"Files should NOT be saved in .tmp for HEIC: {new_orphans}"
    print(f"  [+] 415 ERR_HEIC_UNSUPPORTED 정상 반환 확인")
    print(f"  [+] .tmp 선저장 없이 즉시 차단 확인")

    print("\n" + "=" * 70)
    print(">> [SUCCESS] Celery 2-Phase Commit 및 수명주기 전 항목 실서버 검증 완료!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
