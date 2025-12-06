"""Add deposit corridors and level config

Revision ID: 20251206_000001
Revises: 20251205_000001
Create Date: 2025-12-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251206_000001'
down_revision = '20251205_000001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Создать таблицу deposit_level_configs
    op.create_table(
        'deposit_level_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('level_type', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('min_amount', sa.Numeric(18, 8), nullable=False),
        sa.Column('max_amount', sa.Numeric(18, 8), nullable=False),
        sa.Column('plex_per_dollar', sa.Integer(), default=10),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('roi_percent', sa.Numeric(5, 2), default=2.0),
        sa.Column('roi_cap_percent', sa.Integer(), default=500),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_deposit_level_configs_level_type', 'deposit_level_configs', ['level_type'])
    op.create_index('ix_deposit_level_configs_order', 'deposit_level_configs', ['order'])
    op.create_index('ix_deposit_level_configs_is_active', 'deposit_level_configs', ['is_active'])

    # 2. Добавить новые поля в таблицу deposits
    op.add_column('deposits', sa.Column('deposit_type', sa.String(20), nullable=False, server_default='level_1'))
    op.add_column('deposits', sa.Column('min_amount', sa.Numeric(18, 8), nullable=False, server_default='0'))
    op.add_column('deposits', sa.Column('max_amount', sa.Numeric(18, 8), nullable=False, server_default='0'))
    op.add_column('deposits', sa.Column('usdt_confirmed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('deposits', sa.Column('usdt_confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('deposits', sa.Column('plex_daily_required', sa.Numeric(18, 8), nullable=False, server_default='0'))

    op.create_index('ix_deposits_deposit_type', 'deposits', ['deposit_type'])
    op.create_index('ix_deposits_usdt_confirmed', 'deposits', ['usdt_confirmed'])

    # 3. Заполнить начальные данные deposit_level_configs
    op.execute("""
        INSERT INTO deposit_level_configs (level_type, name, "order", min_amount, max_amount, plex_per_dollar, is_active)
        VALUES
            ('test', 'Тестовый', 0, 30, 100, 10, true),
            ('level_1', 'Уровень 1', 1, 100, 500, 10, true),
            ('level_2', 'Уровень 2', 2, 700, 1200, 10, true),
            ('level_3', 'Уровень 3', 3, 1400, 2200, 10, true),
            ('level_4', 'Уровень 4', 4, 2500, 3500, 10, true),
            ('level_5', 'Уровень 5', 5, 4000, 7000, 10, true)
    """)

    # 4. Миграция существующих депозитов - конвертация level в deposit_type
    # Обновляем все существующие депозиты согласно их level
    op.execute("""
        UPDATE deposits SET
            deposit_type = CASE
                WHEN level = 1 THEN 'level_1'
                WHEN level = 2 THEN 'level_2'
                WHEN level = 3 THEN 'level_3'
                WHEN level = 4 THEN 'level_4'
                WHEN level = 5 THEN 'level_5'
                ELSE 'test'
            END,
            usdt_confirmed = CASE WHEN status = 'confirmed' THEN true ELSE false END,
            plex_daily_required = amount * 10
    """)

def downgrade() -> None:
    op.drop_index('ix_deposits_usdt_confirmed', 'deposits')
    op.drop_index('ix_deposits_deposit_type', 'deposits')
    op.drop_column('deposits', 'plex_daily_required')
    op.drop_column('deposits', 'usdt_confirmed_at')
    op.drop_column('deposits', 'usdt_confirmed')
    op.drop_column('deposits', 'max_amount')
    op.drop_column('deposits', 'min_amount')
    op.drop_column('deposits', 'deposit_type')

    op.drop_index('ix_deposit_level_configs_is_active', 'deposit_level_configs')
    op.drop_index('ix_deposit_level_configs_order', 'deposit_level_configs')
    op.drop_index('ix_deposit_level_configs_level_type', 'deposit_level_configs')
    op.drop_table('deposit_level_configs')
