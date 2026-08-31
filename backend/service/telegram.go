package service

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/redis/go-redis/v9"
)

var (
	telegramHandleRegex    = regexp.MustCompile(`^[a-zA-Z][a-zA-Z0-9_]{4,31}$`)
	telegramNumericIDRegex = regexp.MustCompile(`^[0-9]{5,15}$`)
)

// DefaultNotificationStream is the default Redis Stream key for asynchronous notification dispatch.
const DefaultNotificationStream = "screenscout:notifications:stream"

// TelegramService handles sending alerts to users' Telegram handles.
type TelegramService struct {
	BotToken    string
	Client      *http.Client
	RedisClient *cache.Client
	StreamName  string
}

// NewTelegramService creates a new TelegramService instance.
func NewTelegramService() *TelegramService {
	streamName := os.Getenv("NOTIFICATION_STREAM_NAME")
	if streamName == "" {
		streamName = DefaultNotificationStream
	}

	return &TelegramService{
		BotToken:   os.Getenv("TELEGRAM_BOT_TOKEN"),
		Client:     &http.Client{Timeout: 10 * time.Second},
		StreamName: streamName,
	}
}

// SetRedisClient attaches a Redis client for asynchronous stream publishing.
func (s *TelegramService) SetRedisClient(c *cache.Client) {
	s.RedisClient = c
}

func getFrontendBaseURL() string {
	baseURL := os.Getenv("FRONTEND_URL")
	if baseURL == "" {
		baseURL = os.Getenv("NEXT_PUBLIC_API_URL")
	}
	if baseURL == "" {
		baseURL = "https://www.screenscout.live"
	}
	return strings.TrimRight(baseURL, "/")
}

// FormatMovieAlertMessage formats a rich notification text for single or multiple matched movies.
func FormatMovieAlertMessage(username, movieQuery string, movies []model.Movie) string {
	if len(movies) == 0 {
		return ""
	}

	cleanUser := strings.TrimPrefix(strings.TrimSpace(username), "@")
	escapedUser := strings.ReplaceAll(cleanUser, "_", "\\_")
	escapedQuery := strings.ReplaceAll(strings.ReplaceAll(movieQuery, "*", ""), "_", "\\_")

	base := getFrontendBaseURL()
	var sb strings.Builder
	sb.WriteString("🎬 *ScreenScout Movie Alert!*\n\n")
	sb.WriteString(fmt.Sprintf("Hello @%s,\n", escapedUser))

	if len(movies) == 1 {
		m := movies[0]
		statusStr := "Now Showing"
		if m.Status == "advance_sales" {
			statusStr = "Advance Sales"
		} else if m.Status == "coming_soon" {
			statusStr = "Coming Soon"
		}
		providerStr := "Golden Village"
		if m.Provider == "SHAW" || m.Provider == "Shaw" {
			providerStr = "Shaw Theatres"
		}
		cleanTitle := strings.ReplaceAll(strings.ReplaceAll(m.Title, "*", ""), "_", "\\_")

		sb.WriteString(fmt.Sprintf("Your tracked movie keyword *\"%s\"* is now available!\n\n", escapedQuery))
		sb.WriteString(fmt.Sprintf("🎥 *%s*\n", cleanTitle))
		sb.WriteString(fmt.Sprintf("📌 Status: %s\n", statusStr))
		sb.WriteString(fmt.Sprintf("🏢 Cinema: %s\n", providerStr))
		sb.WriteString(fmt.Sprintf("📅 Release Date: %s\n\n", m.ReleaseDate))
		sb.WriteString(fmt.Sprintf("🔗 Check showtimes: %s/movies/%d", base, m.ID))
	} else {
		sb.WriteString(fmt.Sprintf("Your tracked movie keyword *\"%s\"* matched *%d* movies!\n\n", escapedQuery, len(movies)))
		for i, m := range movies {
			statusStr := "Now Showing"
			if m.Status == "advance_sales" {
				statusStr = "Advance Sales"
			} else if m.Status == "coming_soon" {
				statusStr = "Coming Soon"
			}
			providerStr := "Golden Village"
			if m.Provider == "SHAW" || m.Provider == "Shaw" {
				providerStr = "Shaw Theatres"
			}
			cleanTitle := strings.ReplaceAll(strings.ReplaceAll(m.Title, "*", ""), "_", "\\_")

			sb.WriteString(fmt.Sprintf("%d. 🎥 *%s*\n", i+1, cleanTitle))
			sb.WriteString(fmt.Sprintf("   🏢 %s • 📌 %s\n", providerStr, statusStr))
			sb.WriteString(fmt.Sprintf("   📅 %s • 🔗 %s/movies/%d\n\n", m.ReleaseDate, base, m.ID))
		}
	}

	return sb.String()
}

