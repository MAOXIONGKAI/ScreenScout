package handler

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
	"github.com/maoxiongkai/screenscout-backend/service"
)

// SubscriptionHandler handles HTTP requests for user notification settings and subscriptions.
type SubscriptionHandler struct {
	SubRepo  *repo.SubscriptionRepo
	UserRepo *repo.UserRepo
	Telegram *service.TelegramService
}

// NewSubscriptionHandler creates a new SubscriptionHandler instance.
func NewSubscriptionHandler(subRepo *repo.SubscriptionRepo, userRepo *repo.UserRepo, tg *service.TelegramService) *SubscriptionHandler {
	return &SubscriptionHandler{
		SubRepo:  subRepo,
		UserRepo: userRepo,
		Telegram: tg,
	}
}

// GetBotInfo handles GET /api/telegram/bot-info
func (h *SubscriptionHandler) GetBotInfo(ctx context.Context, c *app.RequestContext) {
	notifyURL := os.Getenv("NOTIFICATION_SERVICE_URL")
	if notifyURL == "" {
		notifyURL = "http://localhost:8085/api/notify"
	}
	baseURL := strings.TrimSuffix(notifyURL, "/api/notify")
	baseURL = strings.TrimSuffix(baseURL, "/")
	botInfoURL := baseURL + "/api/telegram/bot-info"

	resp, err := h.Telegram.Client.Get(botInfoURL)
	if err == nil {
		defer resp.Body.Close()
		var res map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&res); err == nil {
			c.JSON(http.StatusOK, res)
			return
		}
	}

	botUsername := "The_ScreenScout_Bot"
	c.JSON(http.StatusOK, map[string]interface{}{
		"configured":   h.Telegram.BotToken != "",
		"bot_username": "@" + botUsername,
	})
}

// GetNotificationChannel handles GET /api/user/notification-channel
func (h *SubscriptionHandler) GetNotificationChannel(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	ch, err := h.SubRepo.GetNotificationChannel(ctx, userID, "TELEGRAM")
	if err != nil {
		if errors.Is(err, repo.ErrChannelNotFound) {
			c.JSON(http.StatusOK, map[string]interface{}{
				"channel": nil,
			})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"channel": ch,
	})
}

// UpdateNotificationChannel handles POST /api/user/notification-channel
func (h *SubscriptionHandler) UpdateNotificationChannel(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	var req model.UpdateNotificationChannelRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}

	handle := strings.TrimSpace(req.ChannelUserID)
	if handle == "" {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "Telegram handle cannot be empty"})
		return
	}

	channelType := "TELEGRAM"
	if req.ChannelType != "" {
		channelType = req.ChannelType
	}

	isEnabled := true
	if req.IsEnabled != nil {
		isEnabled = *req.IsEnabled
	}

	// Validate Telegram handle format and existence
	if channelType == "TELEGRAM" && isEnabled {
		cleanHandle := strings.TrimPrefix(handle, "@")
		// Check if handle belongs to a known local user
		demoUser, _ := h.UserRepo.GetUserByUsername(ctx, cleanHandle)
		if demoUser == nil {
			validatedHandle, vErr := h.Telegram.ValidateTelegramHandle(ctx, handle)
			if vErr != nil {
				c.JSON(http.StatusBadRequest, map[string]string{
					"error": vErr.Error(),
				})
				return
			}
			handle = validatedHandle
		} else {
			handle = "@" + cleanHandle
		}
	}

	ch, err := h.SubRepo.UpsertNotificationChannel(ctx, userID, channelType, handle, isEnabled)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	// If enabled and handle provided, send welcome confirmation if bot has user's chat_id
	if isEnabled && channelType == "TELEGRAM" {
		username := ""
		if user, uErr := h.UserRepo.GetUserByID(ctx, userID); uErr == nil && user != nil {
			username = user.Username
		}
		welcomeMsg := service.FormatWelcomeMessage(username, handle)
		go func() {
			_, _ = h.Telegram.SendNotification(handle, welcomeMsg)
		}()
	}

	c.JSON(http.StatusOK, ch)
}

