package repo

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/model"
)

var (
	ErrSubscriptionNotFound           = errors.New("subscription not found")
	ErrChannelNotFound                = errors.New("notification channel not found")
	ErrMaxActiveSubscriptionsReached  = errors.New("maximum active monitoring limit reached (10 tasks)")
	sgtZone                           = time.FixedZone("SGT", 8*3600)
)

// SubscriptionRepo handles database operations for notification channels and subscriptions.
type SubscriptionRepo struct {
	Pool *pgxpool.Pool
}

// NewSubscriptionRepo creates a new SubscriptionRepo.
func NewSubscriptionRepo(pool *pgxpool.Pool) *SubscriptionRepo {
	return &SubscriptionRepo{Pool: pool}
}

// EnsureSubscriptionTables creates the necessary tables for subscriptions if not exists.
func (r *SubscriptionRepo) EnsureSubscriptionTables(ctx context.Context) error {
	query := `
	CREATE TABLE IF NOT EXISTS notification_channels (
		id                  BIGINT PRIMARY KEY,
		user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
		channel_type        VARCHAR(20) NOT NULL CHECK (
								channel_type IN ('TELEGRAM', 'WECHAT', 'WHATSAPP', 'EMAIL', 'DISCORD')
							),
		channel_user_id     VARCHAR(255) NOT NULL,
		chat_id             BIGINT,
		is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
		created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
		updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
		UNIQUE (user_id, channel_type)
	);

	ALTER TABLE notification_channels ADD COLUMN IF NOT EXISTS chat_id BIGINT;

	CREATE SEQUENCE IF NOT EXISTS notification_channels_id_seq START WITH 1 INCREMENT BY 1;
	ALTER TABLE notification_channels ALTER COLUMN id SET DEFAULT nextval('notification_channels_id_seq');

	CREATE INDEX IF NOT EXISTS idx_notification_channels_user ON notification_channels(user_id);

	CREATE TABLE IF NOT EXISTS telegram_users (
		username    VARCHAR(255) PRIMARY KEY,
		chat_id     BIGINT NOT NULL,
		first_name  VARCHAR(255),
		updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
	);

	-- Dynamic link: only set chat_id for each user matching their own Telegram username
	UPDATE notification_channels nc
	SET chat_id = tu.chat_id
	FROM telegram_users tu
	WHERE LOWER(TRIM(LEADING '@' FROM nc.channel_user_id)) = LOWER(tu.username)
	  AND nc.channel_type = 'TELEGRAM';

	CREATE TABLE IF NOT EXISTS subscriptions (
		id                  BIGINT PRIMARY KEY,
		user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
		movie_query         VARCHAR(255) NOT NULL,
		is_active           BOOLEAN NOT NULL DEFAULT TRUE,
		matched_movie_id    BIGINT REFERENCES movies(id) ON DELETE SET NULL,
		matched_movie_title VARCHAR(255),
		matched_movies      JSONB DEFAULT '[]'::jsonb,
		triggered_at        TIMESTAMPTZ,
		created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
		updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
	);

	ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS matched_movies JSONB DEFAULT '[]'::jsonb;

	CREATE SEQUENCE IF NOT EXISTS subscriptions_id_seq START WITH 1 INCREMENT BY 1;
	ALTER TABLE subscriptions ALTER COLUMN id SET DEFAULT nextval('subscriptions_id_seq');

	CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
	CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);


	CREATE TABLE IF NOT EXISTS notification_logs (
		id                  BIGINT PRIMARY KEY,
		subscription_id     BIGINT REFERENCES subscriptions(id) ON DELETE CASCADE,
		user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
		channel_type        VARCHAR(20) NOT NULL,
		recipient           VARCHAR(255) NOT NULL,
		message             TEXT NOT NULL,
		status              VARCHAR(20) NOT NULL DEFAULT 'SENT',
		created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
	);

	CREATE SEQUENCE IF NOT EXISTS notification_logs_id_seq START WITH 1 INCREMENT BY 1;
	ALTER TABLE notification_logs ALTER COLUMN id SET DEFAULT nextval('notification_logs_id_seq');

	CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON notification_logs(user_id);
	`
	_, err := r.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("ensure subscription tables: %w", err)
	}
	return nil
}

