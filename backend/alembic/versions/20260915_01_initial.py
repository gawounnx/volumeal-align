"""Initial UUID application schema, matching src/models/entities.py (SSOT), for new databases.

Existing unversioned databases must be audited before explicitly stamping this revision.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "20260915_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('meals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('image_url', sa.String(length=1024), nullable=False),
    sa.Column('focal_length_mm', sa.Numeric(6, 2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('total_calories', sa.Numeric(8, 2), nullable=False),
    sa.Column('total_carbs', sa.Numeric(8, 2), nullable=False),
    sa.Column('total_protein', sa.Numeric(8, 2), nullable=False),
    sa.Column('total_fat', sa.Numeric(8, 2), nullable=False),
    sa.Column('is_calibrated', sa.Boolean(), nullable=True),
    sa.Column('total_sodium_mg', sa.Numeric(8, 2), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('meal_food_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('meal_id', sa.UUID(), nullable=False),
    sa.Column('food_id', sa.String(length=64), nullable=False),
    sa.Column('food_name', sa.String(length=100), nullable=False),
    sa.Column('volume_cm3', sa.Numeric(8, 2), nullable=False),
    sa.Column('weight_g', sa.Numeric(8, 2), nullable=False),
    sa.Column('calories', sa.Numeric(8, 2), nullable=False),
    sa.Column('carbs', sa.Numeric(8, 2), nullable=False),
    sa.Column('protein', sa.Numeric(8, 2), nullable=False),
    sa.Column('fat', sa.Numeric(8, 2), nullable=False),
    sa.Column('is_user_adjusted', sa.Boolean(), nullable=False),
    sa.Column('confidence_score', sa.Numeric(6, 4), nullable=True),
    sa.Column('density_g_cm3', sa.Numeric(6, 4), nullable=True),
    sa.Column('sodium_mg', sa.Numeric(8, 2), nullable=True),
    sa.Column('bbox_2d', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('bbox_3d', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['meal_id'], ['meals.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('meal_correction_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('meal_food_item_id', sa.UUID(), nullable=False),
    sa.Column('original_weight_g', sa.Numeric(8, 2), nullable=False),
    sa.Column('new_weight_g', sa.Numeric(8, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['meal_food_item_id'], ['meal_food_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_meals_user_id', 'meals', ['user_id'])
    op.create_index('ix_meal_food_items_meal_id', 'meal_food_items', ['meal_id'])
    op.create_index('ix_meal_correction_logs_meal_food_item_id', 'meal_correction_logs', ['meal_food_item_id'])

def downgrade():
    raise RuntimeError("Automatic downgrade is disabled to protect meal data.")
