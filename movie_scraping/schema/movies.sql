CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS movies (
    id                    BIGINT PRIMARY KEY,
    
    title                 VARCHAR(255) NOT NULL,
    secondary_title       VARCHAR(255) NULL,
    
    description           TEXT,
    embedding             vector(1536),
    
    poster_url            TEXT,
    trailer_url           TEXT,
    website_url           TEXT,
    
    director              VARCHAR(255),
    casts                 TEXT,
    genre                 TEXT,
    
    provider              VARCHAR(20) NOT NULL
        CHECK (
            provider IN ('GV', 'SHAW')
        ),
    provider_movie_id     BIGINT NOT NULL,
    
    release_date          DATE NOT NULL,
    duration              INT NOT NULL,
    
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (provider, provider_movie_id)
);

-- Exact release date lookup / sorting / range search
CREATE INDEX IF NOT EXISTS idx_movies_release_date
ON movies(release_date);

-- Fuzzy title search
CREATE INDEX IF NOT EXISTS idx_movies_title_trgm
ON movies
USING gin(title gin_trgm_ops);

-- Vector similarity search
CREATE INDEX IF NOT EXISTS idx_movies_embedding
ON movies
USING hnsw (embedding vector_cosine_ops);
