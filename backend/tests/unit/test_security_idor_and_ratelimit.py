"""IDOR 방어 및 Redis Rate Limiter 단위 테스트 [Section 9.3, 10.2, 14.1, 14.2]."""
from datetime import datetime, timedelta, timezone
import io
import time
import uuid
from unittest.mock import AsyncMock, MagicMock
from jose import jwt
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.api.deps import get_current_user
from src.core.config import settings
from src.core.database import get_db_session
from src.core.exceptions import AppException, RateLimitException
from src.core.rate_limiter import check_rate_limit, get_redis_client
from src.models.entities import Meal, MealFoodItem, User


class FakeRedisPipeline:
    def __init__(self, storage, key):
        self.storage = storage
        self.key = key
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", min_score, max_score))
        return self

    def zadd(self, key, mapping):
        self.commands.append(("zadd", mapping))
        return self

    def zcard(self, key):
        self.commands.append(("zcard",))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", seconds))
        return self

    async def execute(self):
        zset = self.storage.setdefault(self.key, [])
        results = []
        for cmd in self.commands:
            if cmd[0] == "zremrangebyscore":
                min_s, max_s = cmd[1], cmd[2]
                self.storage[self.key] = [(elem, score) for elem, score in zset if not (min_s <= score <= max_s)]
                zset = self.storage[self.key]
                results.append(1)
            elif cmd[0] == "zadd":
                for member, score in cmd[1].items():
                    zset.append((member, score))
                results.append(len(cmd[1]))
            elif cmd[0] == "zcard":
                results.append(len(zset))
            elif cmd[0] == "expire":
                results.append(True)
        return results


class FakeRedisClient:
    def __init__(self):
        self.storage = {}

    def pipeline(self, transaction=True):
        return FakeRedisPipeline(self.storage, "dummy")

    def pipeline_for_key(self, key):
        return FakeRedisPipeline(self.storage, key)


@pytest.fixture
def fake_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def security_test_client(fake_db):
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="security_user@example.com",
        name="보안테스트유저",
        role="USER",
        hashed_password="hash",
    )
    fake_redis = FakeRedisClient()

    # pipeline 호출 시 실제 키를 추적하도록 오버라이드
    def custom_pipeline(transaction=True):
        pipe = FakeRedisPipeline(fake_redis.storage, None)
        # key를 첫 번째 zadd/zcard 명령 등에서 포착
        orig_zrem = pipe.zremrangebyscore
        def wrap_zrem(key, min_s, max_s):
            pipe.key = key
            return orig_zrem(key, min_s, max_s)
        pipe.zremrangebyscore = wrap_zrem
        return pipe
    fake_redis.pipeline = custom_pipeline

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: fake_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, mock_user, fake_db, fake_redis

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_check_rate_limit_sliding_window_logic():
    """[Section 14.2] check_rate_limit 슬라이딩 윈도우 알고리즘 검증 (분당 5회 제한)."""
    fake_redis = FakeRedisClient()
    def custom_pipeline(transaction=True):
        pipe = FakeRedisPipeline(fake_redis.storage, None)
        orig_zrem = pipe.zremrangebyscore
        def wrap_zrem(key, min_s, max_s):
            pipe.key = key
            return orig_zrem(key, min_s, max_s)
        pipe.zremrangebyscore = wrap_zrem
        return pipe
    fake_redis.pipeline = custom_pipeline

    user_id = str(uuid.uuid4())

    # 1. 1~5회 호출: 모두 통과
    for _ in range(5):
        await check_rate_limit(fake_redis, user_id=user_id, limit=5, window_sec=60)

    # 2. 6회 호출: 429 ERR_RATE_LIMIT 발생
    with pytest.raises(AppException) as exc_info:
        await check_rate_limit(fake_redis, user_id=user_id, limit=5, window_sec=60)

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "ERR_RATE_LIMIT"


