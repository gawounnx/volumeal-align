"""Opt-in PostgreSQL regression tests. Every test rolls back its outer transaction."""
import copy
import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import bcrypt
import httpx
import pytest
import pytest_asyncio
from PIL import Image
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.main import app
from src.core.config import settings
from src.core.database import get_db_session
from src.models.entities import User, Meal, MealFoodItem, MealCorrectionLog

pytestmark = pytest.mark.skipif(os.getenv('RUN_DB_TESTS') != '1', reason='Set RUN_DB_TESTS=1 to run rolled-back PostgreSQL checks')


@pytest_asyncio.fixture
async def environment():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as db:
            first = User(
                id=uuid.uuid4(),
                email=f'{uuid.uuid4()}@test.invalid',
                name='test',
                role='USER',
                hashed_password=bcrypt.hashpw(b'test-password', bcrypt.gensalt(rounds=4)).decode(),
            )
            other = User(
                id=uuid.uuid4(),
                email=f'{uuid.uuid4()}@test.invalid',
                name='other',
                role='USER',
                hashed_password=first.hashed_password,
            )
            db.add_all([first, other])
            await db.flush()
            await db.commit()

            async def get_test_db():
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as request_db:
                    try:
                        yield request_db
                    except Exception:
                        await request_db.rollback()
                        raise

            app.dependency_overrides[get_db_session] = get_test_db
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                yield client, db, first, other
            app.dependency_overrides.clear()
        await transaction.rollback()
    await engine.dispose()