// GetNotificationChannel retrieves a user's notification channel.
func (r *SubscriptionRepo) GetNotificationChannel(ctx context.Context, userID int64, channelType string) (*model.NotificationChannel, error) {
	query := `
		SELECT id, user_id, channel_type, channel_user_id, chat_id, is_enabled, created_at, updated_at
		FROM notification_channels
		WHERE user_id = $1 AND channel_type = $2
		LIMIT 1
	`

	var ch model.NotificationChannel
	err := r.Pool.QueryRow(ctx, query, userID, strings.ToUpper(channelType)).Scan(
		&ch.ID,
		&ch.UserID,
		&ch.ChannelType,
		&ch.ChannelUserID,
		&ch.ChatID,
		&ch.IsEnabled,
		&ch.CreatedAt,
		&ch.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrChannelNotFound
		}
		return nil, fmt.Errorf("get notification channel: %w", err)
	}

	ch.CreatedAt = ch.CreatedAt.In(sgtZone)
	ch.UpdatedAt = ch.UpdatedAt.In(sgtZone)
	return &ch, nil
}

// UpsertNotificationChannel sets or updates a user's notification handle (e.g. Telegram).
func (r *SubscriptionRepo) UpsertNotificationChannel(ctx context.Context, userID int64, channelType, channelUserID string, isEnabled bool) (*model.NotificationChannel, error) {
	channelUserID = strings.TrimSpace(channelUserID)
	cleanName := strings.ToLower(strings.TrimPrefix(channelUserID, "@"))

	var explicitChatID *int64
	// Check if numeric
	if numID, err := strconv.ParseInt(channelUserID, 10, 64); err == nil {
		explicitChatID = &numID
	} else {
		// Lookup from telegram_users
		var dbChatID int64
		if err := r.Pool.QueryRow(ctx, `SELECT chat_id FROM telegram_users WHERE username = $1`, cleanName).Scan(&dbChatID); err == nil {
			explicitChatID = &dbChatID
		}
		if channelType == "TELEGRAM" && !strings.HasPrefix(channelUserID, "@") && !strings.HasPrefix(channelUserID, "-") {
			channelUserID = "@" + channelUserID
		}
	}

	query := `
		INSERT INTO notification_channels (user_id, channel_type, channel_user_id, chat_id, is_enabled, updated_at)
		VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
		ON CONFLICT (user_id, channel_type)
		DO UPDATE SET
			channel_user_id = EXCLUDED.channel_user_id,
			chat_id = EXCLUDED.chat_id,
			is_enabled = EXCLUDED.is_enabled,
			updated_at = CURRENT_TIMESTAMP
		RETURNING id, user_id, channel_type, channel_user_id, chat_id, is_enabled, created_at, updated_at
	`

	var ch model.NotificationChannel
	err := r.Pool.QueryRow(ctx, query, userID, strings.ToUpper(channelType), channelUserID, explicitChatID, isEnabled).Scan(
		&ch.ID,
		&ch.UserID,
		&ch.ChannelType,
		&ch.ChannelUserID,
		&ch.ChatID,
		&ch.IsEnabled,
		&ch.CreatedAt,
		&ch.UpdatedAt,
	)

	if err != nil {
		return nil, fmt.Errorf("upsert notification channel: %w", err)
	}

	ch.CreatedAt = ch.CreatedAt.In(sgtZone)
	ch.UpdatedAt = ch.UpdatedAt.In(sgtZone)
	return &ch, nil
}

