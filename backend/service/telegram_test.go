package service

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/redis/go-redis/v9"
)

func TestFormatMovieAlertMessage_Empty(t *testing.T) {
	msg := FormatMovieAlertMessage("alice", "dune", []model.Movie{})
	if msg != "" {
		t.Errorf("Expected empty string for no movies, got '%s'", msg)
	}
}

func TestFormatMovieAlertMessage_SingleMovie(t *testing.T) {
	movies := []model.Movie{
		{
			ID:          10,
			Title:       "Dune: Part Two",
			Provider:    "GV",
			Status:      "now_showing",
			ReleaseDate: "2026-08-28",
		},
	}

	msg := FormatMovieAlertMessage("bob", "dune", movies)
	if !strings.Contains(msg, "ScreenScout Movie Alert") {
		t.Error("Message should contain header")
	}
	if !strings.Contains(msg, "Hello @bob") {
		t.Error("Message should contain user handle")
	}
	if !strings.Contains(msg, "Dune: Part Two") {
		t.Error("Message should contain movie title")
	}
	if !strings.Contains(msg, "Golden Village") {
		t.Error("Message should map GV to Golden Village")
	}
	if !strings.Contains(msg, "/movies/10") {
		t.Error("Message should include link with ID 10")
	}
}

func TestFormatMovieAlertMessage_AdvanceSales(t *testing.T) {
	movies := []model.Movie{
		{
			ID:          15,
			Title:       "Deadpool 4",
			Provider:    "GV",
			Status:      "advance_sales",
			ReleaseDate: "2026-11-20",
		},
	}

	msg := FormatMovieAlertMessage("bob", "deadpool", movies)
	if !strings.Contains(msg, "📌 Status: <b>Advance Sales</b>") {
		t.Errorf("Expected '📌 Status: <b>Advance Sales</b>', got:\n%s", msg)
	}
}

func TestFormatMovieAlertMessage_MultipleMovies(t *testing.T) {
	movies := []model.Movie{
		{
			ID:          1,
			Title:       "Avatar 3",
			Provider:    "Shaw",
			Status:      "coming_soon",
			ReleaseDate: "2026-12-18",
		},
		{
			ID:          2,
			Title:       "Avatar 4",
			Provider:    "GV",
			Status:      "coming_soon",
			ReleaseDate: "2028-12-22",
		},
	}

	msg := FormatMovieAlertMessage("charlie", "avatar", movies)
	if !strings.Contains(msg, "matched <b>2</b> movies") {
		t.Error("Message should state matched count 2")
	}
	if !strings.Contains(msg, "Avatar 3") || !strings.Contains(msg, "Avatar 4") {
		t.Error("Message should list both movie titles")
	}
	if !strings.Contains(msg, "Shaw Theatres") {
		t.Error("Message should map Shaw to Shaw Theatres")
	}
}

func TestFormatWelcomeMessage(t *testing.T) {
	msg := FormatWelcomeMessage("X", "@xXG_YXx")
	if !strings.Contains(msg, "Welcome to ScreenScout, X!") {
		t.Error("Welcome message should contain user name")
	}
	if !strings.Contains(msg, "Your Telegram account (@xXG_YXx) is now linked") {
		t.Error("Welcome message should contain handle")
	}
	if !strings.Contains(msg, "Golden Village & Shaw Theatres") {
		t.Error("Welcome message should list supported cinemas")
	}
	if !strings.Contains(msg, "Happy movie hunting! 🍿") {
		t.Error("Welcome message should contain closing tagline")
	}
}

func TestSendNotification_RedisStream(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}
	defer mr.Close()

	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	redisClient := cache.NewFromUniversalClient(rdb)

	svc := NewTelegramService()
	svc.SetRedisClient(redisClient)
	svc.StreamName = "test:notifications:stream"

	status, err := svc.SendNotification("@testuser", "Hello from Redis Stream test!")
	if err != nil {
		t.Fatalf("unexpected error on SendNotification: %v", err)
	}
	if status != "SIMULATED" && status != "SENT" {
		t.Fatalf("expected status 'SIMULATED' or 'SENT', got %s", status)
	}

	time.Sleep(50 * time.Millisecond)

	// Verify the stream contains the event
	ctx := context.Background()
	msgs, err := rdb.XRange(ctx, "test:notifications:stream", "-", "+").Result()
	if err != nil {
		t.Fatalf("failed to read stream: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message in stream, got %d", len(msgs))
	}

	values := msgs[0].Values
	if values["recipient"] != "@testuser" {
		t.Errorf("expected recipient @testuser, got %v", values["recipient"])
	}
	if values["message"] != "Hello from Redis Stream test!" {
		t.Errorf("expected message content, got %v", values["message"])
	}
	if values["channel_type"] != "TELEGRAM" {
		t.Errorf("expected channel_type TELEGRAM, got %v", values["channel_type"])
	}
}

func TestSendNotification_Fallback(t *testing.T) {
	// Service without Redis client should fallback to simulation mode when bot token is empty
	svc := NewTelegramService()
	svc.BotToken = ""

	status, err := svc.SendNotification("@offlineuser", "Fallback message")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if status != "SIMULATED" {
		t.Errorf("expected 'SIMULATED', got %s", status)
	}
}

func TestValidateTelegramHandle_Format(t *testing.T) {
	svc := NewTelegramService()
	ctx := context.Background()

	// Empty handle
	_, err := svc.ValidateTelegramHandle(ctx, "")
	if err == nil || !strings.Contains(err.Error(), "empty") {
		t.Errorf("Expected empty handle error, got: %v", err)
	}

	// Invalid format: too short
	_, err = svc.ValidateTelegramHandle(ctx, "@abc")
	if err == nil || !strings.Contains(err.Error(), "invalid Telegram handle format") {
		t.Errorf("Expected format error for short handle, got: %v", err)
	}

	// Invalid format: special symbols
	_, err = svc.ValidateTelegramHandle(ctx, "@hello!world")
	if err == nil || !strings.Contains(err.Error(), "invalid Telegram handle format") {
		t.Errorf("Expected format error for special characters, got: %v", err)
	}

	// Invalid format: starts with number
	_, err = svc.ValidateTelegramHandle(ctx, "@123user")
	if err == nil || !strings.Contains(err.Error(), "invalid Telegram handle format") {
		t.Errorf("Expected format error for starting with digit, got: %v", err)
	}

	// Valid numeric chat ID
	validID, err := svc.ValidateTelegramHandle(ctx, "987654321")
	if err != nil {
		t.Errorf("Expected numeric ID to be valid, got: %v", err)
	}
	if validID != "987654321" {
		t.Errorf("Expected '987654321', got %s", validID)
	}
}

func TestValidateTelegramHandle_NonExistent(t *testing.T) {
	svc := NewTelegramService()
	ctx := context.Background()

	// Random non-existent handle
	_, err := svc.ValidateTelegramHandle(ctx, "@nonexistent_user_998822119933")
	if err == nil || !strings.Contains(err.Error(), "does not exist") {
		t.Errorf("Expected 'does not exist' error, got: %v", err)
	}
}

func TestValidateTelegramHandle_Existing(t *testing.T) {
	svc := NewTelegramService()
	ctx := context.Background()

	// ScreenScout bot handle or Telegram official handle
	res, err := svc.ValidateTelegramHandle(ctx, "@The_ScreenScout_Bot")
	if err != nil {
		t.Errorf("Expected The_ScreenScout_Bot to exist, got: %v", err)
	}
	if res != "@The_ScreenScout_Bot" {
		t.Errorf("Expected '@The_ScreenScout_Bot', got '%s'", res)
	}
}

