package model

import "time"

// MovieStats represents movie inventory metrics.
type MovieStats struct {
	Total        int64 `json:"total"`
	NowShowing   int64 `json:"now_showing"`
	AdvanceSales int64 `json:"advance_sales"`
	ComingSoon   int64 `json:"coming_soon"`
}

// CinemaStats represents cinema coverage and scheduling metrics.
type CinemaStats struct {
	CinemasCount   int64 `json:"cinemas_count"`
	ProvidersCount int64 `json:"providers_count"`
	SchedulesCount int64 `json:"schedules_count"`
}

// UserStats represents platform user metrics.
type UserStats struct {
	TotalUsers  int64 `json:"total_users"`
	AdminCount  int64 `json:"admin_count"`
	MemberCount int64 `json:"member_count"`
}

// ReviewStats represents community review metrics.
type ReviewStats struct {
	TotalReviews  int64   `json:"total_reviews"`
	AverageRating float64 `json:"average_rating"`
}

// SubscriptionStats represents screening tracking job metrics.
type SubscriptionStats struct {
	TotalJobs      int64 `json:"total_jobs"`
	ActiveJobs     int64 `json:"active_jobs"`
	PausedJobs     int64 `json:"paused_jobs"`
	TriggeredCount int64 `json:"triggered_count"`
}

// SystemStatus represents infrastructure and pipeline health status.
type SystemStatus struct {
	DatabaseStatus       string    `json:"database_status"`
	RedisCacheStatus     string    `json:"redis_cache_status"`
	RedisHitRate         float64   `json:"redis_hit_rate"`
	NotificationPipeline string    `json:"notification_pipeline"`
	ServerTime           time.Time `json:"server_time"`
}

// ProviderStat represents movie inventory and cinema coverage broken down per provider.
type ProviderStat struct {
	Code           string `json:"code"` // "GV", "SHAW"
	Name           string `json:"name"` // "Golden Village", "Shaw Theatres"
	TotalMovies    int64  `json:"total_movies"`
	NowShowing     int64  `json:"now_showing"`
	AdvanceSales   int64  `json:"advance_sales"`
	ComingSoon     int64  `json:"coming_soon"`
	CinemasCount   int64  `json:"cinemas_count"`
	SchedulesCount int64  `json:"schedules_count"`
}

// AdminStatsResponse is the combined telemetry response for the admin dashboard.
type AdminStatsResponse struct {
	Movies        MovieStats        `json:"movies"`
	Cinemas       CinemaStats       `json:"cinemas"`
	Providers     []ProviderStat    `json:"providers"`
	Users         UserStats         `json:"users"`
	Reviews       ReviewStats       `json:"reviews"`
	Subscriptions SubscriptionStats `json:"subscriptions"`
	System        SystemStatus      `json:"system"`
}
