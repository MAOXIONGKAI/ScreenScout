package model

import "time"

// Review represents a user review and rating for a movie.
type Review struct {
	ID        int64     `json:"id"`
	MovieID   int64     `json:"movie_id"`
	UserID    int64     `json:"user_id"`
	Username  string    `json:"username"`
	Rating    int       `json:"rating"` // 1 - 5
	Content   string    `json:"content"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// CreateReviewRequest is the payload sent to create or update a movie review.
type CreateReviewRequest struct {
	Rating  int    `json:"rating"`
	Content string `json:"content"`
}

// MovieReviewsResponse wraps the paginated list of reviews, aggregate stats, and rating distribution for a movie.
type MovieReviewsResponse struct {
	Reviews       []Review       `json:"reviews"`
	Total         int            `json:"total"`
	Page          int            `json:"page"`
	Limit         int            `json:"limit"`
	TotalPages    int            `json:"total_pages"`
	AverageRating float64        `json:"average_rating"`
	RatingCounts  map[string]int `json:"rating_counts"`
}
