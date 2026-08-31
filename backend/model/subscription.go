package model

import "time"

// MatchedMovieItem represents structured details of a matched movie.
type MatchedMovieItem struct {
	ID          int64  `json:"id"`
	Title       string `json:"title"`
	Provider    string `json:"provider"`
	Status      string `json:"status"`
	ReleaseDate string `json:"release_date"`
	PosterURL   string `json:"poster_url,omitempty"`
}

// NotificationChannel represents a user's notification endpoint (e.g. Telegram).
type NotificationChannel struct {
	ID            int64     `json:"id"`
	UserID        int64     `json:"user_id"`
	ChannelType   string    `json:"channel_type"`    // e.g. "TELEGRAM"
	ChannelUserID string    `json:"channel_user_id"` // e.g. "@username"
	ChatID        *int64    `json:"chat_id,omitempty"`
	IsEnabled     bool      `json:"is_enabled"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// Subscription represents a movie monitoring job.
type Subscription struct {
	ID                int64              `json:"id"`
	UserID            int64              `json:"user_id"`
	MovieQuery        string             `json:"movie_query"`
	IsActive          bool               `json:"is_active"`
	MatchedMovieID    *int64             `json:"matched_movie_id,omitempty"`
	MatchedMovieTitle *string            `json:"matched_movie_title,omitempty"`
	MatchedMovies     []MatchedMovieItem `json:"matched_movies"`
	TriggeredAt       *time.Time         `json:"triggered_at,omitempty"`
	CreatedAt         time.Time          `json:"created_at"`
	UpdatedAt         time.Time          `json:"updated_at"`
}

// NotificationLog represents an audit record of sent notifications.
type NotificationLog struct {
	ID             int64      `json:"id"`
	SubscriptionID *int64     `json:"subscription_id,omitempty"`
	UserID         int64      `json:"user_id"`
	ChannelType    string     `json:"channel_type"`
	Recipient      string     `json:"recipient"`
	Message        string     `json:"message"`
	Status         string     `json:"status"` // "SENT", "SIMULATED", "FAILED"
	IsRead         bool       `json:"is_read"`
	ReadAt         *time.Time `json:"read_at,omitempty"`
	CreatedAt      time.Time  `json:"created_at"`
}

// InAppNotification represents a notification for display in the website UI.
type InAppNotification struct {
	ID                int64              `json:"id"`
	SubscriptionID    *int64             `json:"subscription_id,omitempty"`
	UserID            int64              `json:"user_id"`
	MovieQuery        string             `json:"movie_query"`
	MatchedMovieID    *int64             `json:"matched_movie_id,omitempty"`
	MatchedMovieTitle *string            `json:"matched_movie_title,omitempty"`
	MatchedMovies     []MatchedMovieItem `json:"matched_movies"`
	Message           string             `json:"message"`
	Status            string             `json:"status"`
	IsRead            bool               `json:"is_read"`
	CreatedAt         time.Time          `json:"created_at"`
}

// NotificationsResponse payload returned for website notification center.
type NotificationsResponse struct {
	Notifications []InAppNotification `json:"notifications"`
	UnreadCount   int                 `json:"unread_count"`
	TotalCount    int                 `json:"total_count"`
}

// CreateSubscriptionRequest payload.
type CreateSubscriptionRequest struct {
	MovieQuery string `json:"movie_query"`
}

// UpdateNotificationChannelRequest payload.
type UpdateNotificationChannelRequest struct {
	ChannelType   string `json:"channel_type"`    // default "TELEGRAM"
	ChannelUserID string `json:"channel_user_id"` // e.g. "@telegram_handle"
	IsEnabled     *bool  `json:"is_enabled,omitempty"`
}

// SubscriptionCheckResult summary returned after running a monitor sweep.
type SubscriptionCheckResult struct {
	CheckedCount   int `json:"checked_count"`
	TriggeredCount int `json:"triggered_count"`
}

