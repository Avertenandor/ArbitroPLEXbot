-- Create user_activities table
CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT,
    message_text TEXT,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_user_activities_telegram_id ON user_activities(telegram_id);
CREATE INDEX IF NOT EXISTS ix_user_activities_activity_type ON user_activities(activity_type);
CREATE INDEX IF NOT EXISTS ix_user_activities_created_at ON user_activities(created_at);

-- Mark migration as applied
INSERT INTO alembic_version (version_num) VALUES ('20251208_000002')
ON CONFLICT DO NOTHING;
