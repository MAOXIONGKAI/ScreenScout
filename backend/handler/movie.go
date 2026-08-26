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
		Page:     page,
		Limit:    limit,
	}

	movies, total, err := h.Repo.ListMovies(ctx, filters)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
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

	detail, err := h.Repo.GetMovieByID(ctx, id)
	if err != nil {
		c.JSON(http.StatusNotFound, map[string]string{"error": "movie not found"})
		return
	}

	c.JSON(http.StatusOK, detail)
}