def test_rate_limiter_blocks_excessive_estimate_calls(security_test_client, monkeypatch):
    """[Section 14.2] POST /api/v1/vision/estimate 엔드포인트 6회 호출 시 429 차단 검증."""
    client, mock_user, fake_db, fake_redis = security_test_client

    # analyze_upload 모킹하여 GPU/파일 시스템 연산 우회
    async def fake_analyze_upload(**kwargs):
        cal = kwargs.get("calibration")
        if cal is not None:
            cal.update({"focal_length_mm": 26.0, "is_calibrated": False})
        return {
            "foodItems": [],
            "triggers": {},
            "totalNutrition": {"caloriesKcal": 100, "carbsG": 10, "proteinG": 5, "fatG": 2, "sodiumMg": 50},
            "imageUrl": "http://test/img.jpg",
            "groundPlane": {"a": 0.0, "b": 1.0, "c": 0.0, "d": 0.0},
            "visualization3d": {"pointCloud": {"count": 0, "positions": [], "colors": []}},
        }
    monkeypatch.setattr("src.api.v1.endpoints.vision.analyze_upload", fake_analyze_upload)
    monkeypatch.setattr("src.api.v1.endpoints.vision.evaluate_drug_warnings", AsyncMock(return_value=([], [])))

    img_buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="blue").save(img_buffer, format="JPEG")
    img_bytes = img_buffer.getvalue()

    # 1~5회 호출: 200 OK
    for _ in range(5):
        res = client.post(
            "/api/v1/vision/estimate",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            data={"focal_length_mm": "26.0"},
        )
        assert res.status_code == 200

    # 6회 호출: 429 Too Many Requests (ERR_RATE_LIMIT)
    res_blocked = client.post(
        "/api/v1/vision/estimate",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
        data={"focal_length_mm": "26.0"},
    )
    assert res_blocked.status_code == 429
    res_json = res_blocked.json()
    assert res_json["success"] is False
    assert res_json["error"]["code"] == "ERR_RATE_LIMIT"


def test_get_meal_detail_idor_protection(security_test_client):
    """[Section 9.3, 14.1] GET /api/v1/meals/{meal_id} IDOR 방어: 타인 소유 시 403 Forbidden 반환."""
    client, mock_user, fake_db, _ = security_test_client

    other_user_id = uuid.uuid4()
    target_meal_id = uuid.uuid4()

    # 1. 대상 식단이 타인 소유인 경우
    # 1st query: WHERE id = :meal_id AND user_id = :current_user_id -> None
    # 2nd query: WHERE id = :meal_id -> target_meal_id (존재함)
    first_query_res = MagicMock()
    first_query_res.scalar_one_or_none.return_value = None

    second_query_res = MagicMock()
    second_query_res.scalar_one_or_none.return_value = target_meal_id

    fake_db.execute.side_effect = [first_query_res, second_query_res]

    response = client.get(f"/api/v1/meals/{target_meal_id}")
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ERR_ACCESS_DENIED"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in data["error"]["message"]

    # 2. 식단이 아예 존재하지 않는 경우: 404 Not Found
    first_query_res2 = MagicMock()
    first_query_res2.scalar_one_or_none.return_value = None

    second_query_res2 = MagicMock()
    second_query_res2.scalar_one_or_none.return_value = None

    fake_db.execute.side_effect = [first_query_res2, second_query_res2]

    response404 = client.get(f"/api/v1/meals/{uuid.uuid4()}")
    assert response404.status_code == 404


