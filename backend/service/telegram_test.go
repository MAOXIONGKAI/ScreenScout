package service

import (
	"strings"
	"testing"

	"github.com/maoxiongkai/screenscout-backend/model"
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