// FormatWelcomeMessage formats the confirmation text when a user links their Telegram account.
func FormatWelcomeMessage(name, handle string) string {
	cleanHandle := strings.TrimPrefix(strings.TrimSpace(handle), "@")
	escapedHandle := strings.ReplaceAll(cleanHandle, "_", "\\_")
	cleanName := strings.TrimSpace(name)
	if cleanName == "" {
		cleanName = cleanHandle
	}
	cleanName = strings.ReplaceAll(cleanName, "*", "")

	return fmt.Sprintf("🎬 *Welcome to ScreenScout, %s!*\n\n"+
		"✅ Your Telegram account (@%s) is now linked for real-time movie notifications!\n\n"+
		"You will automatically receive alerts here the moment showtimes or new screenings "+
		"for your subscribed movies are published across Singapore cinemas (Golden Village & Shaw Theatres).\n\n"+
		"Happy movie hunting! 🍿", cleanName, escapedHandle)
}

// SendNotification dispatches a message to the user's Telegram handle or chat ID.
// It prioritizes publishing an event to Redis Streams (asynchronous, decoupled),
// falling back to synchronous HTTP or direct simulation if Redis is offline.
func (s *TelegramService) SendNotification(recipient, message string) (string, error) {
	// 1. Primary: Publish to Redis Stream for asynchronous decoupled processing
	if s.RedisClient != nil && s.RedisClient.IsAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		streamName := s.StreamName
		if streamName == "" {
			streamName = DefaultNotificationStream
		}

		_, err := s.RedisClient.XAdd(ctx, &redis.XAddArgs{
			Stream: streamName,
			Values: map[string]interface{}{
				"recipient":    recipient,
				"message":      message,
				"channel_type": "TELEGRAM",
				"parse_mode":   "Markdown",
				"created_at":   time.Now().UTC().Format(time.RFC3339),
				"retry_count":  "0",
			},
		})
		if err == nil {
			return "QUEUED", nil
		}
		fmt.Printf("[Notification Stream Warning] Failed to publish to Redis Stream: %v. Falling back to HTTP delivery.\n", err)
	}

	// 2. Secondary: Fallback to Notification Service HTTP endpoint
	notifyURL := os.Getenv("NOTIFICATION_SERVICE_URL")
	if notifyURL == "" {
		notifyURL = "http://localhost:8085/api/notify"
	}

	payload := map[string]string{
		"recipient":    recipient,
		"message":      message,
		"channel_type": "TELEGRAM",
	}
	jsonData, _ := json.Marshal(payload)
	resp, err := s.Client.Post(notifyURL, "application/json", bytes.NewBuffer(jsonData))
	if err == nil {
		defer resp.Body.Close()
		if resp.StatusCode == http.StatusOK {
			var res map[string]interface{}
			if err := json.NewDecoder(resp.Body).Decode(&res); err == nil {
				if status, ok := res["status"].(string); ok {
					return status, nil
				}
				return "SENT", nil
			}
		}
	}

	// 3. Fallback to direct Telegram Bot API / local simulation
	if s.BotToken == "" {
		fmt.Printf("\n[Telegram Simulation] Sending notification to %s:\n%s\n\n", recipient, message)
		return "SIMULATED", nil
	}

	apiURL := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", s.BotToken)
	directPayload := map[string]string{
		"chat_id":    recipient,
		"text":       message,
		"parse_mode": "Markdown",
	}

	directData, err := json.Marshal(directPayload)
	if err != nil {
		return "FAILED", err
	}

	dResp, err := s.Client.Post(apiURL, "application/json", bytes.NewBuffer(directData))
	if err != nil {
		fmt.Printf("[Telegram Error] Failed to send message: %v\n", err)
		return "FAILED", err
	}
	defer dResp.Body.Close()

	if dResp.StatusCode >= 400 {
		fmt.Printf("[Telegram Warning] Telegram API returned status %d\n", dResp.StatusCode)
		return "FAILED", fmt.Errorf("telegram API status %d", dResp.StatusCode)
	}

	return "SENT", nil
}

