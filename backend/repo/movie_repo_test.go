package repo

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/redis/go-redis/v9"
)

func TestMovieRepo_WithCache(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}
	defer mr.Close()

	rdb := redis.NewClient(&redis.Options{
		Addr: mr.Addr(),
	})
	redisClient := cache.NewFromUniversalClient(rdb)
	movieCache := cache.NewMovieCache(redisClient, 5*time.Minute, 10*time.Minute)

	// Note: Pool is nil for this unit test since cache hit avoids DB pool execution
	repo := NewMovieRepo(nil)
	repo.SetCache(movieCache)

	if repo.GetCache() != movieCache {
		t.Errorf("expected GetCache to return attached movieCache")
	}

	ctx := context.Background()

	// Pre-populate cache with a movie detail
	testDetail := &model.MovieDetail{
		Movie: model.Movie{
			ID:       100,
			Title:    "Interstellar",
			Provider: "GV",
			Status:   "now_showing",
		},
		Schedules: []model.CinemaSchedule{
			{
				CinemaID:   1,
				CinemaName: "GV Suntec",
				Branch:     "Suntec City",
			},
		},
	}
	if err := movieCache.SetMovieDetail(ctx, 100, testDetail); err != nil {
		t.Fatalf("failed to seed cache: %v", err)
	}

	// 1. GetMovieByID should return cached item directly without touching DB
	detail, err := repo.GetMovieByID(ctx, 100)
	if err != nil {
		t.Fatalf("unexpected error on cached GetMovieByID: %v", err)
	}
	if detail == nil || detail.Movie.Title != "Interstellar" {
		t.Fatalf("expected cached movie detail, got %+v", detail)
	}

	// Pre-populate cache with a movie list
	filters := MovieFilters{
		Provider: "GV",
		Page:     1,
		Limit:    20,
	}
	cacheFilters := cache.MovieListFilters{
		Provider: "GV",
		Page:     1,
		Limit:    20,
	}
	testMovies := []model.Movie{
		{ID: 100, Title: "Interstellar", Provider: "GV"},
	}
	if err := movieCache.SetMovieList(ctx, cacheFilters, testMovies, 1); err != nil {
		t.Fatalf("failed to seed list cache: %v", err)
	}

	// 2. ListMovies should return cached movies directly without touching DB
	movies, total, err := repo.ListMovies(ctx, filters)
	if err != nil {
		t.Fatalf("unexpected error on cached ListMovies: %v", err)
	}
	if len(movies) != 1 || total != 1 || movies[0].Title != "Interstellar" {
		t.Fatalf("expected 1 cached movie, got %d (total %d)", len(movies), total)
	}

	// 3. Test InvalidateMovie
	if err := repo.InvalidateMovie(ctx, 100); err != nil {
		t.Fatalf("failed to invalidate movie: %v", err)
	}

	// Verify detail is invalidated from cache
	_, found, _ := movieCache.GetMovieDetail(ctx, 100)
	if found {
		t.Errorf("expected movie detail to be deleted from cache")
	}

	// 4. Test InvalidateAllMovies
	if err := movieCache.SetMovieDetail(ctx, 200, testDetail); err != nil {
		t.Fatalf("failed to seed cache: %v", err)
	}
	deleted, err := repo.InvalidateAllMovies(ctx)
	if err != nil {
		t.Fatalf("failed to invalidate all movies: %v", err)
	}
	if deleted < 1 {
		t.Errorf("expected deleted >= 1, got %d", deleted)
	}
}
