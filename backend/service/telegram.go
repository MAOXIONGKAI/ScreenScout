package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/maoxiongkai/screenscout-backend/model"
)

// TelegramService handles sending alerts to users' Telegram handles.
type TelegramService struct {
	BotToken string
	Client   *http.Client
}

// NewTelegramService creates a new TelegramService instance.
func NewTelegramService() *TelegramService {
	return &TelegramService{
		BotToken: os.Getenv("TELEGRAM_BOT_TOKEN"),
		Client:   &http.Client{Timeout: 10 * time.Second},
	}
}

// FormatMovieAlertMessage formats a rich notification text for single or multiple matched movies.
func FormatMovieAlertMessage(username, movieQuery string, movies []model.Movie) string {
	if len(movies) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("🎬 *ScreenScout Movie Alert!*\n\n")
	sb.WriteString(fmt.Sprintf("Hello @%s,\n", username))

	if len(movies) == 1 {
		m := movies[0]
		statusStr := "Now Showing"
		if m.Status == "coming_soon" {
			statusStr = "Coming Soon"
		}
		providerStr := "Golden Village"
		if m.Provider == "SHAW" || m.Provider == "Shaw" {
			providerStr = "Shaw Theatres"
		}

		sb.WriteString(fmt.Sprintf("Your tracked movie keyword *\"%s\"* is now available!\n\n", movieQuery))
		sb.WriteString(fmt.Sprintf("🎥 *%s*\n", m.Title))
		sb.WriteString(fmt.Sprintf("📌 Status: %s\n", statusStr))
		sb.WriteString(fmt.Sprintf("🏢 Cinema: %s\n", providerStr))
		sb.WriteString(fmt.Sprintf("📅 Release Date: %s\n\n", m.ReleaseDate))
		sb.WriteString(fmt.Sprintf("🔗 Check showtimes: http://localhost:3000/movies/%d", m.ID))
	} else {
		sb.WriteString(fmt.Sprintf("Your tracked movie keyword *\"%s\"* matched *%d* movies!\n\n", movieQuery, len(movies)))
		for i, m := range movies {
			statusStr := "Now Showing"
			if m.Status == "coming_soon" {
				statusStr = "Coming Soon"
			}
			providerStr := "Golden Village"
			if m.Provider == "SHAW" || m.Provider == "Shaw" {
				providerStr = "Shaw Theatres"
			}

			sb.WriteString(fmt.Sprintf("%d. 🎥 *%s*\n", i+1, m.Title))
			sb.WriteString(fmt.Sprintf("   🏢 %s • 📌 %s\n", providerStr, statusStr))
			sb.WriteString(fmt.Sprintf("   📅 %s • 🔗 http://localhost:3000/movies/%d\n\n", m.ReleaseDate, m.ID))
		}
	}

	return sb.String()
}

// SendNotification dispatches a message to the user's Telegram handle or chat ID.
func (s *TelegramService) SendNotification(recipient, message string) (string, error) {
	if s.BotToken == "" {
		// Simulation mode when bot token is not configured
		fmt.Printf("\n[Telegram Simulation] Sending notification to %s:\n%s\n\n", recipient, message)
		return "SIMULATED", nil
	}

	apiURL := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", s.BotToken)
	payload := map[string]string{
		"chat_id":    recipient,
		"text":       message,
		"parse_mode": "Markdown",
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return "FAILED", err
	}

	resp, err := s.Client.Post(apiURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("[Telegram Error] Failed to send message: %v\n", err)
		return "FAILED", err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		fmt.Printf("[Telegram Warning] Telegram API returned status %d\n", resp.StatusCode)
		return "FAILED", fmt.Errorf("telegram API status %d", resp.StatusCode)
	}

	return "SENT", nil
}
