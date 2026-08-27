package handler

import (
	"context"
	"net/http"
	"strconv"
	"strings"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

// ReviewHandler handles HTTP endpoints for movie reviews and ratings.
type ReviewHandler struct {
	ReviewRepo *repo.ReviewRepo
	MovieRepo  *repo.MovieRepo
}

// NewReviewHandler creates a new ReviewHandler.
func NewReviewHandler(reviewRepo *repo.ReviewRepo, movieRepo *repo.MovieRepo) *ReviewHandler {
	return &ReviewHandler{
		ReviewRepo: reviewRepo,
		MovieRepo:  movieRepo,
	}
}

// ListMovieReviews handles GET /api/movies/:id/reviews?page=1&limit=5&rating=5&sort=newest
func (h *ReviewHandler) ListMovieReviews(ctx context.Context, c *app.RequestContext) {
	idStr := c.Param("id")
	movieID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid movie id"})
		return
	}

	page := 1
	if pStr := c.Query("page"); pStr != "" {
		if p, err := strconv.Atoi(pStr); err == nil && p > 0 {
			page = p
		}
	}

	limit := 5
	if lStr := c.Query("limit"); lStr != "" {
		if l, err := strconv.Atoi(lStr); err == nil && l > 0 {
			limit = l
		}
	}

	ratingFilter := 0
	if rStr := c.Query("rating"); rStr != "" {
		if r, err := strconv.Atoi(rStr); err == nil && r >= 1 && r <= 5 {
			ratingFilter = r
		}
	}

	sortBy := strings.TrimSpace(c.Query("sort"))
	if sortBy == "" {
		sortBy = "newest"
	}

	reviews, total, totalPages, avgRating, ratingCounts, err := h.ReviewRepo.ListReviewsByMovieID(ctx, movieID, page, limit, ratingFilter, sortBy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.MovieReviewsResponse{
		Reviews:       reviews,
		Total:         total,
		Page:          page,
		Limit:         limit,
		TotalPages:    totalPages,
		AverageRating: avgRating,
		RatingCounts:  ratingCounts,
	})
}

// CreateMovieReview handles POST /api/movies/:id/reviews (authenticated)
func (h *ReviewHandler) CreateMovieReview(ctx context.Context, c *app.RequestContext) {
	userIDVal, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID, ok := userIDVal.(int64)
	if !ok {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": "invalid user session"})
		return
	}

	idStr := c.Param("id")
	movieID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid movie id"})
		return
	}

	var req model.CreateReviewRequest
	if err := c.BindAndValidate(&req); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid review payload"})
		return
	}

	if req.Rating < 1 || req.Rating > 5 {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "rating must be between 1 and 5 stars"})
		return
	}

	trimmedContent := strings.TrimSpace(req.Content)
	if trimmedContent == "" {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "review content cannot be empty"})
		return
	}

	if len(trimmedContent) > 2000 {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "review content must not exceed 2000 characters"})
		return
	}

	rev, err := h.ReviewRepo.CreateOrUpdateReview(ctx, movieID, userID, req.Rating, trimmedContent)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, rev)
}

// DeleteMovieReview handles DELETE /api/movies/:id/reviews/:review_id (authenticated)
func (h *ReviewHandler) DeleteMovieReview(ctx context.Context, c *app.RequestContext) {
	userIDVal, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID, ok := userIDVal.(int64)
	if !ok {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": "invalid user session"})
		return
	}

	reviewIDStr := c.Param("review_id")
	reviewID, err := strconv.ParseInt(reviewIDStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid review id"})
		return
	}

	err = h.ReviewRepo.DeleteReview(ctx, reviewID, userID)
	if err != nil {
		if err == repo.ErrReviewNotFound {
			c.JSON(http.StatusNotFound, map[string]string{"error": "review not found or unauthorized"})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, map[string]string{"message": "review deleted successfully"})
}
