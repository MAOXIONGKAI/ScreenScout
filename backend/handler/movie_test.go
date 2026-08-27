package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/cloudwego/hertz/pkg/app"
	"github.com/cloudwego/hertz/pkg/protocol/consts"
	"github.com/cloudwego/hertz/pkg/route/param"
	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
	"github.com/redis/go-redis/v9"
)

func setupTestMovieHandler(t *testing.T) (*miniredis.Miniredis, *MovieHandler, *cache.MovieCache) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to run miniredis: %v", err)
	}

	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	client := cache.NewFromUniversalClient(rdb)
	movieCache := cache.NewMovieCache(client, 5*time.Minute, 10*time.Minute)

	movieRepo := repo.NewMovieRepo(nil)
	movieRepo.SetCache(movieCache)

	handler := NewMovieHandler(movieRepo)
	return mr, handler, movieCache
}

func TestMovieHandler_GetCacheStats(t *testing.T) {
	mr, h, _ := setupTestMovieHandler(t)
	defer mr.Close()

	ctx := context.Background()
	c := app.NewContext(16)
	c.Request.Header.SetMethod(consts.MethodGet)
	c.Request.SetRequestURI("/api/cache/stats")

	h.GetCacheStats(ctx, c)

	if c.Response.StatusCode() != http.StatusOK {
		t.Fatalf("expected status 200, got %d", c.Response.StatusCode())
	}

	var res map[string]interface{}
	if err := json.Unmarshal(c.Response.Body(), &res); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}

	if res["status"] != "enabled" {
		t.Errorf("expected status 'enabled', got %v", res["status"])
	}
}

func TestMovieHandler_InvalidateCache(t *testing.T) {
	mr, h, movieCache := setupTestMovieHandler(t)
	defer mr.Close()

	ctx := context.Background()

	// Seed cache
	_ = movieCache.SetMovieDetail(ctx, 88, &model.MovieDetail{
		Movie: model.Movie{ID: 88, Title: "Gladiator II"},
	})

	// 1. Invalidate specific movie
	c1 := app.NewContext(16)
	c1.Request.Header.SetMethod(consts.MethodPost)
	c1.Request.SetRequestURI("/api/cache/movies/invalidate?movie_id=88")

	h.InvalidateCache(ctx, c1)

	if c1.Response.StatusCode() != http.StatusOK {
		t.Fatalf("expected status 200, got %d", c1.Response.StatusCode())
	}

	_, found, _ := movieCache.GetMovieDetail(ctx, 88)
	if found {
		t.Errorf("expected movie 88 to be deleted from cache")
	}

	// 2. Invalidate all
	_ = movieCache.SetMovieDetail(ctx, 99, &model.MovieDetail{
		Movie: model.Movie{ID: 99, Title: "Oppenheimer"},
	})

	c2 := app.NewContext(16)
	c2.Request.Header.SetMethod(consts.MethodPost)
	c2.Request.SetRequestURI("/api/cache/movies/invalidate")

	h.InvalidateCache(ctx, c2)

	if c2.Response.StatusCode() != http.StatusOK {
		t.Fatalf("expected status 200, got %d", c2.Response.StatusCode())
	}

	_, found, _ = movieCache.GetMovieDetail(ctx, 99)
	if found {
		t.Errorf("expected movie 99 to be deleted after flush all")
	}
}

func TestMovieHandler_GetMovie_Cached(t *testing.T) {
	mr, h, movieCache := setupTestMovieHandler(t)
	defer mr.Close()

	ctx := context.Background()

	// Seed cache
	_ = movieCache.SetMovieDetail(ctx, 55, &model.MovieDetail{
		Movie: model.Movie{ID: 55, Title: "Interstellar"},
	})

	c := app.NewContext(16)
	c.Request.Header.SetMethod(consts.MethodGet)
	c.Request.SetRequestURI("/api/movies/55")
	c.Params = []param.Param{
		{Key: "id", Value: "55"},
	}

	h.GetMovie(ctx, c)

	if c.Response.StatusCode() != http.StatusOK {
		t.Fatalf("expected 200, got %d", c.Response.StatusCode())
	}

	if string(c.Response.Header.Peek("X-Cache")) != "HIT" {
		t.Errorf("expected X-Cache: HIT, got %s", string(c.Response.Header.Peek("X-Cache")))
	}

	var detail model.MovieDetail
	if err := json.Unmarshal(c.Response.Body(), &detail); err != nil {
		t.Fatalf("failed to decode body: %v", err)
	}

	if detail.Movie.Title != "Interstellar" {
		t.Errorf("expected Interstellar, got %s", detail.Movie.Title)
	}
}
