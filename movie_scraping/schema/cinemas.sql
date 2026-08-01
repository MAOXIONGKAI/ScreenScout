CREATE TABLE IF NOT EXISTS cinemas (
    id           BIGINT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    branch       VARCHAR(100) NOT NULL,
    postal_code  CHAR(6) NOT NULL,
    address      TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, branch)
);