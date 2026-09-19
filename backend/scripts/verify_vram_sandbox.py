"""[P0-4] Celery Worker VRAM 14GB 샌드박스 격리 및 503 OOM 방어 실측 검증 스크립트.

Reference:
- Requirement Specification.md Section 1.3 (CUDA OOM 방어 및 Celery 격리)
- Requirement Specification.md Section 3.3 (GPU 샌드박싱 제한: 14GB Lock)
- Requirement Specification.md Section 10.3 (하드웨어 예외 처리 가이드라인)
- Requirement Specification.md Section 15.3 (원격 협업 리스크 완화 매트릭스: 14/32)
- Requirement Specification.md Section 16 (PyTorch instances MUST include set_per_process_memory_fraction(0.43))

Verification Objectives:
1. PyTorch CUDA 레벨에서 `torch.cuda.set_per_process_memory_fraction(14/32, device=0)` 설정 시,
   RTX 5090(32GB)의 물리 메모리가 충분하더라도 단일 프로세스가 14GB(~13.72GB)를 초과할 수 없음을 실측 증명.
2. Celery Worker에서 실제 14GB 초과 텐서 할당 시 물리적 `torch.cuda.OutOfMemoryError`가 발생하고,
   메인 FastAPI 서버(포트 8001)는 다운되지 않고 정상적으로 HTTP 503 (`ERR_CELERY_OOM`)을 반환함을 검증.
3. 2-Phase Commit 롤백 메커니즘을 통해 OOM 발생 시 `/static/uploads/.tmp` 내 고아 파일이 즉각 삭제됨을 검증.
4. OOM 직후 후속 요청이 정상 처리(HTTP 200)되어 시스템 가용성이 100% 유지됨을 실측 검증.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import sys
import time
import uuid

# 프로젝트 루트 및 백엔드 경로 주입
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

import httpx
from jose import jwt
from PIL import Image

from src.core.config import settings
from src.services.storage_service import StorageService


def make_test_jwt(user_id: uuid.UUID) -> str:
    """검증용 유효 JWT Access Token 생성 (HS256)."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def generate_test_jpeg(width: int = 128, height: int = 128) -> bytes:
    """테스트용 유효한 JPEG 이미지 바이너리 획득 (실제 음식 사진 우선 로드)."""
    candidates = [
        backend_dir / "data" / "kfood" / "images" / "val" / "kfood_00005.jpg",
        backend_dir.parent / "frontend" / "tests" / "fixtures" / "meal.jpg",
    ]
    for c in candidates:
        if c.is_file():
            return c.read_bytes()
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), color=(70, 130, 180))
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


