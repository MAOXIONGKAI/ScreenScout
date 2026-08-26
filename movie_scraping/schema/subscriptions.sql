-- Section 20 Database Design: Notification Channels & Subscriptions

CREATE TABLE IF NOT EXISTS notification_channels (
    id                  BIGINT PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type        VARCHAR(20) NOT NULL CHECK (
                            channel_type IN ('TELEGRAM', 'WECHAT', 'WHATSAPP', 'EMAIL', 'DISCORD')
                        ),
    channel_user_id     VARCHAR(255) NOT NULL,
    is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
    UNIQUE (user_id, channel_type)
);

CREATE SEQUENCE IF NOT EXISTS notification_channels_id_seq START WITH 1 INCREMENT BY 1;
ALTER TABLE notification_channels ALTER COLUMN id SET DEFAULT nextval('notification_channels_id_seq');

CREATE INDEX IF NOT EXISTS idx_notification_channels_user ON notification_channels(user_id);


CREATE TABLE IF NOT EXISTS subscriptions (
    id                  BIGINT PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_query         VARCHAR(255) NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    matched_movie_id    BIGINT REFERENCES movies(id) ON DELETE SET NULL,
    matched_movie_title VARCHAR(255),
    matched_movies      JSONB DEFAULT '[]'::jsonb,
    triggered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
);

CREATE SEQUENCE IF NOT EXISTS subscriptions_id_seq START WITH 1 INCREMENT BY 1;
ALTER TABLE subscriptions ALTER COLUMN id SET DEFAULT nextval('subscriptions_id_seq');

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);


CREATE TABLE IF NOT EXISTS notification_logs (
    id                  BIGINT PRIMARY KEY,
    subscription_id     BIGINT REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type        VARCHAR(20) NOT NULL,
    recipient           VARCHAR(255) NOT NULL,
    message             TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'SENT',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
);

CREATE SEQUENCE IF NOT EXISTS notification_logs_id_seq START WITH 1 INCREMENT BY 1;
ALTER TABLE notification_logs ALTER COLUMN id SET DEFAULT nextval('notification_logs_id_seq');

CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON notification_logs(user_id);
