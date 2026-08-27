package handler

import (
	"context"
	"net/http"
	"strconv"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

// MovieHandler handles movie-related HTTP requests.
type MovieHandler struct {
	Repo *repo.MovieRepo
}

// NewMovieHandler creates a new MovieHandler.
func NewMovieHandler(r *repo.MovieRepo) *MovieHandler {
	return &MovieHandler{Repo: r}
}

// ListMovies handles GET /api/movies with optional query params:
// provider, branch, status, search, page, limit
func (h *MovieHandler) ListMovies(ctx context.Context, c *app.RequestContext) {
	provider := string(c.Query("provider"))
	branch := string(c.Query("branch"))
	status := string(c.Query("status"))
	search := string(c.Query("search"))
	timeFrom := string(c.Query("time_from"))
	timeTo := string(c.Query("time_to"))

	page, _ := strconv.Atoi(string(c.Query("page")))
	limit, _ := strconv.Atoi(string(c.Query("limit")))

	if page < 1 {
		page = 1
	}
	if limit < 1 {
		limit = 20
	}

	filters := repo.MovieFilters{
		Provider: provider,
		Branch:   branch,
		Status:   status,
		Search:   search,
		TimeFrom: timeFrom,
		TimeTo:   timeTo,
		Page:     page,
		Limit:    limit,
	}

	// Capture initial hits count to determine HIT vs MISS for header
	var initialHits int64
	cache := h.Repo.GetCache()
	if cache != nil {
		initialHits = cache.Stats().Hits
	}

	movies, total, err := h.Repo.ListMovies(ctx, filters)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	if cache != nil && cache.Client().IsAvailable() {
		if cache.Stats().Hits > initialHits {
			c.Header("X-Cache", "HIT")
		} else {
			c.Header("X-Cache", "MISS")
		}
	} else {
		c.Header("X-Cache", "BYPASS")
	}

	if movies == nil {
		movies = []model.Movie{}
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"movies": movies,
		"total":  total,
		"page":   page,
		"limit":  limit,
	})
}

// GetMovie handles GET /api/movies/:id
func (h *MovieHandler) GetMovie(ctx context.Context, c *app.RequestContext) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid movie id"})
		return
	}

	var initialHits int64
	cache := h.Repo.GetCache()
	if cache != nil {
		initialHits = cache.Stats().Hits
	}

	detail, err := h.Repo.GetMovieByID(ctx, id)
	if err != nil {
		c.JSON(http.StatusNotFound, map[string]string{"error": "movie not found"})
		return
	}

	if cache != nil && cache.Client().IsAvailable() {
		if cache.Stats().Hits > initialHits {
			c.Header("X-Cache", "HIT")
		} else {
			c.Header("X-Cache", "MISS")
		}
	} else {
		c.Header("X-Cache", "BYPASS")
	}

	c.JSON(http.StatusOK, detail)
}

// GetCacheStats handles GET /api/cache/stats
func (h *MovieHandler) GetCacheStats(ctx context.Context, c *app.RequestContext) {
	cache := h.Repo.GetCache()
	if cache == nil {
		c.JSON(http.StatusOK, map[string]interface{}{
			"status":    "disabled",
			"connected": false,
		})
		return
	}

	stats := cache.Stats()
	c.JSON(http.StatusOK, map[string]interface{}{
		"status": "enabled",
		"stats":  stats,
	})
}

// InvalidateCache handles POST /api/cache/movies/invalidate
// Optional query parameter: ?movie_id=123 (invalidates specific movie, otherwise invalidates all)
func (h *MovieHandler) InvalidateCache(ctx context.Context, c *app.RequestContext) {
	cache := h.Repo.GetCache()
	if cache == nil {
		c.JSON(http.StatusOK, map[string]interface{}{
			"message": "cache is not configured",
		})
		return
	}

	movieIDStr := string(c.Query("movie_id"))
	if movieIDStr != "" {
		id, err := strconv.ParseInt(movieIDStr, 10, 64)
		if err != nil {
			c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid movie_id"})
			return
		}

		if err := h.Repo.InvalidateMovie(ctx, id); err != nil {
			c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, map[string]interface{}{
			"message":  "movie cache invalidated",
			"movie_id": id,
		})
		return
	}

	deleted, err := h.Repo.InvalidateAllMovies(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"message":      "all movie caches invalidated",
		"keys_deleted": deleted,
	})
}
