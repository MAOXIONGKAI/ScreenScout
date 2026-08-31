package model

import "time"

// Movie represents a movie from the database with a computed status field.
type Movie struct {
	ID             int64      `json:"id"`
	Title          string     `json:"title"`
	SecondaryTitle *string    `json:"secondary_title,omitempty"`
	Description    *string    `json:"description,omitempty"`
	PosterURL      *string    `json:"poster_url,omitempty"`
	TrailerURL     *string    `json:"trailer_url,omitempty"`
	WebsiteURL     *string    `json:"website_url,omitempty"`
	Director       *string    `json:"director,omitempty"`
	Casts          *string    `json:"casts,omitempty"`
	Genre          *string    `json:"genre,omitempty"`
	Provider       string     `json:"provider"`
	ReleaseDate    string     `json:"release_date"`
	Duration       int        `json:"duration"`
	CreatedAt      *time.Time `json:"created_at,omitempty"`
	Status         string     `json:"status"` // "now_showing", "advance_sales", or "coming_soon"
}

// Cinema represents a cinema location.
type Cinema struct {
	ID         int64      `json:"id"`
	Name       string     `json:"name"`
	Branch     string     `json:"branch"`
	PostalCode string     `json:"postal_code"`
	Address    *string    `json:"address,omitempty"`
	CreatedAt  *time.Time `json:"created_at,omitempty"`
}

// Schedule represents a single showtime.
type Schedule struct {
	ID        int64  `json:"id"`
	MovieID   int64  `json:"movie_id"`
	CinemaID  int64  `json:"cinema_id"`
	StartDate string `json:"start_date"`
	StartTime string `json:"start_time"`
}

// ScheduleEntry is a showtime within a date group.
type ScheduleEntry struct {
	ID        int64  `json:"id"`
	StartTime string `json:"start_time"`
}

// DateSchedule groups showtimes by date within a cinema.
type DateSchedule struct {
	Date      string          `json:"date"`
	Showtimes []ScheduleEntry `json:"showtimes"`
}

// CinemaSchedule groups schedules by cinema for the detail page.
type CinemaSchedule struct {
	CinemaID   int64          `json:"cinema_id"`
	CinemaName string         `json:"cinema_name"`
	Branch     string         `json:"branch"`
	Dates      []DateSchedule `json:"dates"`
}

// MovieDetail is the full movie detail with grouped schedules.
type MovieDetail struct {
	Movie     Movie            `json:"movie"`
	Schedules []CinemaSchedule `json:"schedules"`
}

// MoviesResponse is the paginated response for movie listing.
type MoviesResponse struct {
	Movies []Movie `json:"movies"`
	Total  int     `json:"total"`
	Page   int     `json:"page"`
	Limit  int     `json:"limit"`
}
