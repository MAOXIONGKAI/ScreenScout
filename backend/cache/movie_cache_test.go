package cache

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/redis/go-redis/v9"
)

func setupTestRedis(t *testing.T) (*miniredis.Miniredis, *MovieCache) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}

	rdb := redis.NewClient(&redis.Options{
		Addr: mr.Addr(),
	})

	client := NewFromUniversalClient(rdb)
	movieCache := NewMovieCache(client, 5*time.Minute, 10*time.Minute)

	return mr, movieCache
}

func TestMovieCache_Detail(t *testing.T) {
	mr, cache := setupTestRedis(t)
	defer mr.Close()

	ctx := context.Background()

	// 1. Initial lookup -> Cache miss
	detail, found, err := cache.GetMovieDetail(ctx, 42)
	if err != nil {
		t.Fatalf("unexpected error on get: %v", err)
	}
	if found || detail != nil {
		t.Fatalf("expected cache miss, got found=%v, detail=%v", found, detail)
	}

	// 2. Set detail
	origDetail := &model.MovieDetail{
		Movie: model.Movie{
			ID:          42,
			Title:       "Dune: Part Two",
			Provider:    "GV",
			Status:      "now_showing",
			ReleaseDate: "2024-03-01",
			Duration:    166,
		},
		Schedules: []model.CinemaSchedule{
			{
				CinemaID:   1,
				CinemaName: "Golden Village",
				Branch:     "Plaza Singapura",
				Dates: []model.DateSchedule{
					{
						Date: "2024-03-05",
						Showtimes: []model.ScheduleEntry{
							{ID: 101, StartTime: "14:30:00"},
							{ID: 102, StartTime: "18:00:00"},
						},
					},
				},
			},
		},
	}

	if err := cache.SetMovieDetail(ctx, 42, origDetail); err != nil {
		t.Fatalf("failed to set movie detail: %v", err)
	}

	// 3. Cache hit
	cached, found, err := cache.GetMovieDetail(ctx, 42)
	if err != nil {
		t.Fatalf("unexpected error on cache hit: %v", err)
	}
	if !found || cached == nil {
		t.Fatalf("expected cache hit, got found=%v, cached=%v", found, cached)
	}
	if cached.Movie.Title != "Dune: Part Two" || len(cached.Schedules) != 1 {
		t.Errorf("unexpected cached content: %+v", cached)
	}

	// 4. Invalidate specific movie
	if err := cache.InvalidateMovie(ctx, 42); err != nil {
		t.Fatalf("failed to invalidate movie: %v", err)
	}

	// 5. Lookup after invalidation -> Cache miss
	_, found, err = cache.GetMovieDetail(ctx, 42)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if found {
		t.Errorf("expected cache miss after invalidation, but found key")
	}
}

func TestMovieCache_List(t *testing.T) {
	mr, cache := setupTestRedis(t)
	defer mr.Close()

	ctx := context.Background()

	filters := MovieListFilters{
		Provider: "GV",
		Status:   "now_showing",
		Page:     1,
		Limit:    20,
	}

	// 1. Initial lookup -> Miss
	movies, total, found, err := cache.GetMovieList(ctx, filters)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if found || movies != nil || total != 0 {
		t.Fatalf("expected miss, got found=%v, movies=%v, total=%d", found, movies, total)
	}

	// 2. Set list
	origMovies := []model.Movie{
		{ID: 1, Title: "Avatar 3", Provider: "GV", Status: "now_showing"},
		{ID: 2, Title: "Wicked", Provider: "GV", Status: "now_showing"},
	}

	if err := cache.SetMovieList(ctx, filters, origMovies, 2); err != nil {
		t.Fatalf("failed to set movie list: %v", err)
	}

	// 3. Cache hit
	cachedMovies, cachedTotal, found, err := cache.GetMovieList(ctx, filters)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !found || len(cachedMovies) != 2 || cachedTotal != 2 {
		t.Fatalf("expected cache hit with 2 items, got found=%v, count=%d, total=%d", found, len(cachedMovies), cachedTotal)
	}
	if cachedMovies[0].Title != "Avatar 3" {
		t.Errorf("expected 'Avatar 3', got %s", cachedMovies[0].Title)
	}

	// 4. Invalidate all movies
	deleted, err := cache.InvalidateAllMovies(ctx)
	if err != nil {
		t.Fatalf("failed to invalidate all movies: %v", err)
	}
	if deleted < 1 {
		t.Errorf("expected at least 1 deleted key, got %d", deleted)
	}

	// 5. Lookup after full flush -> Miss
	_, _, found, err = cache.GetMovieList(ctx, filters)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if found {
		t.Errorf("expected miss after InvalidateAllMovies, but got found")
	}
}

func TestMovieCache_Stats(t *testing.T) {
	mr, cache := setupTestRedis(t)
	defer mr.Close()

	ctx := context.Background()

	// 1 miss
	_, _, _ = cache.GetMovieDetail(ctx, 999)

	// 1 set
	_ = cache.SetMovieDetail(ctx, 999, &model.MovieDetail{
		Movie: model.Movie{ID: 999, Title: "Test"},
	})

	// 1 hit
	_, _, _ = cache.GetMovieDetail(ctx, 999)

	stats := cache.Stats()
	if !stats.Connected {
		t.Errorf("expected connected=true")
	}
	if stats.Hits != 1 {
		t.Errorf("expected 1 hit, got %d", stats.Hits)
	}
	if stats.Misses != 1 {
		t.Errorf("expected 1 miss, got %d", stats.Misses)
	}
	if stats.Sets != 1 {
		t.Errorf("expected 1 set, got %d", stats.Sets)
	}
	if stats.HitRate != 0.5 {
		t.Errorf("expected hit_rate=0.5, got %f", stats.HitRate)
	}
}

func TestMovieCache_GracefulDegradation(t *testing.T) {
	// Nil client / disabled client should not panic and should report cache miss
	nilCache := NewMovieCache(nil, 0, 0)
	ctx := context.Background()

	detail, found, err := nilCache.GetMovieDetail(ctx, 1)
	if err != nil || found || detail != nil {
		t.Errorf("expected graceful miss with nil client, got detail=%v, found=%v, err=%v", detail, found, err)
	}

	err = nilCache.SetMovieDetail(ctx, 1, &model.MovieDetail{})
	if err != nil {
		t.Errorf("expected nil error on set with nil client, got %v", err)
	}

	movies, total, found, err := nilCache.GetMovieList(ctx, MovieListFilters{})
	if err != nil || found || movies != nil || total != 0 {
		t.Errorf("expected graceful miss for list, got %v, %v, %v, %v", movies, total, found, err)
	}

	stats := nilCache.Stats()
	if stats.Connected {
		t.Errorf("expected connected=false for nil client")
	}
}
