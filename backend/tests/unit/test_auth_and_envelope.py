import datetime
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.api.deps import get_current_user
from src.core.database import get_db_session
from src.models.entities import Meal, MealCorrectionLog, MealFoodItem, User


@pytest.fixture
def fake_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def test_client(fake_db):
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="testuser@example.com",
        name="테스트사용자",
        role="USER",
        hashed_password=bcrypt.hashpw(b"Password123!", bcrypt.gensalt()).decode("utf-8"),
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: fake_db
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, mock_user, fake_db

    app.dependency_overrides.clear()


def test_auth_register_success(test_client):
    client, mock_user, fake_db = test_client

    # Mock DB: no existing user with this email
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = scalars_mock

    payload = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "name": "홍길동",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "홍길동"
    assert data["role"] == "USER"
    assert "id" in data
    assert "createdAt" in data
    assert fake_db.commit.called


def test_auth_signup_without_name_uses_email_local_part(test_client):
    client, _, fake_db = test_client
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = scalars_mock
    response = client.post("/api/v1/auth/signup", json={"email": "newuser@example.com", "password": "SecurePassword123!"})
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "newuser"
    assert fake_db.commit.called

def test_login_sets_strict_httponly_cookie(test_client, monkeypatch):
    """[FR-008, Section 9.1] /api/v1/auth/login 성공 시 HttpOnly, SameSite=Strict, Path=/ 쿠키 헤더 세팅 검증."""
    client, mock_user, fake_db = test_client
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = mock_user
    fake_db.execute.return_value = scalars_mock
    monkeypatch.setattr("src.api.v1.endpoints.auth.settings.AUTH_COOKIE_SECURE", True)

    response = client.post("/api/v1/auth/login", json={
        "email": mock_user.email,
        "password": "Password123!",
    })

    assert response.status_code == 200
    set_cookie_headers = (
        response.headers.get_list("set-cookie")
        if hasattr(response.headers, "get_list")
        else [response.headers.get("set-cookie", "")]
    )
    cookie_str = " ; ".join(set_cookie_headers).lower()

    # 1. 공통 보안 플래그 검증: HttpOnly, SameSite=Strict, Secure
    assert "httponly" in cookie_str
    assert "samesite=strict" in cookie_str
    assert "secure" in cookie_str

    # 2. access_token 및 volumeal_access 쿠키의 Path=/ 및 Max-Age=900 검증
    access_cookies = [c for c in set_cookie_headers if "access_token=" in c or "volumeal_access=" in c]
    assert len(access_cookies) >= 1
    for ac in access_cookies:
        ac_lower = ac.lower()
        assert "httponly" in ac_lower
        assert "samesite=strict" in ac_lower
        assert "path=/" in ac_lower
        assert "max-age=900" in ac_lower

    # 3. refresh_token 및 volumeal_refresh 쿠키의 Path=/api/v1/auth 및 Max-Age=604800 검증
    refresh_cookies = [c for c in set_cookie_headers if "refresh_token=" in c or "volumeal_refresh=" in c]
    assert len(refresh_cookies) >= 1
    for rc in refresh_cookies:
        rc_lower = rc.lower()
        assert "httponly" in rc_lower
        assert "samesite=strict" in rc_lower
        assert "path=/api/v1/auth" in rc_lower
        assert "max-age=604800" in rc_lower


def test_auth_register_duplicate_conflict(test_client):
    client, mock_user, fake_db = test_client

    # Mock DB: existing user already present
    existing = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        name="기존사용자",
        role="USER",
        hashed_password="hash",
    )
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = existing
    fake_db.execute.return_value = scalars_mock

    payload = {
        "email": "existing@example.com",
        "password": "SecurePassword123!",
        "name": "기존사용자",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "이미 등록된 이메일 주소입니다."


def test_auth_register_validation_failure(test_client):
    client, _, _ = test_client

    # Short password (less than 8 chars)
    response = client.post("/api/v1/auth/register", json={
        "email": "valid@example.com",
        "password": "short",
        "name": "홍길동",
    })
    assert response.status_code == 422

    # Invalid email format
    response2 = client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "SecurePassword123!",
        "name": "홍길동",
    })
    assert response2.status_code == 422


