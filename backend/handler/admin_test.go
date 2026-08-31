package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/cloudwego/hertz/pkg/common/test/assert"
	"github.com/maoxiongkai/screenscout-backend/repo"
)

func TestNewAdminHandler(t *testing.T) {
	h := NewAdminHandler(&repo.AdminRepo{})
	assert.NotNil(t, h)
	assert.NotNil(t, h.Repo)
}

func TestAdminHandler_CleanDatabase_MockService(t *testing.T) {
	// Mock notification microservice returning 200 OK
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.DeepEqual(t, "/api/clean", r.URL.Path)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"success":true,"message":"Database cleanup completed successfully. Outdated schedules and past-year movies removed."}`))
	}))
	defer mockServer.Close()

	t.Setenv("NOTIFICATION_SERVICE_URL", mockServer.URL+"/api/notify")

	h := NewAdminHandler(&repo.AdminRepo{})
	ctx := context.Background()
	c := app.NewContext(16)
	c.Request.SetMethod("POST")
	c.Request.SetRequestURI("/api/admin/clean")

	h.CleanDatabase(ctx, c)

	assert.DeepEqual(t, http.StatusOK, c.Response.StatusCode())
}