// TestNotificationChannel handles POST /api/user/notification-channel/test
func (h *SubscriptionHandler) TestNotificationChannel(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	ch, err := h.SubRepo.GetNotificationChannel(ctx, userID, "TELEGRAM")
	if err != nil || ch == nil || ch.ChannelUserID == "" {
		c.JSON(http.StatusBadRequest, map[string]interface{}{
			"success": false,
			"error":   "No Telegram handle registered. Please save your handle first.",
		})
		return
	}

	username := ""
	if user, uErr := h.UserRepo.GetUserByID(ctx, userID); uErr == nil && user != nil {
		username = user.Username
	}

	cleanUser := strings.TrimPrefix(ch.ChannelUserID, "@")
	displayName := username
	if displayName == "" {
		displayName = cleanUser
	}
	testMessage := fmt.Sprintf("🎬 <b>ScreenScout Test Notification</b>\n\n"+
		"Hello %s (@%s),\n\n"+
		"✅ Your Telegram connection is working perfectly!\n"+
		"You will receive real-time alerts whenever your tracked movie showtimes become available across Singapore cinemas.\n\n"+
		"🍿 Happy movie hunting!", html.EscapeString(displayName), html.EscapeString(cleanUser))

	targetRecipient := ch.ChannelUserID
	if ch.ChatID != nil && *ch.ChatID != 0 {
		targetRecipient = fmt.Sprintf("%d", *ch.ChatID)
	}

	res, sErr := h.Telegram.SendDirectNotification(targetRecipient, testMessage)
	if sErr != nil {
		hint := ""
		if res != nil {
			if hStr, ok := res["hint"].(string); ok {
				hint = hStr
			}
		}
		if hint == "" {
			hint = "Make sure you have started a chat with @The_ScreenScout_Bot by sending /start in Telegram."
		}
		c.JSON(http.StatusOK, map[string]interface{}{
			"success": false,
			"status":  "FAILED",
			"error":   sErr.Error(),
			"hint":    hint,
		})
		return
	}

	status := "SENT"
	if s, ok := res["status"].(string); ok {
		status = s
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"status":  status,
		"message": fmt.Sprintf("Test alert delivered to %s (Status: %s)", ch.ChannelUserID, status),
	})
}

// ListSubscriptions handles GET /api/subscriptions
func (h *SubscriptionHandler) ListSubscriptions(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	subs, err := h.SubRepo.GetSubscriptionsByUserID(ctx, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	if subs == nil {
		subs = []model.Subscription{}
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"subscriptions": subs,
	})
}

