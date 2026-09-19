"""[P0-4, NFR-003, Section 1.3, 3.3, 10.3] Celery Worker VRAM 14GB 샌드박스 격리 및 503 방어 통합 테스트."""
import io
import os
import uuid
import pytest
import pytest_asyncio
import httpx
from PIL import Image
from jose import jwt

from src.main import app
from src.core.config import settings
from src.api.deps import get_current_user
from src.models.entities import User
from src.services.storage_service import StorageService
from app.worker.celery_app import (
    apply_gpu_vram_limit,
    process_vision_pipeline_task,
)


def make_test_jwt(user_id: uuid.UUID) -> str:
    from datetime import datetime, timedelta, timezone
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def generate_valid_jpeg() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (64, 64), color="blue")
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db_session


@pytest.fixture
def mock_auth_user():
    """테스트용 인증 유저 및 DB 세션 의존성 오버라이드, Redis 키 정리."""
    user_id = uuid.UUID("a0000000-0000-0000-0000-000000000002")
    user = User(
        id=user_id,
        email="test@volumeal.io",
        name="테스트사용자",
        role="USER",
        hashed_password="hashed_pw",
    )
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        r.delete(f"rate_limit:{user_id}")
    except Exception:
        pass

    fake_db = AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: fake_db
    yield user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        r.delete(f"rate_limit:{user_id}")
    except Exception:
        pass


def test_pytorch_vram_fraction_clamping_on_gpu():
    """[P0-4 Unit] PyTorch 레벨에서 14/32 fraction 설정 시 14GB 상한 락 작동 검증."""
    try:
        import torch
    except ImportError:
        pytest.skip("PyTorch not installed")

    if not torch.cuda.is_available():
        pytest.skip("CUDA device not available")

    # 1. 14/32 VRAM 한도 적용
    apply_gpu_vram_limit()
    total_mem_bytes = torch.cuda.get_device_properties(0).total_memory
    total_mem_gb = total_mem_bytes / (1024 ** 3)
    target_fraction = 14.0 / 32.0

    # 2. 텐서 할당을 통한 상한 도달 테스트
    tensors = []
    oom_occurred = False
    allocated_gb = 0.0
    try:
        for _ in range(16):
            tensors.append(torch.empty((250_000_000,), dtype=torch.float32, device="cuda:0"))
    except torch.cuda.OutOfMemoryError:
        oom_occurred = True
        allocated_gb = torch.cuda.memory_allocated(0) / (1024 ** 3)
        free_bytes, _ = torch.cuda.mem_get_info(0)
        global_free_gb = free_bytes / (1024 ** 3)
        # 물리 GPU에 여유 공간이 남아있는데도 OOM이 났음을 확인 (샌드박스 격리 증명)
        assert global_free_gb > 2.0
    finally:
        del tensors
        torch.cuda.empty_cache()

    assert oom_occurred is True
    # RTX 5090 (31.36GB) * 0.4375 ≈ 13.72GB -> 할당량은 14.5GB 미만이어야 함
    assert allocated_gb <= 14.5


def test_celery_task_vram_overload_raises_oom():
    """[P0-4 Unit] Celery Task에 VRAM_OVERLOAD 주입 시 ERR_CELERY_OOM 예외 발생 검증."""
    storage = StorageService()
    file_bytes = generate_valid_jpeg()
    file_uuid = uuid.uuid4()
    tmp_filename = f"{file_uuid}.tmp"
    tmp_path = os.path.join(storage.tmp_dir, tmp_filename)
    with open(tmp_path, "wb") as f:
        f.write(file_bytes)

    try:
        with pytest.raises(MemoryError) as exc_info:
            process_vision_pipeline_task(
                temp_image_path=tmp_path,
                force_fail="VRAM_OVERLOAD",
            )
        assert "ERR_CELERY_OOM" in str(exc_info.value)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_fastapi_oom_isolation_and_rollback(mock_auth_user):
    """[P0-4 Integration] Worker OOM 부하 주입 시 FastAPI 503(ERR_CELERY_OOM) 응답 및 고아 파일 롤백 검증."""
    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}
    file_bytes = generate_valid_jpeg()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        response = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("vram_stress.jpg", file_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "VRAM_OVERLOAD"},
        )

    assert response.status_code == 503
    res_data = response.json()
    assert res_data["error"]["code"] == "ERR_CELERY_OOM"

    # .tmp 디렉터리 내 고아 파일이 완전히 롤백(삭제)되었는지 확인
    storage = StorageService()
    tmp_files = [f for f in os.listdir(storage.tmp_dir) if not f.startswith(".git")]
    assert len(tmp_files) == 0


@pytest.mark.asyncio
async def test_fastapi_survives_and_recovers_after_oom(mock_auth_user):
    """[P0-4 Integration] OOM 발생 후에도 메인 FastAPI 서버가 다운되지 않고 후속 정상 요청을 즉시 처리함을 검증."""
    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}
    file_bytes = generate_valid_jpeg()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        # 1. OOM 실패 요청
        oom_res = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("oom_req.jpg", file_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "VRAM_OVERLOAD"},
        )
        assert oom_res.status_code == 503

        # 2. 직후 정상 요청 전송 -> 서버 생존 및 200 OK 처리 확인
        normal_res = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("recovery_req.jpg", file_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "MOCK"},
        )
        assert normal_res.status_code == 200
        normal_data = normal_res.json()
        assert normal_data["success"] is True
