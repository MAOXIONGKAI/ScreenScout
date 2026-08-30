package handler

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

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

// TriggerScrape handles POST /api/admin/scrape
// Triggers a full scrape of cinema locations, movies, and screening schedules across providers.
func (h *AdminHandler) TriggerScrape(ctx context.Context, c *app.RequestContext) {
	startTime := time.Now()

	pythonBin, rootDir := findPythonAndProjectRoot()

	// 1. Scrape Cinema Locations
	cinemasScript := filepath.Join(rootDir, "movie_scraping", "cinemas", "main.py")
	cmdCinemas := exec.CommandContext(ctx, pythonBin, cinemasScript, "--provider", "all")
	cmdCinemas.Dir = rootDir
	cmdCinemas.Env = os.Environ()
	outCinemas, err := cmdCinemas.CombinedOutput()
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]interface{}{
			"error":   fmt.Sprintf("cinema scraper failed: %v", err),
			"details": string(outCinemas),
		})
		return
	}

	// 2. Scrape Movies & Schedules
	moviesScript := filepath.Join(rootDir, "movie_scraping", "movies_and_schedules", "main.py")
	cmdMovies := exec.CommandContext(ctx, pythonBin, moviesScript, "--provider", "all")
	cmdMovies.Dir = rootDir
	cmdMovies.Env = os.Environ()
	outMovies, err := cmdMovies.CombinedOutput()
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]interface{}{
			"error":   fmt.Sprintf("movie scraper failed: %v", err),
			"details": string(outMovies),
		})
		return
	}

	// 3. Purge Movie Cache
	var flushedCount int64
	if h.Repo.Cache != nil {
		flushedCount, _ = h.Repo.Cache.InvalidateAllMovies(ctx)
	}

	duration := time.Since(startTime)

	c.JSON(http.StatusOK, map[string]interface{}{
		"success":            true,
		"message":            "Full fetch of cinemas, movies, and showtimes completed successfully.",
		"duration_ms":        duration.Milliseconds(),
		"flushed_keys_count": flushedCount,
	})
}

func findPythonAndProjectRoot() (string, string) {
	if envRoot := os.Getenv("PROJECT_ROOT"); envRoot != "" {
		if envPy := os.Getenv("PYTHON_BIN"); envPy != "" {
			return envPy, envRoot
		}
		venvPy := filepath.Join(envRoot, "venv", "bin", "python")
		if _, err := os.Stat(venvPy); err == nil {
			return venvPy, envRoot
		}
		return "python3", envRoot
	}

	candidates := []string{
		".",
		"..",
		"../..",
	}

	for _, dir := range candidates {
		checkPath := filepath.Join(dir, "movie_scraping", "cinemas", "main.py")
		if _, err := os.Stat(checkPath); err == nil {
			absDir, _ := filepath.Abs(dir)
			if envPy := os.Getenv("PYTHON_BIN"); envPy != "" {
				return envPy, absDir
			}
			venvPy := filepath.Join(absDir, "venv", "bin", "python")
			if _, vErr := os.Stat(venvPy); vErr == nil {
				return venvPy, absDir
			}
			return "python3", absDir
		}
	}

	// Fallback to absolute workspace directory if known
	fallbackDir := "/Users/maoxiongkai/Documents/GitHub/ScreenScout"
	venvPy := filepath.Join(fallbackDir, "venv", "bin", "python")
	if _, err := os.Stat(venvPy); err == nil {
		return venvPy, fallbackDir
	}

	return "python3", "."
}