// CreateSubscription handles POST /api/subscriptions
func (h *SubscriptionHandler) CreateSubscription(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)
	username := c.GetString("username")

	var req model.CreateSubscriptionRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}

	query := strings.TrimSpace(req.MovieQuery)
	if query == "" {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "movie query cannot be empty"})
		return
	}

	sub, err := h.SubRepo.CreateSubscription(ctx, userID, query)
	if err != nil {
		if errors.Is(err, repo.ErrMaxActiveSubscriptionsReached) {
			c.JSON(http.StatusBadRequest, map[string]string{
				"error": "Maximum active monitoring limit reached (10 tasks). Please pause or cancel an active task first.",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	// Immediate match check! If movies are already in DB, trigger alert immediately
	matchingMovies, err := h.SubRepo.FindMatchingMovies(ctx, query)
	if err == nil && len(matchingMovies) > 0 {
		// Lookup user notification channel
		ch, chErr := h.SubRepo.GetNotificationChannel(ctx, userID, "TELEGRAM")
		recipient := "@" + username
		if chErr == nil && ch != nil {
			if ch.ChatID != nil && *ch.ChatID != 0 {
				recipient = fmt.Sprintf("%d", *ch.ChatID)
			} else if ch.ChannelUserID != "" {
				recipient = ch.ChannelUserID
			}
		}

		msg := service.FormatMovieAlertMessage(username, query, matchingMovies)
		status, _ := h.Telegram.SendNotification(recipient, msg)

		// Mark subscription as triggered with all matched movies
		_ = h.SubRepo.TriggerSubscriptionWithMovies(ctx, sub.ID, matchingMovies, userID, "TELEGRAM", recipient, msg, status)

		// Reload subscription fields
		sub.IsActive = false
		firstID := matchingMovies[0].ID
		firstTitle := matchingMovies[0].Title
		sub.MatchedMovieID = &firstID
		sub.MatchedMovieTitle = &firstTitle
		sub.MatchedMovies = make([]model.MatchedMovieItem, 0, len(matchingMovies))
		for _, m := range matchingMovies {
			posterStr := ""
			if m.PosterURL != nil {
				posterStr = *m.PosterURL
			}
			sub.MatchedMovies = append(sub.MatchedMovies, model.MatchedMovieItem{
				ID:          m.ID,
				Title:       m.Title,
				Provider:    m.Provider,
				Status:      m.Status,
				ReleaseDate: m.ReleaseDate,
				PosterURL:   posterStr,
			})
		}
	}

	c.JSON(http.StatusCreated, sub)
}

// DeleteSubscription handles DELETE /api/subscriptions/:id
func (h *SubscriptionHandler) DeleteSubscription(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	idStr := c.Param("id")
	subID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid subscription id"})
		return
	}

	if err := h.SubRepo.DeleteSubscription(ctx, userID, subID); err != nil {
		if errors.Is(err, repo.ErrSubscriptionNotFound) {
			c.JSON(http.StatusNotFound, map[string]string{"error": "subscription not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, map[string]string{"message": "subscription deleted"})
}

// ToggleSubscription handles POST /api/subscriptions/:id/toggle
func (h *SubscriptionHandler) ToggleSubscription(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	userID := val.(int64)

	idStr := c.Param("id")
	subID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid subscription id"})
		return
	}

	sub, err := h.SubRepo.ToggleSubscription(ctx, userID, subID)
	if err != nil {
		if errors.Is(err, repo.ErrSubscriptionNotFound) {
			c.JSON(http.StatusNotFound, map[string]string{"error": "subscription not found"})
			return
		}
		if errors.Is(err, repo.ErrMaxActiveSubscriptionsReached) {
			c.JSON(http.StatusBadRequest, map[string]string{
				"error": "Maximum active monitoring limit reached (10 tasks). Please pause or cancel an active task first.",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	// If reactivated (is_active is now true), check if matching movies exist in DB and trigger alert
	if sub.IsActive {
		matchingMovies, mErr := h.SubRepo.FindMatchingMovies(ctx, sub.MovieQuery)
		if mErr == nil && len(matchingMovies) > 0 {
			user, _ := h.UserRepo.GetUserByID(ctx, userID)
			username := "User"
			if user != nil {
				username = user.Username
			}

			ch, chErr := h.SubRepo.GetNotificationChannel(ctx, userID, "TELEGRAM")
			recipient := "@" + username
			if chErr == nil && ch != nil {
				if ch.ChatID != nil && *ch.ChatID != 0 {
					recipient = fmt.Sprintf("%d", *ch.ChatID)
				} else if ch.ChannelUserID != "" {
					recipient = ch.ChannelUserID
				}
			}

			msg := service.FormatMovieAlertMessage(username, sub.MovieQuery, matchingMovies)
			status, _ := h.Telegram.SendNotification(recipient, msg)

			_ = h.SubRepo.TriggerSubscriptionWithMovies(ctx, sub.ID, matchingMovies, userID, "TELEGRAM", recipient, msg, status)

			sub.IsActive = false
			firstID := matchingMovies[0].ID
			firstTitle := matchingMovies[0].Title
			sub.MatchedMovieID = &firstID
			sub.MatchedMovieTitle = &firstTitle
			sub.MatchedMovies = make([]model.MatchedMovieItem, 0, len(matchingMovies))
			for _, m := range matchingMovies {
				posterStr := ""
				if m.PosterURL != nil {
					posterStr = *m.PosterURL
				}
				sub.MatchedMovies = append(sub.MatchedMovies, model.MatchedMovieItem{
					ID:          m.ID,
					Title:       m.Title,
					Provider:    m.Provider,
					Status:      m.Status,
					ReleaseDate: m.ReleaseDate,
					PosterURL:   posterStr,
				})
			}
		}
	}

	c.JSON(http.StatusOK, sub)
}

// CheckSubscriptions handles POST /api/subscriptions/check
// Scans all active subscriptions and evaluates them against current movies in the database.
func (h *SubscriptionHandler) CheckSubscriptions(ctx context.Context, c *app.RequestContext) {
	activeSubs, err := h.SubRepo.GetActiveSubscriptions(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	triggeredCount := 0
	for _, sub := range activeSubs {
		matchingMovies, err := h.SubRepo.FindMatchingMovies(ctx, sub.MovieQuery)
		if err != nil || len(matchingMovies) == 0 {
			continue
		}

		// Lookup user
		user, uErr := h.UserRepo.GetUserByID(ctx, sub.UserID)
		username := "User"
		if uErr == nil && user != nil {
			username = user.Username
		}

		// Lookup notification channel
		recipient := "@" + username
		ch, chErr := h.SubRepo.GetNotificationChannel(ctx, sub.UserID, "TELEGRAM")
		if chErr == nil && ch != nil {
			if ch.ChatID != nil && *ch.ChatID != 0 {
				recipient = fmt.Sprintf("%d", *ch.ChatID)
			} else if ch.ChannelUserID != "" {
				recipient = ch.ChannelUserID
			}
		}

		msg := service.FormatMovieAlertMessage(username, sub.MovieQuery, matchingMovies)
		status, _ := h.Telegram.SendNotification(recipient, msg)

		if err := h.SubRepo.TriggerSubscriptionWithMovies(ctx, sub.ID, matchingMovies, sub.UserID, "TELEGRAM", recipient, msg, status); err == nil {
			triggeredCount++
		}
	}

	c.JSON(http.StatusOK, model.SubscriptionCheckResult{
		CheckedCount:   len(activeSubs),
		TriggeredCount: triggeredCount,
	})
}