def auth(user):
    token = jwt.encode(
        {'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {'Authorization': f'Bearer {token}'}


def analysis_result(requires_confirmation=False, detected_pills=None, trigger='test'):
    item = {
        'id': str(uuid.uuid4()),
        'foodId': 'FOOD_TEST',
        'foodName': 'test_food',
        'confidenceScore': 0.9,
        'classificationConfidence': 0.91,
        'geometryConfidence': 0.86,
        'requiresConfirmation': requires_confirmation,
        'topCandidates': [{'foodId': 'FOOD_TEST', 'foodName': 'test_food', 'score': 0.91}],
        'volumeCm3': 100.0,
        'densityGCm3': 1.0,
        'weightG': 100.0,
        'caloriesKcal': 100.0,
        'carbsG': 20.0,
        'proteinG': 3.0,
        'fatG': 1.0,
        'sodiumMg': 4.0,
        'bbox2d': {'xmin': 0.1, 'ymin': 0.1, 'xmax': 0.5, 'ymax': 0.5},
        'bbox3d': {'center': {'x': 0, 'y': 0, 'z': 0.55}, 'dimensions': {'x': 0.1, 'y': 0.1, 'z': 0.1},
                   'rotations': {'x': 0, 'y': 0, 'z': 0}, 'vertices': []}
    }
    return {
        'foodItems': [item],
        'totalNutrition': {key: item[key] for key in ('caloriesKcal', 'carbsG', 'proteinG', 'fatG', 'sodiumMg')},
        'groundPlane': {'a': 0, 'b': 0, 'c': 1, 'd': -0.6},
        'visualization3d': {'pointCloud': {'count': 0, 'positions': [], 'colors': []}},
        'triggers': {item['id']: {trigger.lower()}},
        'detectedPills': detected_pills or [],
    }


@pytest.mark.asyncio
async def test_login_and_auth_flow(environment):
    client, db, first, other = environment
    response = await client.post('/api/v1/auth/login', json={'email': first.email, 'password': 'test-password'})
    assert response.status_code == 200, response.text
    assert "accessToken" in response.json()
    # Ref: [Section 9.3] 기로그인 쿠키 제거 후 비인증 상태에서 잘못된 비밀번호 검증
    client.cookies.clear()
    bad = await client.post('/api/v1/auth/login', json={'email': first.email, 'password': 'wrong'})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_analysis_persistence_and_isolation(environment):
    client, db, first, other = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=SimpleNamespace(process_image=lambda *args: analysis_result())):
        response = await client.post('/api/v1/vision/estimate', headers=auth(first), files={'file': ('test.png', image.getvalue(), 'image/png')})
        assert response.status_code == 200, response.text
        data = response.json()['data']
        assert data['imageUrl'].startswith('/static/uploads/meals/') and data['isCalibrated'] is False
        meal_id = data['mealId']
        detail = await client.get('/api/v1/meals/' + meal_id, headers=auth(first))
        assert detail.status_code == 200, detail.text
        assert len(detail.json()['foodItems']) == 1
        # Ref: [Section 9.3, 14.1] 타인 식단 접근 시 403 Forbidden 반환 검증
        assert (await client.get('/api/v1/meals/' + meal_id, headers=auth(other))).status_code == 403

    res = await client.get('/api/v1/meals', headers=auth(first))
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["success"] is True
    assert res_json["data"]["totalCount"] == 1
    items = res_json["data"]["items"]
    assert [m['id'] for m in items] == [meal_id]


@pytest.mark.asyncio
async def test_low_confidence_analysis_is_not_persisted(environment):
    client, db, first, other = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    pipeline = SimpleNamespace(process_image=lambda *args: analysis_result(True))
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=pipeline):
        response = await client.post('/api/v1/vision/estimate', headers=auth(first),
                                   files={'file': ('test.png', image.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['requiresConfirmation'] is True
    assert data['isPersisted'] is False
    assert (await client.get('/api/v1/meals', headers=auth(first))).json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_failed_save_rolls_back_food_and_meal(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock
    client, db, first, other = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=SimpleNamespace(process_image=lambda *args: analysis_result())):
        with patch('src.api.v1.endpoints.vision.AsyncSession.commit', new=AsyncMock(side_effect=SQLAlchemyError('test failure'))):
            response = await client.post('/api/v1/vision/estimate', headers=auth(first), files={'file': ('test.png', image.getvalue(), 'image/png')})
    assert response.status_code == 503
    assert (await client.get('/api/v1/meals', headers=auth(first))).json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_manual_confirmation_recalculates_and_persists(environment):
    client, db, first, other = environment

    # 1. Simulate estimate returning requiresConfirmation=true
    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    pipeline = SimpleNamespace(process_image=lambda *args: analysis_result(requires_confirmation=True))
    with patch("src.api.v1.endpoints.vision.get_pipeline", return_value=pipeline):
        estimate_res = await client.post(
            "/api/v1/vision/estimate",
            headers=auth(first),
            files={"file": ("test.png", image.getvalue(), "image/png")},
        )
    assert estimate_res.status_code == 200
    est_data = estimate_res.json()["data"]
    assert est_data["requiresConfirmation"] is True
    assert est_data["isPersisted"] is False
    temp_meal_id = est_data["mealId"]
    food_item = est_data["foodItems"][0]
    item_id = food_item["id"]

    # At this point, meals list in DB must be empty
    assert (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"] == []

    # 2. User manually confirms selection as 'spinach_namul'
    confirm_payload = {
        "mealId": temp_meal_id,
        "imageUrl": "https://storage.example.com/meals/confirmed.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "spinach_namul",
            }
        ],
        "volumeData": [
            {
                "itemId": item_id,
                "volumeCm3": 150.0,
                "confidenceScore": 0.95,
                "bbox2d": food_item["bbox2d"],
                "bbox3d": food_item["bbox3d"],
            }
        ],
    }

    confirm_res = await client.post(
        "/api/v1/vision/confirm",
        headers=auth(first),
        json=confirm_payload,
    )
    assert confirm_res.status_code == 200, confirm_res.text
    confirm_json = confirm_res.json()
    assert confirm_json["success"] is True
    assert confirm_json["mealId"] == temp_meal_id
    assert confirm_json["data"]["isPersisted"] is True

    # 3. Verify nutrition recalculation
    nutrition = confirm_json["totalNutrition"]
    assert nutrition["caloriesKcal"] > 0
    assert len(confirm_json["data"]["foodItems"]) == 1
    confirmed_food = confirm_json["data"]["foodItems"][0]
    assert confirmed_food["foodId"] == "spinach_namul"
    assert confirmed_food["foodName"] == "시금치나물"
    assert confirmed_food["volumeCm3"] == 150.0
    assert confirmed_food["weightG"] == round(150.0 * confirmed_food["densityGCm3"], 2)

    # 4. Verify DB persistence and detail endpoint
    detail_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(first))
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["id"] == temp_meal_id
    assert detail["imageUrl"] == "https://storage.example.com/meals/confirmed.jpg"
    assert len(detail["foodItems"]) == 1
    assert detail["foodItems"][0]["foodName"] == "시금치나물"
    assert float(detail["foodItems"][0]["volumeCm3"]) == 150.0

    # 5. Verify ownership isolation (other user cannot access -> 403 Forbidden)
    other_res = await client.get(f"/api/v1/meals/{temp_meal_id}", headers=auth(other))
    assert other_res.status_code == 403


@pytest.mark.asyncio
async def test_manual_confirmation_failure_rolls_back(environment):
    from sqlalchemy.exc import SQLAlchemyError
    from unittest.mock import AsyncMock

    client, db, first, other = environment
    item_id = str(uuid.uuid4())
    meal_id = str(uuid.uuid4())

    confirm_payload = {
        "mealId": meal_id,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "white_rice",
                "volumeCm3": 100.0,
            }
        ]
    }

    with patch("src.api.v1.endpoints.vision.AsyncSession.commit", new=AsyncMock(side_effect=SQLAlchemyError("atomic commit failure"))):
        res = await client.post(
            "/api/v1/vision/confirm",
            headers=auth(first),
            json=confirm_payload,
        )
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "ERR_DATABASE_UNAVAILABLE"

    # Verify no partial meal was saved in DB
    meals = (await client.get("/api/v1/meals", headers=auth(first))).json()["data"]["items"]
    assert all(m["id"] != meal_id for m in meals)