// SendDirectNotification synchronously sends a notification via Notification Service HTTP API
// and returns full diagnostic fields (status, error, hint, chat_id).
func (s *TelegramService) SendDirectNotification(recipient, message string) (map[string]interface{}, error) {
	notifyURL := os.Getenv("NOTIFICATION_SERVICE_URL")
	if notifyURL == "" {
		notifyURL = "http://localhost:8085/api/notify"
	}

	payload := map[string]string{
		"recipient":    recipient,
		"message":      message,
		"channel_type": "TELEGRAM",
	}
	jsonData, _ := json.Marshal(payload)
	resp, err := s.Client.Post(notifyURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("notification service unavailable: %w", err)
	}
	defer resp.Body.Close()

	var res map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, fmt.Errorf("failed to parse notification response (HTTP %d)", resp.StatusCode)
	}

	if resp.StatusCode != http.StatusOK {
		errMsg, _ := res["error"].(string)
		if errMsg == "" {
			errMsg = fmt.Sprintf("notification service returned HTTP %d", resp.StatusCode)
		}
		return res, errors.New(errMsg)
	}

	return res, nil
}

// ValidateTelegramHandle verifies that a Telegram username has a valid format and exists on Telegram.
func (s *TelegramService) ValidateTelegramHandle(ctx context.Context, handle string) (string, error) {
	clean := strings.TrimSpace(handle)
	clean = strings.TrimPrefix(clean, "@")
	clean = strings.TrimSpace(clean)

	if clean == "" {
		return "", errors.New("telegram handle cannot be empty")
	}

	// 1. Numeric chat ID (direct ID, e.g. 123456789)
	if telegramNumericIDRegex.MatchString(clean) {
		return clean, nil
	}

	// 2. Format validation (Telegram username standards: 5-32 alphanumeric/underscore characters, starts with a letter)
	if !telegramHandleRegex.MatchString(clean) {
		return "", errors.New("invalid Telegram handle format: must be 5–32 alphanumeric characters or underscores and start with a letter (e.g. @your_handle)")
	}

	// 3. Online Telegram existence check via Telegram domain resolver (t.me/<username>)
	reqURL := fmt.Sprintf("https://t.me/%s", clean)
	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return "@" + clean, nil
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

	resp, err := s.Client.Do(req)
	if err != nil {
		// Network timeout or offline environment, gracefully allow valid format
		return "@" + clean, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		bodyBytes, readErr := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
		if readErr == nil {
			html := string(bodyBytes)
			hasPageTitle := strings.Contains(html, `class="tgme_page_title"`)

			// If hasPageTitle is false, the handle does not exist on Telegram
			if !hasPageTitle {
				return "", fmt.Errorf("the Telegram handle '@%s' does not exist. Please check the spelling or start a chat with @The_ScreenScout_Bot first", clean)
			}
		}
	}

	return "@" + clean, nil
}

