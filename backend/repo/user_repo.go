package repo

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/model"
)

var (
	ErrUserNotFound      = errors.New("user not found")
	ErrUsernameDuplicate = errors.New("username already taken")
)

// UserRepo handles user database operations.
type UserRepo struct {
	Pool *pgxpool.Pool
}

// NewUserRepo creates a new UserRepo.
func NewUserRepo(pool *pgxpool.Pool) *UserRepo {
	return &UserRepo{Pool: pool}
}

// EnsureUserTable creates the users table and sequence if they do not already exist.
func (r *UserRepo) EnsureUserTable(ctx context.Context) error {
	query := `
	CREATE TABLE IF NOT EXISTS users (
		id                  BIGINT PRIMARY KEY,
		username            VARCHAR(55) NOT NULL UNIQUE,
		hashed_password     TEXT NOT NULL,
		created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
		updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
	);

	CREATE SEQUENCE IF NOT EXISTS users_id_seq START WITH 1 INCREMENT BY 1;
	ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');

	-- Migrate existing columns from TIMESTAMP to TIMESTAMPTZ if needed
	DO $$ 
	BEGIN
		IF EXISTS (
			SELECT 1 FROM information_schema.columns 
			WHERE table_name = 'users' AND column_name = 'created_at' AND data_type = 'timestamp without time zone'
		) THEN
			ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
			ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
		END IF;
	EXCEPTION
		WHEN OTHERS THEN NULL;
	END $$;

	-- Set column defaults
	ALTER TABLE users ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
	ALTER TABLE users ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;

	CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
	`
	_, err := r.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("ensure users table: %w", err)
	}
	return nil
}

// CreateUser inserts a new user record.
func (r *UserRepo) CreateUser(ctx context.Context, username, hashedPassword string) (*model.User, error) {
	query := `
		INSERT INTO users (username, hashed_password)
		VALUES ($1, $2)
		RETURNING id, username, hashed_password, created_at, updated_at
	`

	var user model.User
	err := r.Pool.QueryRow(ctx, query, strings.TrimSpace(username), hashedPassword).Scan(
		&user.ID,
		&user.Username,
		&user.HashedPassword,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" { // Unique violation
			return nil, ErrUsernameDuplicate
		}
		return nil, fmt.Errorf("create user: %w", err)
	}

	return &user, nil
}

// GetUserByUsername retrieves a user by username (case-insensitive search).
func (r *UserRepo) GetUserByUsername(ctx context.Context, username string) (*model.User, error) {
	query := `
		SELECT id, username, hashed_password, created_at, updated_at
		FROM users
		WHERE LOWER(username) = LOWER($1)
		LIMIT 1
	`

	var user model.User
	err := r.Pool.QueryRow(ctx, query, strings.TrimSpace(username)).Scan(
		&user.ID,
		&user.Username,
		&user.HashedPassword,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrUserNotFound
		}
		return nil, fmt.Errorf("get user by username: %w", err)
	}

	return &user, nil
}

// GetUserByID retrieves a user by ID.
func (r *UserRepo) GetUserByID(ctx context.Context, id int64) (*model.User, error) {
	query := `
		SELECT id, username, hashed_password, created_at, updated_at
		FROM users
		WHERE id = $1
		LIMIT 1
	`

	var user model.User
	err := r.Pool.QueryRow(ctx, query, id).Scan(
		&user.ID,
		&user.Username,
		&user.HashedPassword,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrUserNotFound
		}
		return nil, fmt.Errorf("get user by id: %w", err)
	}

	return &user, nil
}
