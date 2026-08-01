CREATE TABLE IF NOT EXISTS schedules (
    id             BIGINT PRIMARY KEY,
    movie_id       BIGINT NOT NULL REFERENCES movies(id),
    cinema_id      BIGINT NOT NULL REFERENCES cinemas(id),
    start_date     DATE NOT NULL,
    start_time     TIME NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (movie_id, cinema_id, start_date, start_time)
);

CREATE INDEX IF NOT EXISTS idx_schedules_cinema_time
ON schedules(cinema_id, start_date, start_time);