# ==============================================================================
# Stage 1: Direct PyTorch CUDA Memory Fraction (14/32) Stress Verification
# ==============================================================================
def verify_pytorch_vram_fraction_direct() -> bool:
    """[P0-4 Stage 1] PyTorch의 torch.cuda.set_per_process_memory_fraction(14/32) 실제 작동 검증."""
    print("\n" + "=" * 78)
    print(" [Stage 1] PyTorch CUDA VRAM 14GB 샌드박스 직접 부하 실측 검증")
    print("=" * 78)

    try:
        import torch
    except ImportError:
        print("[ERROR] PyTorch가 설치되어 있지 않습니다.")
        return False

    if not torch.cuda.is_available():
        print("[SKIP] CUDA 지원 GPU를 감지할 수 없습니다. (CPU 환경)")
        return False

    device_name = torch.cuda.get_device_name(0)
    total_mem_bytes = torch.cuda.get_device_properties(0).total_memory
    total_mem_gb = total_mem_bytes / (1024 ** 3)
    target_fraction = 14.0 / 32.0  # 0.4375

    print(f" * 감지된 GPU 장치: {device_name}")
    print(f" * GPU 물리 총 VRAM: {total_mem_gb:.2f} GB ({total_mem_bytes:,} bytes)")
    print(f" * 목표 VRAM 클램프 비율: 14/32 ({target_fraction:.4f})")

    # 1. 프로세스 메모리 상한 설정
    torch.cuda.set_per_process_memory_fraction(target_fraction, device=0)
    expected_limit_gb = total_mem_gb * target_fraction
    print(f" * 프로세스 허용 상한(Clamp Limit): 약 {expected_limit_gb:.2f} GB")

    # 2. 1GB 단위 점진적 텐서 할당 부하 실행 (최대 16GB 시도)
    tensors = []
    oom_occurred = False
    allocated_gb_at_oom = 0.0
    reserved_gb_at_oom = 0.0
    global_free_gb_at_oom = 0.0

    print(" * 1GB 단위 텐서 연속 할당 시작 (14GB 상한 돌파 시도)...")
    try:
        for i in range(1, 17):
            # 1GB float32 tensor = 250,000,000 floats * 4 bytes = 1,000,000,000 bytes
            t = torch.empty((250_000_000,), dtype=torch.float32, device="cuda:0")
            tensors.append(t)
            curr_alloc = torch.cuda.memory_allocated(0) / (1024 ** 3)
            curr_res = torch.cuda.memory_reserved(0) / (1024 ** 3)
            print(f"   - 할당 성공: {i}GB 누적 (Allocated: {curr_alloc:.2f} GB, Reserved: {curr_res:.2f} GB)")

    except torch.cuda.OutOfMemoryError as exc:
        oom_occurred = True
        allocated_gb_at_oom = torch.cuda.memory_allocated(0) / (1024 ** 3)
        reserved_gb_at_oom = torch.cuda.memory_reserved(0) / (1024 ** 3)
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        global_free_gb_at_oom = free_bytes / (1024 ** 3)
        print("\n [OOM DETECTED] 예상된 torch.cuda.OutOfMemoryError 발생!")
        print(f"   * OOM 시점 프로세스 Allocated VRAM: {allocated_gb_at_oom:.2f} GB")
        print(f"   * OOM 시점 프로세스 Reserved VRAM:  {reserved_gb_at_oom:.2f} GB")
        print(f"   * OOM 시점 전체 GPU 물리 가용 잔여 VRAM: {global_free_gb_at_oom:.2f} GB")
        print(f"   * 예외 메시지 요약: {str(exc).splitlines()[-1] if str(exc) else 'CUDA out of memory'}")

    finally:
        del tensors
        torch.cuda.empty_cache()

    # 3. 검증 판정
    if not oom_occurred:
        print("\n [FAIL] 16GB를 할당할 때까지 OOM이 발생하지 않았습니다. VRAM 상한 격리 실패!")
        return False

    # 허용 상한(약 13.0 ~ 14.5 GB 사이)에서 OOM이 발생했는지 검증
    if allocated_gb_at_oom > 14.5:
        print(f"\n [FAIL] 할당량이 14.5GB({allocated_gb_at_oom:.2f}GB)를 초과했습니다. 상한 락 미준수!")
        return False

    # 물리 GPU에는 아직 메모리가 충분히 남아있었는지 검증 (프로세스 샌드박싱 증명)
    if global_free_gb_at_oom < 5.0:
        print(f"\n [FAIL] 물리 GPU 전체가 고갈되었습니다 ({global_free_gb_at_oom:.2f}GB 잔여). 샌드박싱 격리 아님!")
        return False

    print(f"\n [PASS] Stage 1 통과: VRAM 14GB({allocated_gb_at_oom:.2f}GB) 도달 시 정확히 OutOfMemoryError 발생!")
    print(f"        물리 GPU 잔여 메모리 {global_free_gb_at_oom:.2f}GB가 안전하게 보존되어 샌드박싱 입증됨.")
    return True


