package cache

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/maoxiongkai/screenscout-backend/model"
)

const (
	// DefaultListTTL is the default cache expiration for movie listings (5 minutes).
	DefaultListTTL = 5 * time.Minute
	// DefaultDetailTTL is the default cache expiration for movie details and schedules (10 minutes).
	DefaultDetailTTL = 10 * time.Minute

	// Key prefixes
	keyPrefixMovieDetail = "screenscout:movie:detail:"
	keyPrefixMovieList   = "screenscout:movie:list:"
	keyPatternAllMovies  = "screenscout:movie:*"
	keyPatternAllLists   = "screenscout:movie:list:*"
)

// MovieListFilters abstracts the query parameters used for caching movie listings.
type MovieListFilters struct {
	Provider string
	Branch   string
	Status   string
	Search   string
	TimeFrom string
	TimeTo   string
	Page     int
	Limit    int
}

// CachedMovieList represents the payload stored for a movie list query.
type CachedMovieList struct {
	Movies []model.Movie `json:"movies"`
	Total  int           `json:"total"`
}

// MovieCache provides caching operations for movie listings and details.
type MovieCache struct {
	client    *Client
	listTTL   time.Duration
	detailTTL time.Duration
}

// NewMovieCache creates a new MovieCache.
func NewMovieCache(client *Client, listTTL, detailTTL time.Duration) *MovieCache {
	if listTTL <= 0 {
		listTTL = DefaultListTTL
	}
	if detailTTL <= 0 {
		detailTTL = DefaultDetailTTL
	}
	return &MovieCache{
		client:    client,
		listTTL:   listTTL,
		detailTTL: detailTTL,
	}
}

// Client returns the underlying Redis client wrapper.
func (c *MovieCache) Client() *Client {
	return c.client
}

// BuildDetailKey constructs the Redis key for a single movie's detail.
func (c *MovieCache) BuildDetailKey(id int64) string {
	return fmt.Sprintf("%s%d", keyPrefixMovieDetail, id)
}

// BuildListKey constructs the Redis key for a movie list query based on filters.
func (c *MovieCache) BuildListKey(f MovieListFilters) string {
	// Normalize parameters
	prov := strings.ToUpper(strings.TrimSpace(f.Provider))
	branch := strings.ToLower(strings.TrimSpace(f.Branch))
	status := strings.ToLower(strings.TrimSpace(f.Status))
	search := strings.ToLower(strings.TrimSpace(f.Search))
	timeFrom := strings.TrimSpace(f.TimeFrom)
	timeTo := strings.TrimSpace(f.TimeTo)
	page := f.Page
	if page < 1 {
		page = 1
	}
	limit := f.Limit
	if limit < 1 {
		limit = 20
	}

	raw := fmt.Sprintf("prov=%s|br=%s|st=%s|q=%s|tf=%s|tt=%s|p=%d|l=%d",
		prov, branch, status, search, timeFrom, timeTo, page, limit)

	// Generate deterministic short hash to keep keys compact and safe
	hasher := sha256.New()
	hasher.Write([]byte(raw))
	hash := hex.EncodeToString(hasher.Sum(nil))[:16]

	return fmt.Sprintf("%s%s:%s", keyPrefixMovieList, raw[:min(len(raw), 40)], hash)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// GetMovieDetail retrieves a cached movie detail by ID.
// Returns (detail, found, error). If not found, found is false and err is nil.
func (c *MovieCache) GetMovieDetail(ctx context.Context, id int64) (*model.MovieDetail, bool, error) {
	if c == nil || c.client == nil || !c.client.IsAvailable() {
		return nil, false, nil
	}

	key := c.BuildDetailKey(id)
	val, err := c.client.Get(ctx, key)
	if err != nil {
		if errors.Is(err, ErrCacheMiss) {
			return nil, false, nil
		}
		return nil, false, err
	}

	var detail model.MovieDetail
	if err := json.Unmarshal([]byte(val), &detail); err != nil {
		// Stale/corrupt cache payload, delete and report miss
		_ = c.client.Del(ctx, key)
		return nil, false, nil
	}

	return &detail, true, nil
}

// SetMovieDetail caches a movie detail with schedules.
func (c *MovieCache) SetMovieDetail(ctx context.Context, id int64, detail *model.MovieDetail) error {
	if c == nil || c.client == nil || !c.client.IsAvailable() || detail == nil {
		return nil
	}

	key := c.BuildDetailKey(id)
	payload, err := json.Marshal(detail)
	if err != nil {
		return fmt.Errorf("marshal movie detail: %w", err)
	}

	return c.client.Set(ctx, key, payload, c.detailTTL)
}

// GetMovieList retrieves cached movie listing results.
// Returns (movies, total, found, error).
func (c *MovieCache) GetMovieList(ctx context.Context, f MovieListFilters) ([]model.Movie, int, bool, error) {
	if c == nil || c.client == nil || !c.client.IsAvailable() {
		return nil, 0, false, nil
	}

	key := c.BuildListKey(f)
	val, err := c.client.Get(ctx, key)
	if err != nil {
		if errors.Is(err, ErrCacheMiss) {
			return nil, 0, false, nil
		}
		return nil, 0, false, err
	}

	var cached CachedMovieList
	if err := json.Unmarshal([]byte(val), &cached); err != nil {
		_ = c.client.Del(ctx, key)
		return nil, 0, false, nil
	}

	return cached.Movies, cached.Total, true, nil
}

// SetMovieList caches a movie list result.
func (c *MovieCache) SetMovieList(ctx context.Context, f MovieListFilters, movies []model.Movie, total int) error {
	if c == nil || c.client == nil || !c.client.IsAvailable() {
		return nil
	}

	key := c.BuildListKey(f)
	cached := CachedMovieList{
		Movies: movies,
		Total:  total,
	}

	payload, err := json.Marshal(cached)
	if err != nil {
		return fmt.Errorf("marshal movie list: %w", err)
	}

	return c.client.Set(ctx, key, payload, c.listTTL)
}

// InvalidateMovie purges the cache for a specific movie ID and purges all listing caches.
func (c *MovieCache) InvalidateMovie(ctx context.Context, id int64) error {
	if c == nil || c.client == nil || !c.client.IsAvailable() {
		return nil
	}

	// Delete detail key
	detailKey := c.BuildDetailKey(id)
	_ = c.client.Del(ctx, detailKey)

	// Purge all movie list queries as list contents or showtimes changed
	_, err := c.client.FlushPrefix(ctx, keyPatternAllLists)
	return err
}

// InvalidateAllMovies purges all movie-related cache entries (details and lists).
func (c *MovieCache) InvalidateAllMovies(ctx context.Context) (int64, error) {
	if c == nil || c.client == nil || !c.client.IsAvailable() {
		return 0, nil
	}
	return c.client.FlushPrefix(ctx, keyPatternAllMovies)
}

// Stats returns the underlying Redis client statistics.
func (c *MovieCache) Stats() Stats {
	if c == nil || c.client == nil {
		return Stats{Connected: false}
	}
	return c.client.Stats()
}