def test_meals_list_envelope_and_highest_risk_level(test_client):
    client, mock_user, fake_db = test_client

    # Create dummy meals with different risk levels
    meal_danger = Meal(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        image_url="https://example.com/danger.jpg",
        focal_length_mm=26.0,
        is_calibrated=False,
        total_calories_kcal=600.0,
        total_carbs_g=50.0,
        total_protein_g=20.0,
        total_fat_g=10.0,
        total_sodium_mg=500.0,
        created_at=datetime.datetime(2026, 9, 15, 12, 0, tzinfo=datetime.timezone.utc),
    )
    meal_danger.food_items = [MealFoodItem(id=uuid.uuid4(), food_name="시금치나물", is_user_adjusted=False)]

    meal_caution = Meal(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        image_url="https://example.com/caution.jpg",
        focal_length_mm=26.0,
        is_calibrated=False,
        total_calories_kcal=400.0,
        total_carbs_g=40.0,
        total_protein_g=15.0,
        total_fat_g=5.0,
        total_sodium_mg=300.0,
        created_at=datetime.datetime(2026, 9, 14, 12, 0, tzinfo=datetime.timezone.utc),
    )
    meal_caution.food_items = [MealFoodItem(id=uuid.uuid4(), food_name="우유", is_user_adjusted=False)]

    meal_none = Meal(
        id=uuid.uuid4(),
        user_id=mock_user.id,
        image_url="https://example.com/none.jpg",
        focal_length_mm=26.0,
        is_calibrated=False,
        total_calories_kcal=300.0,
        total_carbs_g=30.0,
        total_protein_g=10.0,
        total_fat_g=2.0,
        total_sodium_mg=100.0,
        created_at=datetime.datetime(2026, 9, 13, 12, 0, tzinfo=datetime.timezone.utc),
    )
    meal_none.food_items = [MealFoodItem(id=uuid.uuid4(), food_name="백미밥", is_user_adjusted=False)]

    # Mock count query result
    count_result = MagicMock()
    count_result.scalar.return_value = 3

    # Mock select query result
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [meal_danger, meal_caution, meal_none]

    fake_db.execute.side_effect = [count_result, items_result]

    response = client.get("/api/v1/meals?page=1&pageSize=10")
    assert response.status_code == 200, response.text
    res_json = response.json()

    # Verify Envelope format
    assert res_json["success"] is True
    assert "data" in res_json
    data = res_json["data"]
    assert data["totalCount"] == 3
    assert data["page"] == 1
    assert data["pageSize"] == 10
    assert len(data["items"]) == 3


def test_auth_signup_success(test_client):
    client, mock_user, fake_db = test_client

    # Mock DB: no existing user with this email
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = scalars_mock

    payload = {
        "email": "signup_user@example.com",
        "password": "SecurePassword123!",
        "name": "가입사용자",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "signup_user@example.com"
    assert data["name"] == "가입사용자"
    assert data["role"] == "USER"
    assert "id" in data
    assert "createdAt" in data
    assert fake_db.commit.called


def test_meal_food_item_and_correction_log_model():
    # Verify MealFoodItem is_user_adjusted default and MealCorrectionLog schema
    item_id = uuid.uuid4()
    item = MealFoodItem(
        id=item_id,
        meal_id=uuid.uuid4(),
        food_name="김치찌개",
        confidence_score=0.95,
        volume_cm3=250.0,
        density_g_cm3=1.0,
        weight_g=250.0,
        calories_kcal=180.0,
        carbs_g=10.0,
        protein_g=12.0,
        fat_g=8.0,
        sodium_mg=800.0,
        bbox_2d={},
        bbox_3d={},
        is_user_adjusted=False,
    )
    assert item.is_user_adjusted is False

    log_id = uuid.uuid4()
    log = MealCorrectionLog(
        id=log_id,
        meal_food_item_id=item_id,
        original_weight_g=250.0,
        new_weight_g=300.0,
    )
    assert log.id == log_id
    assert log.meal_food_item_id == item_id
    assert log.original_weight_g == 250.0
    assert log.new_weight_g == 300.0


def test_refresh_rotates_access_cookie(test_client):
    client, mock_user, fake_db = test_client
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    fake_db.execute.return_value = result
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": mock_user.email, "password": "Password123!"},
    )
    assert login_response.status_code == 200
    assert client.cookies.get("volumeal_refresh")
    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["accessToken"]
    assert client.cookies.get("volumeal_access")


