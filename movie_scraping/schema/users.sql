CREATE TABLE IF NOT EXISTS users (
    id                  BIGINT PRIMARY KEY,
    username            VARCHAR(55) NOT NULL UNIQUE,
    hashed_password     TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
);

CREATE SEQUENCE IF NOT EXISTS users_id_seq START WITH 1 INCREMENT BY 1;
ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