@pytest.mark.asyncio
async def test_registration_and_signup_db_flow(environment):
    client, db, first, other = environment
    new_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    raw_pw = "RegisterTestPassword123!"

    # 1. Successful signup via /api/v1/auth/signup [FR-008]
    reg_res = await client.post(
        "/api/v1/auth/signup",
        json={"email": new_email, "password": raw_pw, "name": "신규가입자"},
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert reg_data["email"] == new_email
    assert reg_data["name"] == "신규가입자"
    assert reg_data["role"] == "USER"
    assert "id" in reg_data

    # 2. Login with newly registered user
    # Ref: [Section 9.3] signup 시 자동 설정된 쿠키를 비워 GUEST 상태로 로그인 시도
    client.cookies.clear()
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": new_email, "password": raw_pw},
    )
    assert login_res.status_code == 200, login_res.text
    assert "accessToken" in login_res.json()
    new_headers = {"Authorization": f"Bearer {login_res.json()['accessToken']}"}

    # 3. Meals list should be empty initially for new user
    meals_res = await client.get("/api/v1/meals", headers=new_headers)
    assert meals_res.status_code == 200
    assert meals_res.json()["data"]["totalCount"] == 0
    assert meals_res.json()["data"]["items"] == []

    # 4. Duplicate registration returns 409 Conflict
    # Ref: [Section 9.3] login 시 설정된 인증 쿠키를 비워 GUEST 상태로 회원가입 시도
    client.cookies.clear()
    dup_res = await client.post(
        "/api/v1/auth/signup",
        json={"email": new_email, "password": raw_pw, "name": "중복가입자"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["detail"] == "이미 등록된 이메일 주소입니다."


@pytest.mark.asyncio
async def test_seed_data_verification_db_flow(environment):
    client, db, first, other = environment

    # Verify seed data inserted from seed.sql exists in DB
    test_user = (await db.execute(select(User).where(User.email == "test@volumeal.io"))).scalar_one_or_none()
    assert test_user is not None
    assert test_user.role == "USER"

    admin_user = (await db.execute(select(User).where(User.email == "admin@volumeal.io"))).scalar_one_or_none()
    assert admin_user is not None
    assert admin_user.role == "ADMIN"

    seed_meal = (await db.execute(select(Meal).where(Meal.id == uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")))).scalar_one_or_none()
    assert seed_meal is not None
    assert seed_meal.status == "ESTIMATED"

    seed_food = (await db.execute(select(MealFoodItem).where(MealFoodItem.id == uuid.UUID("e1a2b3c4-0001-4000-8000-000000000001")))).scalar_one_or_none()
    assert seed_food is not None
    assert seed_food.food_name == "제육볶음"
    assert seed_food.is_user_adjusted is False


@pytest.mark.asyncio
async def test_analysis_persistence_with_is_calibrated_true(environment):
    client, db, first, other = environment
    image = io.BytesIO()
    Image.new('RGB', (100, 100)).save(image, format='PNG')
    with patch('src.api.v1.endpoints.vision.get_pipeline', return_value=SimpleNamespace(process_image=lambda *args: analysis_result())):
        response = await client.post(
            '/api/v1/vision/estimate',
            headers=auth(first),
            files={'file': ('calibrated.png', image.getvalue(), 'image/png')},
            data={'is_calibrated': 'true', 'focal_length_mm': '35.0'},
        )
        assert response.status_code == 200, response.text
        data = response.json()['data']
        assert data['isCalibrated'] is True
        assert data['focalLengthMm'] == 35.0
        meal_id = data['mealId']

        # DB에 is_calibrated=True가 보존되었는지 검증
        db_meal = (await db.execute(select(Meal).where(Meal.id == uuid.UUID(meal_id)))).scalar_one()
        assert db_meal.is_calibrated is True
        assert db_meal.focal_length_mm == 35.0


@pytest.mark.asyncio
async def test_confirmation_weight_update_retry_ownership_and_rollback(environment):
    from unittest.mock import AsyncMock
    from sqlalchemy.exc import SQLAlchemyError
    client, db, first, other = environment
    source = analysis_result()["foodItems"][0]
    nutrition = {**source, "interactionTags": []}
    service = SimpleNamespace(calculate=lambda food_id, volume: dict(nutrition))
    payload = {"mealId": str(uuid.uuid4()), "confirmedItems": [{
        "itemId": source["id"], "foodId": source["foodId"], "volumeCm3": 100, "weightG": 50,
    }]}
    with patch("src.api.v1.endpoints.vision.get_nutrition_service", return_value=service):
        saved = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()['data']['foodItems'][0]['weightG'] == 50
        assert saved.json()['data']['totalNutrition']['caloriesKcal'] == 50
        assert saved.json()['data']['foodItems'][0]['volumeCm3'] == 100
        payload['confirmedItems'][0]['weightG'] = 200
        updated = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert updated.status_code == 200, updated.text
        assert updated.json()['data']['totalNutrition']['caloriesKcal'] == 200
        retry = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert retry.status_code == 200, retry.text
        meals = (await client.get('/api/v1/meals', headers=auth(first))).json()['data']['items']
        assert len([m for m in meals if m['id'] == payload['mealId']]) == 1
        # Ref: [Section 9.3, 14.1] 타인 식단 확정 시 403 Forbidden 반환 검증
        denied = await client.post('/api/v1/vision/confirm', headers=auth(other), json=payload)
        assert denied.status_code == 403
        payload['confirmedItems'][0]['weightG'] = 300
        with patch('src.api.v1.endpoints.vision.AsyncSession.commit', new=AsyncMock(side_effect=SQLAlchemyError('failure'))):
            failed = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
        assert failed.status_code == 503
        detail = (await client.get('/api/v1/meals/' + payload['mealId'], headers=auth(first))).json()
        assert detail['totalCaloriesKcal'] == 200
        assert len(detail['foodItems']) == 1
        for weight in [0, -1, 'NaN', 'Infinity']:
            payload['confirmedItems'][0]['weightG'] = weight
            invalid = await client.post('/api/v1/vision/confirm', headers=auth(first), json=payload)
            assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_idor_protection_in_database_flow(environment):
    """[FR-008, Section 9.1, 9.3, 14.1] 다른 사용자의 토큰 및 HttpOnly 세션 쿠키로 meal_id 조회 및 /confirm 시도 시 403 ERR_ACCESS_DENIED 차단 검증."""
    client, db, first_user, other_user = environment

    # 1. first_user 소유의 식단 생성 (confirmedItems를 통한 원자적 영속화)
    first_meal_id = uuid.uuid4()
    first_item_id = uuid.uuid4()
    initial_payload = {
        "mealId": str(first_meal_id),
        "imageUrl": "https://storage.example.com/meals/idor_test.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": str(first_item_id),
                "foodId": "white_rice",
                "volumeCm3": 95.24,
                "weightG": 100.0,
            }
        ],
    }
    init_res = await client.post("/api/v1/vision/confirm", headers=auth(first_user), json=initial_payload)
    assert init_res.status_code == 200, init_res.text
    assert init_res.json()["data"]["isPersisted"] is True

    # 2. first_user(소유자)는 정상 조회 (200 OK)
    owner_res = await client.get(f"/api/v1/meals/{first_meal_id}", headers=auth(first_user))
    assert owner_res.status_code == 200
    assert owner_res.json()["id"] == str(first_meal_id)

    # 3. other_user의 Bearer 토큰으로 GET /api/v1/meals/{meal_id} 시도 -> 403 ERR_ACCESS_DENIED
    other_get_res = await client.get(f"/api/v1/meals/{first_meal_id}", headers=auth(other_user))
    assert other_get_res.status_code == 403
    other_get_json = other_get_res.json()
    assert other_get_json["success"] is False
    assert other_get_json["error"]["code"] == "ERR_ACCESS_DENIED"
    assert other_get_json["error"]["path"] == f"/api/v1/meals/{first_meal_id}"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in other_get_json["error"]["message"]

    # 4. other_user의 HttpOnly 세션 쿠키(access_token)로 GET /api/v1/meals/{meal_id} 시도 -> 403 ERR_ACCESS_DENIED
    other_token = auth(other_user)["Authorization"].split(" ")[1]
    other_cookie_res = await client.get(
        f"/api/v1/meals/{first_meal_id}",
        cookies={"access_token": other_token, settings.AUTH_COOKIE_NAME: other_token},
    )
    assert other_cookie_res.status_code == 403
    assert other_cookie_res.json()["error"]["code"] == "ERR_ACCESS_DENIED"

    # 5. other_user의 토큰으로 POST /api/v1/vision/confirm 시도 -> 403 ERR_ACCESS_DENIED
    confirm_payload = {
        "mealId": str(first_meal_id),
        "corrections": [
            {
                "foodItemId": str(first_item_id),
                "correctedWeightG": 180.0,
            }
        ],
    }
    other_confirm_res = await client.post(
        "/api/v1/vision/confirm",
        headers=auth(other_user),
        json=confirm_payload,
    )
    assert other_confirm_res.status_code == 403
    other_confirm_json = other_confirm_res.json()
    assert other_confirm_json["success"] is False
    assert other_confirm_json["error"]["code"] == "ERR_ACCESS_DENIED"
    assert other_confirm_json["error"]["path"] == "/api/v1/vision/confirm"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in other_confirm_json["error"]["message"]

    # 6. other_user의 세션 쿠키로 POST /api/v1/confirm (alias) 시도 -> 403 ERR_ACCESS_DENIED
    other_confirm_cookie_res = await client.post(
        "/api/v1/confirm",
        cookies={"access_token": other_token, settings.AUTH_COOKIE_NAME: other_token},
        json=confirm_payload,
    )
    assert other_confirm_cookie_res.status_code == 403
    assert other_confirm_cookie_res.json()["error"]["code"] == "ERR_ACCESS_DENIED"

    # 7. 미등록 meal_id 조회 시 404 Not Found 확인
    not_found_res = await client.get(f"/api/v1/meals/{uuid.uuid4()}", headers=auth(first_user))
    assert not_found_res.status_code == 404


@pytest.mark.asyncio
async def test_manual_correction_ssot_recalculation_and_audit_logging(environment):
    """[FR-007, BR-VAL-004] SSOT 수동 보정 정밀 재계산 및 meal_correction_logs 적재 검증."""
    client, db, first_user, other_user = environment
    meal_id = uuid.uuid4()
    item_id = uuid.uuid4()

    # 1. 초기 식단 확정 (white_rice 100g)
    initial_payload = {
        "mealId": str(meal_id),
        "imageUrl": "https://storage.example.com/meals/p1_4_test.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": str(item_id),
                "foodId": "white_rice",
                "volumeCm3": 95.24,
                "weightG": 100.0,
            }
        ],
    }
    init_res = await client.post("/api/v1/vision/confirm", headers=auth(first_user), json=initial_payload)
    assert init_res.status_code == 200, init_res.text

    # 2. 수동 보정 요청 (100g -> 180g)
    correction_payload = {
        "mealId": str(meal_id),
        "corrections": [
            {
                "foodItemId": str(item_id),
                "correctedWeightG": 180.0,
            }
        ],
    }
    correct_res = await client.post("/api/v1/vision/confirm", headers=auth(first_user), json=correction_payload)
    assert correct_res.status_code == 200, correct_res.text
    correct_data = correct_res.json()["data"]
    corrected_item = correct_data["foodItems"][0]

    # [FR-007, BR-VAL-004] 영양 프로필 정밀 재계산 검증 (white_rice 100g 기준 대비 1.8배)
    assert corrected_item["weightG"] == 180.0
    assert corrected_item["isUserAdjusted"] is True
    assert abs(corrected_item["caloriesKcal"] - 286.97) < 0.1
    assert abs(corrected_item["carbsG"] - 63.18) < 0.1
    assert abs(corrected_item["proteinG"] - 4.93) < 0.1
    assert abs(corrected_item["fatG"] - 0.38) < 0.1
    assert abs(corrected_item["sodiumMg"] - 50.92) < 0.1

    # 3. PostgreSQL DB 쿼리 검증
    db_item = (await db.execute(select(MealFoodItem).where(MealFoodItem.id == item_id))).scalar_one()
    assert db_item.is_user_adjusted is True
    assert float(db_item.weight_g) == 180.0
    assert abs(float(db_item.calories) - 286.97) < 0.1

    logs = (await db.execute(
        select(MealCorrectionLog)
        .where(MealCorrectionLog.meal_food_item_id == item_id)
        .order_by(MealCorrectionLog.created_at.asc())
    )).scalars().all()
    assert len(logs) >= 1
    target_log = [l for l in logs if float(l.new_weight_g) == 180.0][0]
    assert float(target_log.original_weight_g) == 100.0
    assert float(target_log.new_weight_g) == 180.0


