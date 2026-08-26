package model

import (
	"encoding/json"
	"testing"
	"time"
)

func strPtr(s string) *string {
	return &s
}

func TestSubscriptionJSONSerialization(t *testing.T) {
	now := time.Date(2026, 8, 26, 12, 0, 0, 0, time.UTC)
	sub := Subscription{
		ID:         1,
		UserID:     10,
		MovieQuery: "spider-man",
		IsActive:   true,
		MatchedMovies: []MatchedMovieItem{
			{
				ID:          100,
				Title:       "Spider-Man: Beyond the Spider-Verse",
				Provider:    "GV",
				Status:      "now_showing",
				ReleaseDate: "2026-08-28",
			},
		},
		CreatedAt: now,
		UpdatedAt: now,
	}

	data, err := json.Marshal(sub)
	if err != nil {
		t.Fatalf("Failed to marshal subscription: %v", err)
	}

	var parsed Subscription
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal subscription: %v", err)
	}

	if parsed.MovieQuery != "spider-man" {
		t.Errorf("Expected MovieQuery 'spider-man', got '%s'", parsed.MovieQuery)
	}
	if !parsed.IsActive {
		t.Error("Expected IsActive to be true")
	}
	if len(parsed.MatchedMovies) != 1 {
		t.Fatalf("Expected 1 matched movie, got %d", len(parsed.MatchedMovies))
	}
	if parsed.MatchedMovies[0].Title != "Spider-Man: Beyond the Spider-Verse" {
		t.Errorf("Expected title 'Spider-Man: Beyond the Spider-Verse', got '%s'", parsed.MatchedMovies[0].Title)
	}
}

func TestMovieModelSerialization(t *testing.T) {
	movie := Movie{
		ID:          55,
		Title:       "Inception",
		Provider:    "Shaw",
		Status:      "now_showing",
		Duration:    148,
		Genre:       strPtr("Sci-Fi, Action"),
		Director:    strPtr("Christopher Nolan"),
		Casts:       strPtr("Leonardo DiCaprio, Joseph Gordon-Levitt"),
		TrailerURL:  strPtr("https://youtube.com/watch?v=example"),
		ReleaseDate: "2010-07-16",
	}

	data, err := json.Marshal(movie)
	if err != nil {
		t.Fatalf("Failed to marshal movie: %v", err)
	}

	var parsed Movie
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal movie: %v", err)
	}

	if parsed.Title != "Inception" {
		t.Errorf("Expected Title 'Inception', got '%s'", parsed.Title)
	}
	if parsed.Duration != 148 {
		t.Errorf("Expected Duration 148, got %d", parsed.Duration)
	}
	if parsed.Genre == nil || *parsed.Genre != "Sci-Fi, Action" {
		t.Errorf("Expected Genre 'Sci-Fi, Action', got '%v'", parsed.Genre)
	}
}

func TestNotificationChannelJSON(t *testing.T) {
	channel := NotificationChannel{
		ID:            5,
		UserID:        10,
		ChannelType:   "TELEGRAM",
		ChannelUserID: "@movie_fanatic",
		IsEnabled:     true,
	}

	data, err := json.Marshal(channel)
	if err != nil {
		t.Fatalf("Failed to marshal channel: %v", err)
	}

	var parsed NotificationChannel
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal channel: %v", err)
	}

	if parsed.ChannelUserID != "@movie_fanatic" {
		t.Errorf("Expected ChannelUserID '@movie_fanatic', got '%s'", parsed.ChannelUserID)
	}
}