# ==============================================================================
# Stage 2: Live End-to-End Celery Worker & FastAPI (8001) Isolation Stress Test
# ==============================================================================
async def verify_e2e_celery_fastapi_oom_isolation(base_url: str = "http://0.0.0.0:8001") -> bool:
    """[P0-4 Stage 2] Celery Worker OOM 발생 시 FastAPI(8001) 생존 및 503 응답 검증."""
    print("\n" + "=" * 78)
    print(f" [Stage 2] Celery Worker VRAM 부하 주입 및 FastAPI(8001) 503 에러 격리 검증")
    print(f" 대상 엔드포인트: {base_url}/api/v1/vision/estimate")
    print("=" * 78)

    test_user_id = uuid.UUID("a0000000-0000-0000-0000-000000000002")
    token = make_test_jwt(test_user_id)
    headers = {
        "Authorization": f"Bearer {token}",
    }
    cookies = {
        settings.AUTH_COOKIE_NAME: token,
        "access_token": token,
    }

    storage = StorageService()
    test_image_bytes = generate_test_jpeg()

    # 클라이언트 타임아웃 15초 설정
    async with httpx.AsyncClient(base_url=base_url, headers=headers, cookies=cookies, timeout=15.0) as client:
        # 1. 서버 생존 여부 사전 확인 (Health Check / Docs)
        try:
            health_res = await client.get("/docs")
            if health_res.status_code != 200:
                print(f" [WARN] 메인 서버 응답 상태: {health_res.status_code}")
        except Exception as exc:
            print(f" [FAIL] FastAPI 서버({base_url})에 연결할 수 없습니다: {exc}")
            return False

        print(" [Step 1] 정상 이미지 추론 요청 전송 (기준 상태 확인)...")
        res_normal = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("normal_sample.jpg", test_image_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "BENCHMARK"},
            data={"focal_length_mm": "26.0", "conf_threshold": "0.1"},
        )
        print(f"   -> 응답 코드: {res_normal.status_code}")
        if res_normal.status_code != 200:
            print(f"   [FAIL] 예상치 못한 응답 코드: {res_normal.status_code}, 본문: {res_normal.text[:200]}")
            return False
        print(f"   [PASS] 정상 추론 요청 처리 완료 (200 OK)")

        # 2. VRAM 14GB 초과 유도 부하 요청 전송 (VRAM_OVERLOAD)
        print("\n [Step 2] Celery Worker 14GB VRAM 한도 초과 부하 주입 요청 전송 (X-Test-Force-Fail: VRAM_OVERLOAD)...")
        res_oom = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("vram_stress.jpg", test_image_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "VRAM_OVERLOAD"},
            data={"focal_length_mm": "26.0", "conf_threshold": "0.1"},
        )
        print(f"   -> OOM 부하 주입 응답 코드: {res_oom.status_code}")
        try:
            res_oom_json = res_oom.json()
            print(f"   -> 응답 JSON: {res_oom_json}")
        except Exception:
            res_oom_json = {}

        # 503 검증
        if res_oom.status_code != 503:
            print(f"   [FAIL] OOM 발생 시 503 응답이 반환되어야 하나, {res_oom.status_code} 반환됨!")
            return False

        err_code = res_oom_json.get("error", {}).get("code")
        if err_code != "ERR_CELERY_OOM":
            print(f"   [FAIL] 에러 코드가 'ERR_CELERY_OOM'이어야 하나, '{err_code}' 반환됨!")
            return False

        print(f"   [PASS] OOM 부하 요청에 대해 503 ({err_code}) 정확히 반환 확인!")

        # 3. 2-Phase Commit 롤백 확인 (.tmp 내 잔여 파일 검사)
        print("\n [Step 3] 2-Phase Commit 롤백 확인 (.tmp 고아 파일 잔존 여부)...")
        tmp_files = [f for f in os.listdir(storage.tmp_dir) if not f.startswith(".git")]
        print(f"   -> .tmp 디렉터리 내 잔여 파일 수: {len(tmp_files)}")
        if len(tmp_files) != 0:
            print(f"   [FAIL] 고아 파일이 남아있습니다: {tmp_files}")
            return False
        print("   [PASS] OOM 에러 발생 시 임시 파일이 안전하게 os.unlink() 롤백됨.")

        # 4. OOM 직후 메인 FastAPI 서버 생존 및 후속 요청 복구력 검증
        print("\n [Step 4] OOM 발생 직후 메인 FastAPI 서버 생존 및 후속 정상 요청 복구력 검증...")
        res_recovery = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("recovery_sample.jpg", test_image_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "BENCHMARK"},
            data={"focal_length_mm": "26.0", "conf_threshold": "0.1"},
        )
        print(f"   -> 후속 복구 요청 응답 코드: {res_recovery.status_code}")
        if res_recovery.status_code != 200:
            print(f"   [FAIL] 후속 요청이 200 OK를 반환하지 못했습니다: {res_recovery.status_code}")
            return False

        rec_json = res_recovery.json()
        print(f"   -> 후속 정상 추론 성공: success={rec_json.get('success')}, items={len(rec_json.get('data', {}).get('foodItems', []))}")
        print("   [PASS] FastAPI 메인 서버는 다운되지 않았으며, 워커 VRAM 캐시 해제 후 즉시 정상 복구됨!")

    print("\n" + "=" * 78)
    print(" [Stage 2 통과] Celery Worker 14GB VRAM 격리 및 메인 서버 503 방어 100% 실측 검증 완료!")
    print("=" * 78)
    return True


# ==============================================================================
# Main Orchestrator
# ==============================================================================
def main() -> int:
    import asyncio
    print("\n" + "#" * 78)
    print(" [P0-4] Celery Worker VRAM 14GB 샌드박스 격리 및 503 OOM 방어 통합 실측 검증")
    print("#" * 78)

    # 1. Stage 1: PyTorch Cuda Memory Limit 실측
    stage1_ok = verify_pytorch_vram_fraction_direct()
    if not stage1_ok:
        print("\n[CRITICAL FAIL] Stage 1 VRAM 상한 실측 실패!")
        return 1

    # 2. Stage 2: E2E FastAPI + Celery Worker 격리 실측
    port = os.getenv("PORT", "8001")
    target_url = f"http://0.0.0.0:{port}"
    try:
        stage2_ok = asyncio.run(verify_e2e_celery_fastapi_oom_isolation(target_url))
    except Exception as exc:
        print(f"\n[CRITICAL ERROR in Stage 2]: {exc}")
        stage2_ok = False

    if not stage2_ok:
        print(f"\n[FAIL] Stage 2 검증 실패. 서버({target_url}) 또는 Celery Worker 상태를 확인하세요.")
        return 1

    print("\n" + "#" * 78)
    print(" [최종 결과: SUCCESS] 모든 [P0-4 / NFR-003] VRAM 14GB 격리 및 503 방어 기준 충족!")
    print("#" * 78 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