def test_confirm_meal_idor_protection(security_test_client):
    """[Section 9.3, 14.1] POST /api/v1/vision/confirm IDOR 방어: 타인 소유 식단 확정 시 403 Forbidden 반환."""
    client, mock_user, fake_db, _ = security_test_client

    other_user_id = uuid.uuid4()
    target_meal_id = uuid.uuid4()

    other_meal = Meal(
        id=target_meal_id,
        user_id=other_user_id,  # 타인 소유
        image_url="http://test/img.jpg",
        focal_length_mm=26.0,
        is_calibrated=False,
        total_calories_kcal=500.0,
        total_carbs_g=40.0,
        total_protein_g=20.0,
        total_fat_g=10.0,
        total_sodium_mg=200.0,
    )
    other_meal.food_items = [
        MealFoodItem(
            id=uuid.uuid4(),
            meal_id=target_meal_id,
            food_name="타인음식",
            volume_cm3=100.0,
            density_g_cm3=1.0,
            weight_g=100.0,
            calories_kcal=150.0,
            carbs_g=10.0,
            protein_g=5.0,
            fat_g=2.0,
            sodium_mg=50.0,
        )
    ]

    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = other_meal
    fake_db.execute.return_value = scalars_mock

    payload = {
        "mealId": str(target_meal_id),
        "corrections": [
            {
                "foodItemId": str(other_meal.food_items[0].id),
                "correctedWeightG": 120.0,
            }
        ],
    }

    response = client.post("/api/v1/vision/confirm", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ERR_ACCESS_DENIED"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in data["error"]["message"]


def _generate_test_jwt(user_id: uuid.UUID) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def test_cookie_session_idor_protection_get_meal(fake_db):
    """[FR-008, Section 9.1, 9.3, 14.1] A 사용자의 HttpOnly 세션 쿠키로 B 사용자의 식단 조회(GET /meals/{mealId}) 시 403 차단 검증."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    meal_b_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email="user_a@example.com",
        name="사용자A",
        role="USER",
        hashed_password="hash",
    )

    # get_current_user에서 db.get(User, user_a_id) 호출 시 user_a 반환
    fake_db.get.return_value = user_a

    # 1st query: WHERE id = :meal_b_id AND user_id = :user_a_id -> None
    first_res = MagicMock()
    first_res.scalar_one_or_none.return_value = None

    # 2nd query: WHERE id = :meal_b_id -> meal_b_id (타인 소유 식단 존재)
    second_res = MagicMock()
    second_res.scalar_one_or_none.return_value = meal_b_id

    fake_db.execute.side_effect = [first_res, second_res]

    token_a = _generate_test_jwt(user_a_id)

    app.dependency_overrides[get_db_session] = lambda: fake_db
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            # HttpOnly 세션 쿠키 주입: access_token 및 volumeal_access
            client.cookies.set("access_token", token_a, path="/")
            client.cookies.set(settings.AUTH_COOKIE_NAME, token_a, path="/")

            response = client.get(f"/api/v1/meals/{meal_b_id}")
            assert response.status_code == 403
            body = response.json()
            assert body["success"] is False
            assert body["error"]["code"] == "ERR_ACCESS_DENIED"
            assert "본인 소유의 식단에만 접근할 수 있습니다" in body["error"]["message"]
            assert body["error"]["path"] == f"/api/v1/meals/{meal_b_id}"
    finally:
        app.dependency_overrides.clear()


def test_cookie_session_idor_protection_confirm_meal(fake_db):
    """[FR-008, Section 9.1, 9.3, 14.1] A 사용자의 HttpOnly 세션 쿠키로 B 사용자의 식단 확정(POST /confirm) 시 403 차단 검증."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    meal_b_id = uuid.uuid4()
    food_item_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email="user_a@example.com",
        name="사용자A",
        role="USER",
        hashed_password="hash",
    )

    fake_db.get.return_value = user_a

    meal_b = Meal(
        id=meal_b_id,
        user_id=user_b_id,  # User B 소유
        image_url="http://test/food.jpg",
        focal_length_mm=26.0,
        is_calibrated=False,
        total_calories_kcal=400.0,
        total_carbs_g=30.0,
        total_protein_g=20.0,
        total_fat_g=10.0,
        total_sodium_mg=150.0,
    )
    meal_b.food_items = [
        MealFoodItem(
            id=food_item_id,
            meal_id=meal_b_id,
            food_name="타인음식",
            volume_cm3=100.0,
            density_g_cm3=1.0,
            weight_g=100.0,
            calories_kcal=150.0,
            carbs_g=10.0,
            protein_g=5.0,
            fat_g=2.0,
            sodium_mg=50.0,
        )
    ]

    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = meal_b
    fake_db.execute.return_value = scalars_mock

    token_a = _generate_test_jwt(user_a_id)

    app.dependency_overrides[get_db_session] = lambda: fake_db
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            client.cookies.set("access_token", token_a, path="/")
            client.cookies.set(settings.AUTH_COOKIE_NAME, token_a, path="/")

            payload = {
                "mealId": str(meal_b_id),
                "corrections": [
                    {
                        "foodItemId": str(food_item_id),
                        "correctedWeightG": 130.0,
                    }
                ],
            }

            # 1. /api/v1/vision/confirm 엔드포인트 검증
            res1 = client.post("/api/v1/vision/confirm", json=payload)
            assert res1.status_code == 403
            body1 = res1.json()
            assert body1["success"] is False
            assert body1["error"]["code"] == "ERR_ACCESS_DENIED"
            assert "본인 소유의 식단에만 접근할 수 있습니다" in body1["error"]["message"]

            # 2. /api/v1/confirm (하위 호환 alias) 엔드포인트 검증
            res2 = client.post("/api/v1/confirm", json=payload)
            assert res2.status_code == 403
            body2 = res2.json()
            assert body2["success"] is False
            assert body2["error"]["code"] == "ERR_ACCESS_DENIED"
            assert "본인 소유의 식단에만 접근할 수 있습니다" in body2["error"]["message"]
    finally:
        app.dependency_overrides.clear()
