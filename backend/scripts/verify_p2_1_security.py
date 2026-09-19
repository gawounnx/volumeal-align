"""[P2-1] HttpOnly 쿠키 인증 및 IDOR 방어 실서버 라이브 검증 스크립트 (FR-008, Section 9).

검증 항목:
1. /api/v1/auth/login 및 /api/v1/auth/signup 응답의 Set-Cookie 헤더:
   - HttpOnly, SameSite=Strict, Path=/ 플래그 확인
   - refresh_token의 Path=/api/v1/auth 플래그 확인
2. A 사용자의 세션 쿠키로 B 사용자의 mealId에 접근 시 IDOR 방어:
   - GET /api/v1/meals/{mealId} -> 403 Forbidden (ERR_ACCESS_DENIED)
   - POST /api/v1/vision/confirm -> 403 Forbidden (ERR_ACCESS_DENIED)
   - POST /api/v1/confirm -> 403 Forbidden (ERR_ACCESS_DENIED)
3. B 사용자 본인의 세션 쿠키로는 정상 200 OK 조회 확인.
"""
import json
import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8001"


def verify_p2_1():
    print(f"=== [P2-1] Live Verification against {BASE_URL} ===")

    # 1. 회원가입 및 로그인 쿠키 플래그 검증
    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    print(f"\n[Step 1] User A ({user_a_email}) Signup & Login...")
    client_signup = httpx.Client(base_url=BASE_URL)
    res_signup_a = client_signup.post(
        "/api/v1/auth/signup",
        json={"email": user_a_email, "password": password, "name": "User A"},
    )
    assert res_signup_a.status_code == 201, f"User A signup failed: {res_signup_a.text}"

    # Section 9.3: /login은 미인증 상태에서만 접근 허용되므로 새 클라이언트로 로그인 테스트
    client_a = httpx.Client(base_url=BASE_URL)
    res_login_a = client_a.post(
        "/api/v1/auth/login",
        json={"email": user_a_email, "password": password},
    )
    assert res_login_a.status_code == 200, f"User A login failed: {res_login_a.text}"

    set_cookie_headers = res_login_a.headers.get_list("set-cookie")
    print(f"Set-Cookie count: {len(set_cookie_headers)}")
    for sc in set_cookie_headers:
        print(f"  - {sc}")

    # Set-Cookie 검증
    access_cookie_found = False
    refresh_cookie_found = False
    for sc in set_cookie_headers:
        sc_lower = sc.lower()
        if "access_token=" in sc_lower or "volumeal_access=" in sc_lower:
            access_cookie_found = True
            assert "httponly" in sc_lower, f"access_token missing HttpOnly: {sc}"
            assert "samesite=strict" in sc_lower, f"access_token missing SameSite=Strict: {sc}"
            assert "path=/" in sc_lower, f"access_token missing Path=/: {sc}"
            assert "max-age=900" in sc_lower, f"access_token missing Max-Age=900: {sc}"
        if "refresh_token=" in sc_lower or "volumeal_refresh=" in sc_lower:
            refresh_cookie_found = True
            assert "httponly" in sc_lower, f"refresh_token missing HttpOnly: {sc}"
            assert "samesite=strict" in sc_lower, f"refresh_token missing SameSite=Strict: {sc}"
            assert "path=/api/v1/auth" in sc_lower, f"refresh_token missing Path=/api/v1/auth: {sc}"
            assert "max-age=604800" in sc_lower, f"refresh_token missing Max-Age=604800: {sc}"

    assert access_cookie_found, "access_token cookie not found in login response"
    assert refresh_cookie_found, "refresh_token cookie not found in login response"
    print("  -> Step 1 PASS: HttpOnly, SameSite=Strict, Path=/ confirmed on login cookies!")

    # 2. User B 회원가입 및 식단 생성
    print(f"\n[Step 2] User B ({user_b_email}) Signup & Meal Creation...")
    client_b = httpx.Client(base_url=BASE_URL)
    res_signup_b = client_b.post(
        "/api/v1/auth/signup",
        json={"email": user_b_email, "password": password, "name": "User B"},
    )
    assert res_signup_b.status_code == 201, f"User B signup failed: {res_signup_b.text}"

    meal_b_id = str(uuid.uuid4())
    item_b_id = str(uuid.uuid4())

    confirm_payload = {
        "mealId": meal_b_id,
        "imageUrl": "https://storage.example.com/meals/user_b_meal.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": item_b_id,
                "foodId": "white_rice",
                "volumeCm3": 120.0,
                "weightG": 126.0,
            }
        ],
    }

    res_b_meal = client_b.post("/api/v1/vision/confirm", json=confirm_payload)
    assert res_b_meal.status_code == 200, f"User B meal creation failed: {res_b_meal.text}"
    meal_data = res_b_meal.json()
    assert meal_data["success"] is True
    assert meal_data["data"]["isPersisted"] is True
    print(f"  -> User B meal created successfully with mealId={meal_b_id}")

    # User B 본인 조회 확인 (Happy Path)
    res_b_get = client_b.get(f"/api/v1/meals/{meal_b_id}")
    assert res_b_get.status_code == 200, f"User B failed to view own meal: {res_b_get.text}"
    assert res_b_get.json()["id"] == meal_b_id
    print("  -> User B self-access verification: 200 OK PASS!")

    # 3. User A의 세션 쿠키로 User B 식단 조회 시 IDOR 차단 검증
    print(f"\n[Step 3] User A accesses User B's meal (GET /api/v1/meals/{meal_b_id})...")
    res_idor_get = client_a.get(f"/api/v1/meals/{meal_b_id}")
    print(f"  Status: {res_idor_get.status_code}")
    print(f"  Body: {res_idor_get.text}")
    assert res_idor_get.status_code == 403, f"Expected 403 Forbidden, got {res_idor_get.status_code}"
    err_data = res_idor_get.json()
    assert err_data["success"] is False
    assert err_data["error"]["code"] == "ERR_ACCESS_DENIED"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in err_data["error"]["message"]
    print("  -> Step 3 PASS: IDOR blocked with 403 ERR_ACCESS_DENIED!")

    # 4. User A의 세션 쿠키로 User B 식단 확정/수정(POST /confirm) 시 IDOR 차단 검증
    print(f"\n[Step 4] User A modifies User B's meal (POST /api/v1/vision/confirm)...")
    res_idor_confirm = client_a.post(
        "/api/v1/vision/confirm",
        json={
            "mealId": meal_b_id,
            "corrections": [
                {
                    "foodItemId": item_b_id,
                    "correctedWeightG": 200.0,
                }
            ],
        },
    )
    print(f"  Status: {res_idor_confirm.status_code}")
    print(f"  Body: {res_idor_confirm.text}")
    assert res_idor_confirm.status_code == 403, f"Expected 403 Forbidden, got {res_idor_confirm.status_code}"
    err_confirm = res_idor_confirm.json()
    assert err_confirm["success"] is False
    assert err_confirm["error"]["code"] == "ERR_ACCESS_DENIED"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in err_confirm["error"]["message"]
    print("  -> Step 4 PASS: Vision confirm IDOR blocked with 403 ERR_ACCESS_DENIED!")

    # 5. User A의 세션 쿠키로 User B 식단 확정(POST /confirm alias) 시 IDOR 차단 검증
    print(f"\n[Step 5] User A modifies User B's meal via alias (POST /api/v1/confirm)...")
    res_idor_alias = client_a.post(
        "/api/v1/confirm",
        json={
            "mealId": meal_b_id,
            "corrections": [
                {
                    "foodItemId": item_b_id,
                    "correctedWeightG": 250.0,
                }
            ],
        },
    )
    print(f"  Status: {res_idor_alias.status_code}")
    print(f"  Body: {res_idor_alias.text}")
    assert res_idor_alias.status_code == 403, f"Expected 403 Forbidden, got {res_idor_alias.status_code}"
    err_alias = res_idor_alias.json()
    assert err_alias["success"] is False
    assert err_alias["error"]["code"] == "ERR_ACCESS_DENIED"
    assert "본인 소유의 식단에만 접근할 수 있습니다" in err_alias["error"]["message"]
    print("  -> Step 5 PASS: Alias confirm IDOR blocked with 403 ERR_ACCESS_DENIED!")

    print("\n=======================================================")
    print("🎉 ALL P2-1 VERIFICATIONS PASSED SUCCESSFULLY! 🎉")
    print("=======================================================")


if __name__ == "__main__":
    verify_p2_1()
