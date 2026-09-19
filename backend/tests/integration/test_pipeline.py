"""2-Phase Commit 파일 관리 및 Celery 태스크 롤백 통합 테스트 [FR-001, NFR 3.2, Section 11.2]."""
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
from src.core.exceptions import AppException
from src.api.deps import get_current_user
from src.models.entities import User
from src.services.storage_service import StorageService

pytestmark = pytest.mark.asyncio


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
    image = Image.new("RGB", (64, 64), color="red")
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def mock_auth_user():
    """테스트용 인증 유저 의존성 오버라이드 (시드 유저 ID 유지 및 Redis rate_limit 정리)"""
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

    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        r.delete(f"rate_limit:{user_id}")
    except Exception:
        pass


async def test_estimate_2phase_commit_success(mock_auth_user, monkeypatch):
    """[Section 11.2, NFR 3.2] 모의 추론 성공 시 /static/uploads/meals/로 파일 정상 이동(2-Phase Commit) 검증."""
    import src.api.v1.endpoints.vision as vision_mod

    # FakeCeleryWorker 모의 추론 결과 모킹
    food_item_id = str(uuid.uuid4())

    async def fake_dispatch(*args, **kwargs):
        return {
            "foodItems": [
                {
                    "id": food_item_id,
                    "foodId": "FOOD_001",
                    "foodName": "제육볶음",
                    "confidenceScore": 0.95,
                    "classificationConfidence": 0.95,
                    "geometryConfidence": 0.95,
                    "requiresConfirmation": False,
                    "topCandidates": [
                        {
                            "foodId": "FOOD_001",
                            "foodName": "제육볶음",
                            "score": 0.95,
                            "densityGCm3": 0.85,
                            "weightG": 102.0,
                            "caloriesKcal": 204.0,
                            "carbsG": 10.0,
                            "proteinG": 20.0,
                            "fatG": 8.0,
                            "sodiumMg": 300.0,
                        }
                    ],
                    "volumeCm3": 120.0,
                    "densityGCm3": 0.85,
                    "weightG": 102.0,
                    "caloriesKcal": 204.0,
                    "carbsG": 10.0,
                    "proteinG": 20.0,
                    "fatG": 8.0,
                    "sodiumMg": 300.0,
                    "bbox2d": {
                        "ymin": 0.1,
                        "xmin": 0.1,
                        "ymax": 0.5,
                        "xmax": 0.5,
                    },
                    "bbox3d": {
                        "center": {"x": 0.0, "y": 0.0, "z": 0.5},
                        "dimensions": {"x": 0.1, "y": 0.1, "z": 0.05},
                        "rotations": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "vertices": [{"x": 0.0, "y": 0.0, "z": 0.5} for _ in range(8)],
                    },
                }
            ],
            "triggers": {},
            "totalNutrition": {
                "caloriesKcal": 204.0,
                "carbsG": 10.0,
                "proteinG": 20.0,
                "fatG": 8.0,
                "sodiumMg": 300.0,
            },
            "groundPlane": {"a": 0.0, "b": 0.0, "c": 1.0, "d": -0.5},
            "visualization3d": {
                "pointCloud": {"positions": [], "colors": [], "count": 0},
                "tablePlane": {"a": 0.0, "b": 0.0, "c": 1.0, "d": -0.5},
                "cameraFov": 72.0,
            },
            "detectedPills": [],
        }

    monkeypatch.setattr(vision_mod, "dispatch_vision_task", fake_dispatch)

    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}
    file_bytes = generate_valid_jpeg()

    storage = StorageService()
    created_file = None

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
            response = await client.post(
                "/api/v1/vision/estimate",
                files={"file": ("test.jpg", file_bytes, "image/jpeg")},
            )

        assert response.status_code == 200
        res_data = response.json()
        assert res_data["success"] is True

        image_url = res_data["data"]["imageUrl"]
        assert image_url.startswith("/static/uploads/meals/")
        filename = os.path.basename(image_url)
        final_meal_path = os.path.join(str(storage.meals_dir), filename)
        created_file = final_meal_path

        # 1. meals/ 디렉터리로 정상 이동되었는지 검증
        assert os.path.isfile(final_meal_path)
        assert os.path.getsize(final_meal_path) > 0

        # 2. .tmp 폴더에는 파일이 남아있지 않음을 검증
        tmp_files = [f for f in os.listdir(storage.tmp_dir) if not f.startswith(".git")]
        assert len(tmp_files) == 0

    finally:
        if created_file and os.path.exists(created_file):
            try:
                os.unlink(created_file)
            except OSError:
                pass


async def test_estimate_2phase_commit_and_rollback(mock_auth_user):
    """[Section 11.2, NFR 3.2] OOM 발생 시 503(ERR_CELERY_OOM) 응답 및 .tmp 고아 파일 롤백(os.unlink) 삭제 검증."""
    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}

    # 1. 가상 이미지 바이너리 파일 업로드
    file_bytes = generate_valid_jpeg()

    # 2. 강제 예외 발생을 유도하는 헤더 주입 (Mock Worker / Dispatcher에서 인식)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        response = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("test.jpg", file_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "OOM"},
        )

    # 3. 503 응답 확인 및 .tmp 폴더 내 고아 파일(Orphan file) 삭제 확인
    assert response.status_code == 503
    res_data = response.json()
    assert res_data["error"]["code"] == "ERR_CELERY_OOM"

    # 임시 디렉토리가 완전히 비워져 있어야 함을 검증 (롤백 os.unlink 성공)
    storage = StorageService()
    tmp_files = [f for f in os.listdir(storage.tmp_dir) if not f.startswith(".git")]
    assert len(tmp_files) == 0


async def test_estimate_timeout_rollback(mock_auth_user):
    """[Section 10.2, 10.3] Celery 작업 5.0초 타임아웃 시 504(ERR_CELERY_TIMEOUT) 및 .tmp 롤백 삭제 검증."""
    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}
    file_bytes = generate_valid_jpeg()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        response = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("test.jpg", file_bytes, "image/jpeg")},
            headers={"X-Test-Force-Fail": "TIMEOUT"},
        )

    assert response.status_code == 504
    res_data = response.json()
    assert res_data["error"]["code"] == "ERR_CELERY_TIMEOUT"

    storage = StorageService()
    tmp_files = [f for f in os.listdir(storage.tmp_dir) if not f.startswith(".git")]
    assert len(tmp_files) == 0


async def test_estimate_heic_rejected_without_saving(mock_auth_user):
    """[BR-VAL-003, Section 10.2] HEIC 포맷 파일 업로드 시 415(ERR_HEIC_UNSUPPORTED) 즉시 차단."""
    token = make_test_jwt(mock_auth_user.id)
    cookies = {settings.AUTH_COOKIE_NAME: token}

    # HEIC ISOBMFF 헤더 시그니처 바이너리
    heic_bytes = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies=cookies) as client:
        response = await client.post(
            "/api/v1/vision/estimate",
            files={"file": ("photo.heic", heic_bytes, "image/heic")},
        )

    assert response.status_code == 415
    res_data = response.json()
    assert res_data["error"]["code"] == "ERR_HEIC_UNSUPPORTED"
