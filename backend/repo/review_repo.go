package repo

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/model"
)

var (
	ErrReviewNotFound = errors.New("review not found or unauthorized")
	ErrInvalidRating  = errors.New("rating must be between 1 and 5 stars")
	ErrEmptyContent   = errors.New("review content cannot be empty")
)

// ReviewRepo manages database persistence for movie reviews and ratings.
type ReviewRepo struct {
	Pool *pgxpool.Pool
}

// NewReviewRepo creates a new ReviewRepo.
func NewReviewRepo(pool *pgxpool.Pool) *ReviewRepo {
	return &ReviewRepo{Pool: pool}
}

// EnsureReviewTable creates the reviews table, sequence, and indexes if they do not already exist.
func (r *ReviewRepo) EnsureReviewTable(ctx context.Context) error {
	query := `
	CREATE TABLE IF NOT EXISTS reviews (
		id          BIGINT PRIMARY KEY,
		movie_id    BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
		user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
		rating      INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
		content     TEXT NOT NULL,
		created_at  TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
		updated_at  TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
		UNIQUE (movie_id, user_id)
	);

	CREATE SEQUENCE IF NOT EXISTS reviews_id_seq START WITH 1 INCREMENT BY 1;
	ALTER TABLE reviews ALTER COLUMN id SET DEFAULT nextval('reviews_id_seq');

	CREATE INDEX IF NOT EXISTS idx_reviews_movie_created ON reviews(movie_id, created_at DESC);
	CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id);
	`
	_, err := r.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("ensure reviews table: %w", err)
	}
	return nil
}

// ListReviewsByMovieID returns paginated reviews for a movie along with summary metrics (average rating, counts, total pages).
func (r *ReviewRepo) ListReviewsByMovieID(ctx context.Context, movieID int64, page, limit int) ([]model.Review, int, int, float64, map[string]int, error) {
	if page < 1 {
		page = 1
	}
	if limit < 1 {
		limit = 5
	}
	if limit > 50 {
		limit = 50
	}

	// 1. Fetch aggregate metrics across ALL reviews for this movie
	aggQuery := `
	SELECT rating, COUNT(*)
	FROM reviews
	WHERE movie_id = $1
	GROUP BY rating
	`
	rows, err := r.Pool.Query(ctx, aggQuery, movieID)
	if err != nil {
		return nil, 0, 0, 0, nil, fmt.Errorf("query review stats: %w", err)
	}
	defer rows.Close()

	ratingCounts := map[string]int{
		"1": 0,
		"2": 0,
		"3": 0,
		"4": 0,
		"5": 0,
	}
	var total int
	var totalRatingSum int

	for rows.Next() {
		var starRating, count int
		if err := rows.Scan(&starRating, &count); err != nil {
			return nil, 0, 0, 0, nil, fmt.Errorf("scan review stats: %w", err)
		}
		key := fmt.Sprintf("%d", starRating)
		ratingCounts[key] = count
		total += count
		totalRatingSum += starRating * count
	}

	var avgRating float64
	if total > 0 {
		avgRating = math.Round((float64(totalRatingSum)/float64(total))*10) / 10
	}

	totalPages := 0
	if total > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(limit)))
	}

	// 2. Fetch paginated review items
	offset := (page - 1) * limit
	query := `
	SELECT r.id, r.movie_id, r.user_id, u.username, r.rating, r.content, r.created_at, r.updated_at
	FROM reviews r
	JOIN users u ON u.id = r.user_id
	WHERE r.movie_id = $1
	ORDER BY r.created_at DESC
	LIMIT $2 OFFSET $3
	`

	pRows, err := r.Pool.Query(ctx, query, movieID, limit, offset)
	if err != nil {
		return nil, 0, 0, 0, nil, fmt.Errorf("query paginated reviews: %w", err)
	}
	defer pRows.Close()

	var reviews []model.Review
	for pRows.Next() {
		var rev model.Review
		if err := pRows.Scan(
			&rev.ID,
			&rev.MovieID,
			&rev.UserID,
			&rev.Username,
			&rev.Rating,
			&rev.Content,
			&rev.CreatedAt,
			&rev.UpdatedAt,
		); err != nil {
			return nil, 0, 0, 0, nil, fmt.Errorf("scan review item: %w", err)
		}
		reviews = append(reviews, rev)
	}

	if reviews == nil {
		reviews = []model.Review{}
	}

	return reviews, total, totalPages, avgRating, ratingCounts, nil
}

// CreateOrUpdateReview inserts or updates a user's review for a given movie.
func (r *ReviewRepo) CreateOrUpdateReview(ctx context.Context, movieID, userID int64, rating int, content string) (*model.Review, error) {
	if rating < 1 || rating > 5 {
		return nil, ErrInvalidRating
	}

	trimmedContent := strings.TrimSpace(content)
	if trimmedContent == "" {
		return nil, ErrEmptyContent
	}

	query := `
	INSERT INTO reviews (movie_id, user_id, rating, content, created_at, updated_at)
	VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
	ON CONFLICT (movie_id, user_id)
	DO UPDATE SET 
		rating = EXCLUDED.rating,
		content = EXCLUDED.content,
		updated_at = CURRENT_TIMESTAMP
	RETURNING id, movie_id, user_id, rating, content, created_at, updated_at
	`

	var rev model.Review
	err := r.Pool.QueryRow(ctx, query, movieID, userID, rating, trimmedContent).Scan(
		&rev.ID,
		&rev.MovieID,
		&rev.UserID,
		&rev.Rating,
		&rev.Content,
		&rev.CreatedAt,
		&rev.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("upsert review: %w", err)
	}

	// Fetch username for response
	var username string
	userErr := r.Pool.QueryRow(ctx, `SELECT username FROM users WHERE id = $1`, userID).Scan(&username)
	if userErr == nil {
		rev.Username = username
	}

	return &rev, nil
}

// DeleteReview deletes a review by ID if it belongs to the authenticated user.
func (r *ReviewRepo) DeleteReview(ctx context.Context, reviewID, userID int64) error {
	cmd, err := r.Pool.Exec(ctx, `DELETE FROM reviews WHERE id = $1 AND user_id = $2`, reviewID, userID)
	if err != nil {
		return fmt.Errorf("delete review: %w", err)
	}

	if cmd.RowsAffected() == 0 {
		return ErrReviewNotFound
	}

	return nil
}

// GetUserReview retrieves a specific user's review for a movie (if any).
func (r *ReviewRepo) GetUserReview(ctx context.Context, movieID, userID int64) (*model.Review, error) {
	query := `
	SELECT r.id, r.movie_id, r.user_id, u.username, r.rating, r.content, r.created_at, r.updated_at
	FROM reviews r
	JOIN users u ON u.id = r.user_id
	WHERE r.movie_id = $1 AND r.user_id = $2
	`

	var rev model.Review
	err := r.Pool.QueryRow(ctx, query, movieID, userID).Scan(
		&rev.ID,
		&rev.MovieID,
		&rev.UserID,
		&rev.Username,
		&rev.Rating,
		&rev.Content,
		&rev.CreatedAt,
		&rev.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("get user review: %w", err)
	}

	return &rev, nil
}
