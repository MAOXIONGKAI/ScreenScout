package handler

import (
	"context"
	"net/http"
	"testing"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/cloudwego/hertz/pkg/protocol/consts"
	"github.com/cloudwego/hertz/pkg/route/param"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

func TestReviewHandler_Unauthenticated(t *testing.T) {
	h := NewReviewHandler(repo.NewReviewRepo(nil), repo.NewMovieRepo(nil))
	ctx := context.Background()

	// 1. Create review without user_id in context -> 401
	c1 := app.NewContext(16)
	c1.Request.Header.SetMethod(consts.MethodPost)
	c1.Request.SetRequestURI("/api/movies/1/reviews")
	c1.Params = []param.Param{{Key: "id", Value: "1"}}

	h.CreateMovieReview(ctx, c1)
	if c1.Response.StatusCode() != http.StatusUnauthorized {
		t.Errorf("expected status 401, got %d", c1.Response.StatusCode())
	}

	// 2. Delete review without user_id in context -> 401
	c2 := app.NewContext(16)
	c2.Request.Header.SetMethod(consts.MethodDelete)
	c2.Request.SetRequestURI("/api/movies/1/reviews/10")
	c2.Params = []param.Param{{Key: "id", Value: "1"}, {Key: "review_id", Value: "10"}}

	h.DeleteMovieReview(ctx, c2)
	if c2.Response.StatusCode() != http.StatusUnauthorized {
		t.Errorf("expected status 401, got %d", c2.Response.StatusCode())
	}
}

func TestReviewHandler_InvalidInputs(t *testing.T) {
	h := NewReviewHandler(repo.NewReviewRepo(nil), repo.NewMovieRepo(nil))
	ctx := context.Background()

	// 1. Invalid movie ID on list
	c1 := app.NewContext(16)
	c1.Request.Header.SetMethod(consts.MethodGet)
	c1.Request.SetRequestURI("/api/movies/abc/reviews")
	c1.Params = []param.Param{{Key: "id", Value: "abc"}}

	h.ListMovieReviews(ctx, c1)
	if c1.Response.StatusCode() != http.StatusBadRequest {
		t.Errorf("expected status 400 for invalid movie ID, got %d", c1.Response.StatusCode())
	}

	// 2. Invalid rating
	c2 := app.NewContext(16)
	c2.Request.Header.SetMethod(consts.MethodPost)
	c2.Request.SetRequestURI("/api/movies/1/reviews")
	c2.Params = []param.Param{{Key: "id", Value: "1"}}
	c2.Set("user_id", int64(1))
	c2.Request.SetBody([]byte(`{"rating": 10, "content": "Awesome"}`))
	c2.Request.Header.SetContentTypeBytes([]byte("application/json"))

	h.CreateMovieReview(ctx, c2)
	if c2.Response.StatusCode() != http.StatusBadRequest {
		t.Errorf("expected status 400 for rating 10, got %d", c2.Response.StatusCode())
	}

	// 3. Empty content
	c3 := app.NewContext(16)
	c3.Request.Header.SetMethod(consts.MethodPost)
	c3.Request.SetRequestURI("/api/movies/1/reviews")
	c3.Params = []param.Param{{Key: "id", Value: "1"}}
	c3.Set("user_id", int64(1))
	c3.Request.SetBody([]byte(`{"rating": 5, "content": "   "}`))
	c3.Request.Header.SetContentTypeBytes([]byte("application/json"))

	h.CreateMovieReview(ctx, c3)
	if c3.Response.StatusCode() != http.StatusBadRequest {
		t.Errorf("expected status 400 for empty content, got %d", c3.Response.StatusCode())
	}
}
