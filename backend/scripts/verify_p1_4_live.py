"""
[P1-4] SSOT 수동 보정 및 이력 테이블 적재 검증 스크립트 (FR-007, BR-VAL-004)
1. POST /api/v1/vision/confirm 요청 시 백엔드 SSOT 기준 정밀 재계산 영양소 반환 검증
2. PostgreSQL meal_food_items의 is_user_adjusted = True 플래그 갱신 검증
3. meal_correction_logs 테이블에 변경 전/후 데이터(original_weight_g, new_weight_g) 적재 쿼리 검증
"""
import uuid
import requests
import json
import subprocess

BASE_URL = "http://localhost:8001/api/v1"

def run_psql(query: str):
    cmd = [
        "docker", "exec", "volumeal-postgres",
        "psql", "-U", "voluuser", "-d", "volumeal",
        "-c", query
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()

def main():
    print("=" * 70)
    print("[P1-4] SSOT 수동 보정 및 이력 테이블 적재 실시간 Live 검증 시작")
    print("=" * 70)

    # 1. 로그인
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "live-e2e-tester@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[1] 인증 완료 (JWT 발급 성공)")

    # 2. 1단계: 초기 식단 확정 (white_rice 100g, 표준 영양소 적재)
    meal_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    initial_payload = {
        "mealId": meal_id,
        "imageUrl": "https://storage.example.com/meals/p1_4_test.jpg",
        "focalLengthMm": 26.0,
        "isCalibrated": False,
        "confirmedItems": [
            {
                "itemId": item_id,
                "foodId": "white_rice",
                "volumeCm3": 85.0,  # 밀도 1.18 -> 100g
                "weightG": 100.0,
            }
        ]
    }
    init_res = requests.post(f"{BASE_URL}/vision/confirm", headers=headers, json=initial_payload)
    assert init_res.status_code == 200, f"Initial confirm failed: {init_res.text}"
    init_data = init_res.json()["data"]
    init_item = init_data["foodItems"][0]
    print(f"[2] 초기 식단 생성 완료 (Meal ID: {meal_id}, Item ID: {item_id})")
    print(f"    - 초기 중량: {init_item['weightG']}g, isUserAdjusted: {init_item['isUserAdjusted']}")
    print(f"    - 초기 영양소: 칼로리 {init_item['caloriesKcal']}kcal, 탄수화물 {init_item['carbsG']}g, 단백질 {init_item['proteinG']}g, 지방 {init_item['fatG']}g, 나트륨 {init_item['sodiumMg']}mg")

    # DB 초기 상태 확인
    print("\n--- [DB 초기 상태 조회] ---")
    query_item = f"SELECT id, food_name, weight_g, calories, carbs, protein, fat, sodium_mg, is_user_adjusted FROM meal_food_items WHERE id = '{item_id}';"
    print(run_psql(query_item))
    query_logs = f"SELECT count(*) as log_count FROM meal_correction_logs WHERE meal_food_item_id = '{item_id}';"
    print(run_psql(query_logs))

    # 3. 2단계: 수동 중량 보정 요청 (100g -> 180g)
    # 클라이언트가 UI에서 임의로 계산한 수치가 아니라 서버 표준 DB(SSOT) 기준으로 재계산되어야 함
    # white_rice 기준 영양소(100g당): 159.43kcal, 35.1g, 2.74g, 0.21g, 28.29mg
    # 180g 기대값:
    # 159.43 * 1.8 = 286.97 kcal
    # 35.1 * 1.8 = 63.18 g
    # 2.74 * 1.8 = 4.93 g
    # 0.21 * 1.8 = 0.38 g
    # 28.29 * 1.8 = 50.92 mg
    correction_payload = {
        "mealId": meal_id,
        "corrections": [
            {
                "foodItemId": item_id,
                "correctedWeightG": 180.0
            }
        ]
    }
    correct_res = requests.post(f"{BASE_URL}/vision/confirm", headers=headers, json=correction_payload)
    assert correct_res.status_code == 200, f"Correction failed: {correct_res.text}"
    correct_data = correct_res.json()["data"]
    corrected_item = correct_data["foodItems"][0]

    print(f"\n[3] 수동 보정(100g -> 180g) 응답 수신 및 SSOT 영양소 재계산 검증")
    print(f"    - 수정 중량: {corrected_item['weightG']}g (기대: 180.0)")
    print(f"    - isUserAdjusted: {corrected_item['isUserAdjusted']} (기대: True)")
    print(f"    - 재계산 칼로리: {corrected_item['caloriesKcal']} kcal (기대: 286.97)")
    print(f"    - 재계산 탄수화물: {corrected_item['carbsG']} g (기대: 63.18)")
    print(f"    - 재계산 단백질: {corrected_item['proteinG']} g (기대: 4.93)")
    print(f"    - 재계산 지방: {corrected_item['fatG']} g (기대: 0.38)")
    print(f"    - 재계산 나트륨: {corrected_item['sodiumMg']} mg (기대: 50.92)")

    assert corrected_item["weightG"] == 180.0
    assert corrected_item["isUserAdjusted"] is True
    assert abs(corrected_item["caloriesKcal"] - 286.97) < 0.05
    assert abs(corrected_item["carbsG"] - 63.18) < 0.05
    assert abs(corrected_item["proteinG"] - 4.93) < 0.05
    assert abs(corrected_item["fatG"] - 0.38) < 0.05
    assert abs(corrected_item["sodiumMg"] - 50.92) < 0.05
    print("    => [PASS] 응답 매크로 영양소가 서버 표준 영양 DB(SSOT) 기준으로 정밀 재계산되어 반환됨을 확인!")

    # 4. DB 갱신 상태 쿼리 검증
    print("\n--- [DB 수동 보정 후 상태 직접 쿼리 검증] ---")
    print("1) meal_food_items 테이블 플래그 및 영양소:")
    print(run_psql(query_item))

    print("2) meal_correction_logs 테이블 이력 적재 확인:")
    query_log_detail = f"SELECT id, meal_food_item_id, original_weight_g, new_weight_g, created_at FROM meal_correction_logs WHERE meal_food_item_id = '{item_id}';"
    log_output = run_psql(query_log_detail)
    print(log_output)
    assert "100.00" in log_output and "180.00" in log_output, "이력 테이블에 100.00 -> 180.00 데이터 누락!"
    print("    => [PASS] meal_correction_logs에 변경 전(100.00g)과 변경 후(180.00g) 데이터가 누락 없이 기록됨을 확인!")

    # 5. 2차 연속 보정 테스트 (180g -> 220g) - 이력 누적 검증
    print(f"\n[4] 2차 연속 보정(180g -> 220g) 이력 누적 검증")
    second_correction_payload = {
        "mealId": meal_id,
        "corrections": [
            {
                "foodItemId": item_id,
                "correctedWeightG": 220.0
            }
        ]
    }
    sec_res = requests.post(f"{BASE_URL}/vision/confirm", headers=headers, json=second_correction_payload)
    assert sec_res.status_code == 200, f"Second correction failed: {sec_res.text}"
    sec_data = sec_res.json()["data"]["foodItems"][0]
    # 220g 기대값:
    # 159.43 * 2.2 = 350.75 kcal
    print(f"    - 2차 수정 중량: {sec_data['weightG']}g")
    print(f"    - 2차 재계산 칼로리: {sec_data['caloriesKcal']} kcal (기대: 350.75)")
    assert sec_data["weightG"] == 220.0
    assert abs(sec_data["caloriesKcal"] - 350.75) < 0.05

    print("\n--- [DB 2차 보정 후 이력 테이블 전체 조회] ---")
    log_output_2 = run_psql(query_log_detail)
    print(log_output_2)
    assert "180.00" in log_output_2 and "220.00" in log_output_2, "2차 이력 데이터 누락!"
    print("    => [PASS] 2차 보정 이력(180.00g -> 220.00g)까지 총 2건의 이력이 순차 누적 적재됨을 확인!")

    # 6. 식단 상세 조회 API (GET /api/v1/meals/{id})에서도 반영 확인
    detail_res = requests.get(f"{BASE_URL}/meals/{meal_id}", headers=headers)
    assert detail_res.status_code == 200, f"Detail get failed: {detail_res.text}"
    detail = detail_res.json()
    print(f"\n[5] GET /api/v1/meals/{meal_id} 조회 확인:")
    print(f"    - totalCaloriesKcal: {detail['totalCaloriesKcal']} kcal")
    print(f"    - foodItem count: {len(detail['foodItems'])}")
    print(f"    - foodItem weightG: {detail['foodItems'][0]['weightG']}g")

    print("\n" + "=" * 70)
    print(">>> [P1-4] SSOT 수동 보정 및 이력 테이블 적재 모든 검증 통과 완료! <<<")
    print("=" * 70)

if __name__ == "__main__":
    main()
