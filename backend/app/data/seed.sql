-- ==============================================================================
-- VoluMeal-Align Local Verification Seed Data
-- Reference: Requirement Specification.md Section 7.3
-- Owner: 백엔드/인프라 담당 [고용민]
-- Description: 프론트엔드 개발자(차가원)가 로컬 DB에 접근하여 독립적인 UI 렌더링
--              및 이력 조회 테스트를 수행할 수 있도록 기본 데이터를 적재합니다.
-- ==============================================================================

-- 1. 사용자 계정 시드 (Password: 'Test1234!') [FR-008]
INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
VALUES
  ('a0000000-0000-0000-0000-000000000001', 'admin@volumeal.io', '$2b$12$KIXH/C./T21GjEa8f6Tf5.RMBF4Q.R1sWlX6p8oFh1c8F3Yd6pQxK', 'ADMIN', NOW(), NOW()),
  ('a0000000-0000-0000-0000-000000000002', 'test@volumeal.io', '$2b$12$KIXH/C./T21GjEa8f6Tf5.RMBF4Q.R1sWlX6p8oFh1c8F3Yd6pQxK', 'USER', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- 2. 식단 마스터 시드 [FR-001, FR-006]
INSERT INTO meals (id, user_id, image_url, focal_length_mm, status, total_calories, total_carbs, total_protein, total_fat, created_at, updated_at)
VALUES (
  'f47ac10b-58cc-4372-a567-0e02b2c3d479', 'a0000000-0000-0000-0000-000000000002',
  '/static/uploads/meals/seed_sample.jpg', 26.00, 'ESTIMATED',
  250.00, 30.50, 15.20, 7.40, NOW(), NOW()
) ON CONFLICT (id) DO NOTHING;

-- 3. 개별 음식 시드 [FR-003, FR-004, FR-007]
INSERT INTO meal_food_items (id, meal_id, food_id, food_name, volume_cm3, weight_g, calories, carbs, protein, fat, is_user_adjusted, created_at, updated_at)
VALUES (
  'e1a2b3c4-0001-4000-8000-000000000001', 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
  'FOOD_001', '제육볶음', 120.00, 150.00, 250.00, 30.50, 15.20, 7.40, FALSE, NOW(), NOW()
) ON CONFLICT (id) DO NOTHING;
