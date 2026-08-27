package repo

import (
	"context"
	"testing"
)

func TestReviewRepo_Validation(t *testing.T) {
	repo := NewReviewRepo(nil)
	ctx := context.Background()

	// Rating < 1
	_, err := repo.CreateOrUpdateReview(ctx, 1, 1, 0, "Good movie")
	if err != ErrInvalidRating {
		t.Errorf("expected ErrInvalidRating for 0, got %v", err)
	}

	// Rating > 5
	_, err = repo.CreateOrUpdateReview(ctx, 1, 1, 6, "Good movie")
	if err != ErrInvalidRating {
		t.Errorf("expected ErrInvalidRating for 6, got %v", err)
	}

	// Empty content
	_, err = repo.CreateOrUpdateReview(ctx, 1, 1, 5, "   ")
	if err != ErrEmptyContent {
		t.Errorf("expected ErrEmptyContent, got %v", err)
	}
}