// CreateSubscription inserts a new movie subscription monitoring job.
func (r *SubscriptionRepo) CreateSubscription(ctx context.Context, userID int64, movieQuery string) (*model.Subscription, error) {
	// Safety net: check active count limit (max 10 active monitoring tasks per user)
	var activeCount int
	if err := r.Pool.QueryRow(ctx, `SELECT COUNT(*) FROM subscriptions WHERE user_id = $1 AND is_active = TRUE`, userID).Scan(&activeCount); err != nil {
		return nil, fmt.Errorf("count active subscriptions: %w", err)
	}
	if activeCount >= 10 {
		return nil, ErrMaxActiveSubscriptionsReached
	}

	query := `
		INSERT INTO subscriptions (user_id, movie_query, is_active, matched_movies)
		VALUES ($1, $2, TRUE, '[]'::jsonb)
		RETURNING id, user_id, movie_query, is_active, matched_movie_id, matched_movie_title, matched_movies, triggered_at, created_at, updated_at
	`

	var sub model.Subscription
	var matchedMoviesJSON []byte
	err := r.Pool.QueryRow(ctx, query, userID, strings.TrimSpace(movieQuery)).Scan(
		&sub.ID,
		&sub.UserID,
		&sub.MovieQuery,
		&sub.IsActive,
		&sub.MatchedMovieID,
		&sub.MatchedMovieTitle,
		&matchedMoviesJSON,
		&sub.TriggeredAt,
		&sub.CreatedAt,
		&sub.UpdatedAt,
	)

	if err != nil {
		return nil, fmt.Errorf("create subscription: %w", err)
	}

	sub.MatchedMovies = []model.MatchedMovieItem{}
	if len(matchedMoviesJSON) > 0 {
		_ = json.Unmarshal(matchedMoviesJSON, &sub.MatchedMovies)
	}

	sub.CreatedAt = sub.CreatedAt.In(sgtZone)
	sub.UpdatedAt = sub.UpdatedAt.In(sgtZone)
	if sub.TriggeredAt != nil {
		t := sub.TriggeredAt.In(sgtZone)
		sub.TriggeredAt = &t
	}
	return &sub, nil
}

// GetSubscriptionsByUserID returns all subscriptions for a specific user.
func (r *SubscriptionRepo) GetSubscriptionsByUserID(ctx context.Context, userID int64) ([]model.Subscription, error) {
	query := `
		SELECT id, user_id, movie_query, is_active, matched_movie_id, matched_movie_title, COALESCE(matched_movies, '[]'::jsonb), triggered_at, created_at, updated_at
		FROM subscriptions
		WHERE user_id = $1
		ORDER BY is_active DESC, updated_at DESC
	`

	rows, err := r.Pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("get subscriptions: %w", err)
	}
	defer rows.Close()

	var subs []model.Subscription
	for rows.Next() {
		var sub model.Subscription
		var matchedMoviesJSON []byte
		if err := rows.Scan(
			&sub.ID,
			&sub.UserID,
			&sub.MovieQuery,
			&sub.IsActive,
			&sub.MatchedMovieID,
			&sub.MatchedMovieTitle,
			&matchedMoviesJSON,
			&sub.TriggeredAt,
			&sub.CreatedAt,
			&sub.UpdatedAt,
		); err != nil {
			return nil, err
		}

		sub.MatchedMovies = []model.MatchedMovieItem{}
		if len(matchedMoviesJSON) > 0 {
			_ = json.Unmarshal(matchedMoviesJSON, &sub.MatchedMovies)
		}

		// Backwards compatibility: if matched_movies is empty but matched_movie_id exists
		if len(sub.MatchedMovies) == 0 && sub.MatchedMovieID != nil && sub.MatchedMovieTitle != nil {
			sub.MatchedMovies = []model.MatchedMovieItem{
				{
					ID:       *sub.MatchedMovieID,
					Title:    *sub.MatchedMovieTitle,
					Provider: "GV / Shaw",
					Status:   "now_showing",
				},
			}
		}

		sub.CreatedAt = sub.CreatedAt.In(sgtZone)
		sub.UpdatedAt = sub.UpdatedAt.In(sgtZone)
		if sub.TriggeredAt != nil {
			t := sub.TriggeredAt.In(sgtZone)
			sub.TriggeredAt = &t
		}
		subs = append(subs, sub)
	}

	return subs, nil
}

