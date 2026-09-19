-- ==============================================================================
-- VoluMeal-Align Database Schema Initialization (SSOT)
-- Reference: Requirement Specification.md Section 7.1
-- Tables: users, meals, meal_food_items, meal_correction_logs
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 7.1.1 users 테이블 [FR-008]
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7.1.2 meals 테이블 [FR-001, FR-006]
CREATE TABLE IF NOT EXISTS meals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url VARCHAR(1024) NOT NULL,
    focal_length_mm NUMERIC(6, 2) NOT NULL DEFAULT 26.00,
    status VARCHAR(20) NOT NULL DEFAULT 'ESTIMATED',
    total_calories NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    total_carbs NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    total_protein NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    total_fat NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    is_calibrated BOOLEAN DEFAULT FALSE,
    total_sodium_mg NUMERIC(8, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_meals_user_id ON meals (user_id);
CREATE INDEX IF NOT EXISTS ix_meals_status ON meals (status);
CREATE INDEX IF NOT EXISTS ix_meals_created_at ON meals (created_at);

-- 7.1.3 meal_food_items 테이블 [FR-003, FR-004, FR-007]
CREATE TABLE IF NOT EXISTS meal_food_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_id UUID NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_id VARCHAR(64) NOT NULL DEFAULT 'FOOD_001',
    food_name VARCHAR(100) NOT NULL,
    volume_cm3 NUMERIC(8, 2) NOT NULL,
    weight_g NUMERIC(8, 2) NOT NULL,
    calories NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    carbs NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    protein NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    fat NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    is_user_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_score NUMERIC(6, 4) DEFAULT 1.0,
    density_g_cm3 NUMERIC(6, 4) DEFAULT 1.0,
    sodium_mg NUMERIC(8, 2) DEFAULT 0.0,
    bbox_2d JSONB DEFAULT '{}'::jsonb,
    bbox_3d JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_meal_food_items_meal_id ON meal_food_items (meal_id);
CREATE INDEX IF NOT EXISTS ix_meal_food_items_food_id ON meal_food_items (food_id);

-- 7.1.4 meal_correction_logs 테이블 [FR-007]
CREATE TABLE IF NOT EXISTS meal_correction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_food_item_id UUID NOT NULL REFERENCES meal_food_items(id) ON DELETE CASCADE,
    original_weight_g NUMERIC(8, 2) NOT NULL,
    new_weight_g NUMERIC(8, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_meal_correction_logs_item_id ON meal_correction_logs (meal_food_item_id);
CREATE INDEX IF NOT EXISTS ix_meal_correction_logs_created_at ON meal_correction_logs (created_at);
