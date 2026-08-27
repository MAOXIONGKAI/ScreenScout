package handler

import (
	"context"
	"net/http"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

// AdminHandler handles HTTP requests for admin operations and telemetry.
type AdminHandler struct {
	Repo *repo.AdminRepo
}

// NewAdminHandler creates a new AdminHandler.
func NewAdminHandler(r *repo.AdminRepo) *AdminHandler {
	return &AdminHandler{Repo: r}
}

// GetAdminStats handles GET /api/admin/stats
func (h *AdminHandler) GetAdminStats(ctx context.Context, c *app.RequestContext) {
	stats, err := h.Repo.GetAdminStats(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to retrieve system metrics: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, stats)
}