// GetActiveSubscriptions retrieves all active subscription jobs for the monitoring worker.
func (r *SubscriptionRepo) GetActiveSubscriptions(ctx context.Context) ([]model.Subscription, error) {
	query := `
		SELECT id, user_id, movie_query, is_active, matched_movie_id, matched_movie_title, COALESCE(matched_movies, '[]'::jsonb), triggered_at, created_at, updated_at
		FROM subscriptions
		WHERE is_active = TRUE
		ORDER BY created_at ASC
	`

	rows, err := r.Pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("get active subscriptions: %w", err)
	}
	defer rows.Close()

	var subs []model.Subscription
	for rows.Next() {
		var sub model.Subscription
		var matchedMoviesJSON []byte
		if err := rows.Scan(
			&sub.ID,
			&sub.UserID,
			&sub.MovieQuery,
			&sub.IsActive,
			&sub.MatchedMovieID,
			&sub.MatchedMovieTitle,
			&matchedMoviesJSON,
			&sub.TriggeredAt,
			&sub.CreatedAt,
			&sub.UpdatedAt,
		); err != nil {
			return nil, err
		}

		sub.MatchedMovies = []model.MatchedMovieItem{}
		if len(matchedMoviesJSON) > 0 {
			_ = json.Unmarshal(matchedMoviesJSON, &sub.MatchedMovies)
		}

		sub.CreatedAt = sub.CreatedAt.In(sgtZone)
		sub.UpdatedAt = sub.UpdatedAt.In(sgtZone)
		subs = append(subs, sub)
	}

	return subs, nil
}

// FindMatchingMovies checks if any movies in the database match the movie query substring.
func (r *SubscriptionRepo) FindMatchingMovies(ctx context.Context, movieQuery string) ([]model.Movie, error) {
	trimmed := strings.TrimSpace(movieQuery)
	if trimmed == "" {
		return nil, nil
	}

	pattern := "%" + strings.ToLower(trimmed) + "%"
	query := `
		SELECT id, title, secondary_title, description, poster_url, trailer_url, website_url, director, casts, genre, provider, release_date, duration,
		       CASE
		           WHEN EXISTS (
		               SELECT 1 FROM schedules s
		               WHERE s.movie_id = movies.id
		                 AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
		           ) AND release_date > CURRENT_DATE THEN 'advance_sales'
		           WHEN EXISTS (
		               SELECT 1 FROM schedules s
		               WHERE s.movie_id = movies.id
		                 AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
		           ) THEN 'now_showing'
		           ELSE 'coming_soon'
		       END AS status
		FROM movies
		WHERE LOWER(title) LIKE $1 OR LOWER(COALESCE(secondary_title, '')) LIKE $1
		ORDER BY release_date DESC
		LIMIT 10
	`

	rows, err := r.Pool.Query(ctx, query, pattern)
	if err != nil {
		return nil, fmt.Errorf("find matching movies: %w", err)
	}
	defer rows.Close()

	var movies []model.Movie
	for rows.Next() {
		var m model.Movie
		if err := rows.Scan(
			&m.ID,
			&m.Title,
			&m.SecondaryTitle,
			&m.Description,
			&m.PosterURL,
			&m.TrailerURL,
			&m.WebsiteURL,
			&m.Director,
			&m.Casts,
			&m.Genre,
			&m.Provider,
			&m.ReleaseDate,
			&m.Duration,
			&m.Status,
		); err != nil {
			return nil, err
		}
		movies = append(movies, m)
	}

	return movies, nil
}

// TriggerSubscriptionWithMovies marks a subscription as triggered with multiple matched movies, sets is_active = FALSE, and logs the notification.
func (r *SubscriptionRepo) TriggerSubscriptionWithMovies(
	ctx context.Context,
	subID int64,
	movies []model.Movie,
	userID int64,
	channelType, recipient, message, status string,
) error {
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	if len(movies) == 0 {
		return nil
	}

	var primaryID int64 = movies[0].ID
	primaryTitle := movies[0].Title

	// Build structured list of items
	items := make([]model.MatchedMovieItem, 0, len(movies))
	titles := make([]string, 0, len(movies))
	for _, m := range movies {
		posterStr := ""
		if m.PosterURL != nil {
			posterStr = *m.PosterURL
		}
		items = append(items, model.MatchedMovieItem{
			ID:          m.ID,
			Title:       m.Title,
			Provider:    m.Provider,
			Status:      m.Status,
			ReleaseDate: m.ReleaseDate,
			PosterURL:   posterStr,
		})
		titles = append(titles, m.Title)
	}

	itemsJSON, err := json.Marshal(items)
	if err != nil {
		itemsJSON = []byte("[]")
	}

	summaryTitle := primaryTitle
	if len(titles) > 1 {
		summaryTitle = fmt.Sprintf("%s (+%d more)", primaryTitle, len(titles)-1)
	}

	// 1. Update subscription status
	updateQuery := `
		UPDATE subscriptions
		SET is_active = FALSE,
		    matched_movie_id = $1,
		    matched_movie_title = $2,
		    matched_movies = $3,
		    triggered_at = CURRENT_TIMESTAMP,
		    updated_at = CURRENT_TIMESTAMP
		WHERE id = $4
	`
	if _, err := tx.Exec(ctx, updateQuery, primaryID, summaryTitle, itemsJSON, subID); err != nil {
		return fmt.Errorf("update subscription triggered: %w", err)
	}

	// 2. Insert notification log
	logQuery := `
		INSERT INTO notification_logs (subscription_id, user_id, channel_type, recipient, message, status)
		VALUES ($1, $2, $3, $4, $5, $6)
	`
	if _, err := tx.Exec(ctx, logQuery, subID, userID, channelType, recipient, message, status); err != nil {
		return fmt.Errorf("insert notification log: %w", err)
	}

	return tx.Commit(ctx)
}

