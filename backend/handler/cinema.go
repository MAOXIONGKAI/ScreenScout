package handler

import (
	"context"
	"net/http"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

// CinemaHandler handles cinema-related HTTP requests.
type CinemaHandler struct {
	Repo *repo.CinemaRepo
}

// NewCinemaHandler creates a new CinemaHandler.
func NewCinemaHandler(r *repo.CinemaRepo) *CinemaHandler {
	return &CinemaHandler{Repo: r}
}

// ListCinemas handles GET /api/cinemas with optional provider query param.
func (h *CinemaHandler) ListCinemas(ctx context.Context, c *app.RequestContext) {
	provider := string(c.Query("provider"))

	cinemas, err := h.Repo.ListCinemas(ctx, provider)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	if cinemas == nil {
		cinemas = []model.Cinema{}
	}

	c.JSON(http.StatusOK, cinemas)
}

// ListProviders handles GET /api/providers.
func (h *CinemaHandler) ListProviders(ctx context.Context, c *app.RequestContext) {
	providers, err := h.Repo.ListProviders(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	if providers == nil {
		providers = []string{}
	}

	c.JSON(http.StatusOK, providers)
}