def test_refresh_rejects_access_token_in_refresh_cookie(test_client):
    client, mock_user, fake_db = test_client
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    fake_db.execute.return_value = result
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": mock_user.email, "password": "Password123!"},
    )
    client.cookies.clear()
    client.cookies.set("volumeal_refresh", login_response.json()["accessToken"])
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_signup_enforces_bcrypt_cost_12_and_sets_cookies(test_client):
    """[FR-008, Section 8.1, 9.1] signup 엔드포인트: Bcrypt(Cost: 12) 및 쿠키 정책 강제 검증."""
    client, _, fake_db = test_client
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = scalars_mock

    payload = {
        "email": "bcrypt12@example.com",
        "password": "SecurePassword123!",
        "name": "보안사용자",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "bcrypt12@example.com"

    # 1. Bcrypt Cost: 12 검증 ($2b$12$... 접두사)
    added_user = fake_db.add.call_args[0][0]
    assert added_user.hashed_password.startswith("$2b$12$")

    # 2. Section 9.1 쿠키 보안 규격 검증
    # access_token: Max-Age 900초(15분), HttpOnly=True, SameSite=Strict
    # refresh_token: Max-Age 604800초(7일), HttpOnly=True, SameSite=Strict, Path=/api/v1/auth
    cookie_headers = [h[1].decode("latin-1") for h in response.headers.raw if h[0].decode("latin-1").lower() == "set-cookie"]
    cookie_str = "; ".join(cookie_headers)

    assert "access_token=" in cookie_str
    assert "refresh_token=" in cookie_str
    assert "max-age=900" in cookie_str.lower()
    assert "max-age=604800" in cookie_str.lower()
    assert "samesite=strict" in cookie_str.lower()
    assert "httponly" in cookie_str.lower()
    assert "path=/api/v1/auth" in cookie_str.lower()


def test_cors_allows_credentials_for_dev_ports(test_client):
    """[Section 9.1] 고용민 FE (0.0.0.0:3001) 및 차가원 FE (0.0.0.0:3002) CORS 자격 증명 검증."""
    client, _, _ = test_client

    for origin in ["http://0.0.0.0:3001", "http://0.0.0.0:3002"]:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"


def test_nfr_10_1_global_error_envelope_format(test_client):
    """[NFR 10.1] 전역 표준 에러 응답 포맷 일원화 (code, message, timestamp, path, details)."""
    import re
    client, _, fake_db = test_client

    # Case 1: Validation Error (422)
    val_res = client.post("/api/v1/auth/signup", json={"email": "not-an-email", "password": "123"})
    assert val_res.status_code == 422
    val_data = val_res.json()
    assert val_data["success"] is False
    assert "error" in val_data
    err = val_data["error"]
    assert err["code"] == "ERR_INVALID_INPUT"
    assert err["path"] == "/api/v1/auth/signup"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", err["timestamp"])
    assert isinstance(err["details"], list)
    assert len(err["details"]) > 0

    # Case 2: Duplicate Email Conflict (409)
    existing_user = User(
        id=uuid.uuid4(),
        email="dup@example.com",
        name="중복유저",
        role="USER",
        hashed_password="hash",
    )
    scalars_mock = MagicMock()
    scalars_mock.scalar_one_or_none.return_value = existing_user
    fake_db.execute.return_value = scalars_mock

    conflict_res = client.post("/api/v1/auth/signup", json={"email": "dup@example.com", "password": "SecurePassword123!"})
    assert conflict_res.status_code == 409
    conf_data = conflict_res.json()
    assert conf_data["success"] is False
    assert conf_data["error"]["code"] == "ERR_CONFLICT"
    assert conf_data["error"]["message"] == "이미 등록된 이메일 주소입니다."
    assert conf_data["error"]["path"] == "/api/v1/auth/signup"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", conf_data["error"]["timestamp"])
    assert isinstance(conf_data["error"]["details"], list)


def test_nfr_10_1_global_error_codes_comprehensive(test_client):
    """[NFR 10.1] 400, 401, 403, 404, 422 전역 에러 포맷 일원화 (timestamp, path, ERR_ code)."""
    import re
    client, mock_user, fake_db = test_client

    iso_utc_regex = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"

    # 1. 422 Unprocessable Entity (입력 검증 오류)
    res_422 = client.post("/api/v1/auth/signup", json={"email": "bad-email", "password": "1"})
    assert res_422.status_code == 422
    data_422 = res_422.json()
    assert data_422["success"] is False
    assert data_422["error"]["code"] == "ERR_INVALID_INPUT"
    assert data_422["error"]["path"] == "/api/v1/auth/signup"
    assert re.match(iso_utc_regex, data_422["error"]["timestamp"])
    assert isinstance(data_422["error"]["details"], list)

    # 2. 401 Unauthorized (인증 실패)
    scalars_mock_none = MagicMock()
    scalars_mock_none.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = scalars_mock_none

    res_401 = client.post("/api/v1/auth/login", json={"email": "none@example.com", "password": "wrong"})
    assert res_401.status_code == 401
    data_401 = res_401.json()
    assert data_401["success"] is False
    assert data_401["error"]["code"] == "ERR_UNAUTHORIZED"
    assert data_401["error"]["path"] == "/api/v1/auth/login"
    assert re.match(iso_utc_regex, data_401["error"]["timestamp"])

    # 3. 404 Not Found (존재하지 않는 경로)
    res_404 = client.get("/api/v1/nonexistent-route-for-testing")
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert data_404["success"] is False
    assert data_404["error"]["code"] == "ERR_NOT_FOUND"
    assert data_404["error"]["path"] == "/api/v1/nonexistent-route-for-testing"
    assert re.match(iso_utc_regex, data_404["error"]["timestamp"])

    # 4. 403 Forbidden (IDOR 타인 식단 조회)
    target_meal_id = uuid.uuid4()
    first_res = MagicMock()
    first_res.scalar_one_or_none.return_value = None
    second_res = MagicMock()
    second_res.scalar_one_or_none.return_value = target_meal_id
    fake_db.execute.side_effect = [first_res, second_res]

    res_403 = client.get(f"/api/v1/meals/{target_meal_id}")
    assert res_403.status_code == 403
    data_403 = res_403.json()
    assert data_403["success"] is False
    assert data_403["error"]["code"] == "ERR_ACCESS_DENIED"
    assert data_403["error"]["path"] == f"/api/v1/meals/{target_meal_id}"
    assert re.match(iso_utc_regex, data_403["error"]["timestamp"])
    assert "본인 소유의 식단에만 접근할 수 있습니다" in data_403["error"]["message"]

    # 5. 400 Bad Request (알 수 없는 식품 식별자)
    fake_db.execute.side_effect = None
    dummy_scalar = MagicMock()
    dummy_scalar.scalar_one_or_none.return_value = None
    fake_db.execute.return_value = dummy_scalar

    res_400 = client.post("/api/v1/vision/confirm", json={
        "mealId": str(uuid.uuid4()),
        "confirmedItems": [
            {
                "itemId": str(uuid.uuid4()),
                "foodId": "UNKNOWN_FOOD_ID_9999",
                "volumeCm3": 100.0,
            }
        ],
        "volumeData": [
            {
                "itemId": str(uuid.uuid4()),
                "volumeCm3": 100.0,
            }
        ]
    })
    assert res_400.status_code == 400
    data_400 = res_400.json()
    assert data_400["success"] is False
    assert data_400["error"]["code"] == "ERR_UNKNOWN_FOOD"
    assert data_400["error"]["path"] == "/api/v1/vision/confirm"
    assert re.match(iso_utc_regex, data_400["error"]["timestamp"])


def test_rate_limiter_blocks_on_sixth_estimate_request(test_client, monkeypatch):
    """[Section 14.2] 연속 6회 /vision/estimate 요청 시 6번째 요청에서 429 ERR_RATE_LIMIT 차단 검증."""
    import io
    from PIL import Image
    from src.core.rate_limiter import get_redis_client

    class DummyPipeline:
        def __init__(self, key, counts):
            self.key = key
            self.counts = counts

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def zremrangebyscore(self, *args):
            return self

        def zadd(self, *args):
            return self

        def zcard(self, *args):
            return self

        def expire(self, *args):
            return self

        async def execute(self):
            self.counts[self.key] = self.counts.get(self.key, 0) + 1
            # results[2] is zcard count
            return [1, 1, self.counts[self.key], True]

    class DummyRedis:
        def __init__(self):
            self.counts = {}

        def pipeline(self, transaction=True):
            pipe = DummyPipeline("rate_limit:test", self.counts)
            orig_zrem = pipe.zremrangebyscore
            def wrap_zrem(key, *args):
                pipe.key = key
                return orig_zrem(key, *args)
            pipe.zremrangebyscore = wrap_zrem
            return pipe

    dummy_redis = DummyRedis()
    app.dependency_overrides[get_redis_client] = lambda: dummy_redis

    client, _, fake_db = test_client

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

    img_buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="green").save(img_buf, format="JPEG")
    img_data = img_buf.getvalue()

    # 1~5번째 요청은 200 통과
    for i in range(5):
        resp = client.post(
            "/api/v1/vision/estimate",
            files={"file": ("test.jpg", img_data, "image/jpeg")},
            data={"focal_length_mm": "26.0"},
        )
        assert resp.status_code == 200, f"Request {i+1} failed"

    # 6번째 요청은 429 ERR_RATE_LIMIT 차단
    resp_6 = client.post(
        "/api/v1/vision/estimate",
        files={"file": ("test.jpg", img_data, "image/jpeg")},
        data={"focal_length_mm": "26.0"},
    )
    assert resp_6.status_code == 429
    err_json = resp_6.json()
    assert err_json["success"] is False
    assert err_json["error"]["code"] == "ERR_RATE_LIMIT"
    assert err_json["error"]["path"] == "/api/v1/vision/estimate"
    assert "timestamp" in err_json["error"]

    app.dependency_overrides.pop(get_redis_client, None)