// ToggleSubscription toggles an active/inactive subscription.
func (r *SubscriptionRepo) ToggleSubscription(ctx context.Context, userID, subID int64) (*model.Subscription, error) {
	// First check current status
	var currentIsActive bool
	err := r.Pool.QueryRow(ctx, `SELECT is_active FROM subscriptions WHERE id = $1 AND user_id = $2`, subID, userID).Scan(&currentIsActive)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrSubscriptionNotFound
		}
		return nil, fmt.Errorf("check subscription status: %w", err)
	}

	// If currently inactive, activating it will increase active count. Check limit!
	if !currentIsActive {
		var activeCount int
		if err := r.Pool.QueryRow(ctx, `SELECT COUNT(*) FROM subscriptions WHERE user_id = $1 AND is_active = TRUE`, userID).Scan(&activeCount); err != nil {
			return nil, fmt.Errorf("count active subscriptions: %w", err)
		}
		if activeCount >= 10 {
			return nil, ErrMaxActiveSubscriptionsReached
		}
	}

	query := `
		UPDATE subscriptions
		SET is_active = NOT is_active,
		    triggered_at = CASE WHEN NOT is_active = TRUE THEN NULL ELSE triggered_at END,
		    matched_movie_id = CASE WHEN NOT is_active = TRUE THEN NULL ELSE matched_movie_id END,
		    matched_movie_title = CASE WHEN NOT is_active = TRUE THEN NULL ELSE matched_movie_title END,
		    matched_movies = CASE WHEN NOT is_active = TRUE THEN '[]'::jsonb ELSE matched_movies END,
		    updated_at = CURRENT_TIMESTAMP
		WHERE id = $1 AND user_id = $2
		RETURNING id, user_id, movie_query, is_active, matched_movie_id, matched_movie_title, COALESCE(matched_movies, '[]'::jsonb), triggered_at, created_at, updated_at
	`

	var sub model.Subscription
	var matchedMoviesJSON []byte
	err = r.Pool.QueryRow(ctx, query, subID, userID).Scan(
		&sub.ID,
		&sub.UserID,
		&sub.MovieQuery,
		&sub.IsActive,
		&sub.MatchedMovieID,
		&sub.MatchedMovieTitle,
		&matchedMoviesJSON,
		&sub.TriggeredAt,
		&sub.CreatedAt,
		&sub.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrSubscriptionNotFound
		}
		return nil, fmt.Errorf("toggle subscription: %w", err)
	}

	sub.MatchedMovies = []model.MatchedMovieItem{}
	if len(matchedMoviesJSON) > 0 {
		_ = json.Unmarshal(matchedMoviesJSON, &sub.MatchedMovies)
	}

	sub.CreatedAt = sub.CreatedAt.In(sgtZone)
	sub.UpdatedAt = sub.UpdatedAt.In(sgtZone)
	if sub.TriggeredAt != nil {
		t := sub.TriggeredAt.In(sgtZone)
		sub.TriggeredAt = &t
	}
	return &sub, nil
}

// DeleteSubscription removes a user's subscription.
func (r *SubscriptionRepo) DeleteSubscription(ctx context.Context, userID, subID int64) error {
	query := `DELETE FROM subscriptions WHERE id = $1 AND user_id = $2`
	tag, err := r.Pool.Exec(ctx, query, subID, userID)
	if err != nil {
		return fmt.Errorf("delete subscription: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrSubscriptionNotFound
	}
	return nil
}
