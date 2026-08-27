package service

import (
	"context"
	"strings"
	"testing"

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
	if !strings.Contains(msg, "matched *2* movies") {
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
	if !strings.Contains(msg, "Your Telegram account (@xXG\\_YXx) is now linked") {
		t.Error("Welcome message should contain escaped handle")
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
	if status != "QUEUED" {
		t.Fatalf("expected status 'QUEUED', got %s", status)
	}

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
