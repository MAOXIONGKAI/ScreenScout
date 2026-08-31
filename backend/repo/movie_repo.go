package repo

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/model"
)

// MovieRepo provides database access for movie data with optional Redis caching.
type MovieRepo struct {
	Pool  *pgxpool.Pool
	Cache *cache.MovieCache
}

// NewMovieRepo creates a new MovieRepo.
func NewMovieRepo(pool *pgxpool.Pool) *MovieRepo {
	return &MovieRepo{Pool: pool}
}

// SetCache attaches a MovieCache to the repository.
func (r *MovieRepo) SetCache(c *cache.MovieCache) {
	r.Cache = c
}

// GetCache returns the attached MovieCache (if any).
func (r *MovieRepo) GetCache() *cache.MovieCache {
	return r.Cache
}

// InvalidateMovie purges cache entries for a specific movie and associated listings.
func (r *MovieRepo) InvalidateMovie(ctx context.Context, id int64) error {
	if r.Cache != nil {
		return r.Cache.InvalidateMovie(ctx, id)
	}
	return nil
}

// InvalidateAllMovies purges all movie caches (details and listing queries).
func (r *MovieRepo) InvalidateAllMovies(ctx context.Context) (int64, error) {
	if r.Cache != nil {
		return r.Cache.InvalidateAllMovies(ctx)
	}
	return 0, nil
}

// MovieFilters defines optional query filters.
type MovieFilters struct {
	Provider string
	Branch   string
	Status   string // "now_showing" or "coming_soon"
	Search   string
	TimeFrom string // HH:MM (showtime start >= this)
	TimeTo   string // HH:MM (estimated end time <= this)
	Page     int
	Limit    int
}

// ListMovies returns movies matching the given filters with pagination.
// It checks the Redis cache first, falling back to PostgreSQL on cache miss.
func (r *MovieRepo) ListMovies(ctx context.Context, f MovieFilters) ([]model.Movie, int, error) {
	if f.Page < 1 {
		f.Page = 1
	}
	if f.Limit < 1 || f.Limit > 100 {
		f.Limit = 20
	}

	cacheFilters := cache.MovieListFilters{
		Provider: f.Provider,
		Branch:   f.Branch,
		Status:   f.Status,
		Search:   f.Search,
		TimeFrom: f.TimeFrom,
		TimeTo:   f.TimeTo,
		Page:     f.Page,
		Limit:    f.Limit,
	}

	if r.Cache != nil {
		if cachedMovies, cachedTotal, found, err := r.Cache.GetMovieList(ctx, cacheFilters); found && err == nil {
			return cachedMovies, cachedTotal, nil
		}
	}

	// Build a CTE that tags each movie with has_schedule (boolean)
	// A movie "now_showing" = has at least one future schedule
	// A movie "coming_soon" = release_date > CURRENT_DATE and no future schedules
	// A movie "coming_soon" = release_date > CURRENT_DATE and no future schedules
	baseQuery := `
WITH movie_status AS (
    SELECT
        m.id,
        m.title,
        m.secondary_title,
        m.description,
        m.poster_url,
        m.trailer_url,
        m.website_url,
        m.director,
        m.casts,
        m.genre,
        m.provider,
        m.release_date,
        m.duration,
        m.created_at,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM schedules s
                WHERE s.movie_id = m.id
                  AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
            ) THEN 'now_showing'
            ELSE 'coming_soon'
        END AS status
    FROM movies m
)`

	var conditions []string
	var args []interface{}
	argIdx := 1

	if f.Provider != "" {
		conditions = append(conditions, fmt.Sprintf("ms.provider = $%d", argIdx))
		args = append(args, strings.ToUpper(f.Provider))
		argIdx++
	}

	if f.Search != "" {
		conditions = append(conditions, fmt.Sprintf("ms.title ILIKE $%d", argIdx))
		args = append(args, "%"+f.Search+"%")
		argIdx++
	}

	if f.Status != "" {
		conditions = append(conditions, fmt.Sprintf("ms.status = $%d", argIdx))
		args = append(args, f.Status)
		argIdx++
	}

	if f.Branch != "" {
		// Filter movies that have schedules at a cinema with this branch
		conditions = append(conditions, fmt.Sprintf(`EXISTS (
			SELECT 1 FROM schedules s
			JOIN cinemas c ON c.id = s.cinema_id
			WHERE s.movie_id = ms.id AND c.branch ILIKE $%d
			  AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
		)`, argIdx))
		args = append(args, "%"+f.Branch+"%")
		argIdx++
	}

	if f.TimeFrom != "" || f.TimeTo != "" {
		var schedConds []string
		schedConds = append(schedConds, "s.movie_id = ms.id")
		schedConds = append(schedConds, "(s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))")

		if f.TimeFrom != "" {
			schedConds = append(schedConds, fmt.Sprintf("s.start_time >= $%d::time", argIdx))
			args = append(args, f.TimeFrom)
			argIdx++
		}

		if f.TimeTo != "" {
			schedConds = append(schedConds, fmt.Sprintf("(EXTRACT(EPOCH FROM s.start_time) + ms.duration * 60) <= EXTRACT(EPOCH FROM $%d::time)", argIdx))
			args = append(args, f.TimeTo)
			argIdx++
		}

		conditions = append(conditions, fmt.Sprintf(`EXISTS (
			SELECT 1 FROM schedules s
			WHERE %s
		)`, strings.Join(schedConds, " AND ")))
	}

	whereClause := ""
	if len(conditions) > 0 {
		whereClause = "WHERE " + strings.Join(conditions, " AND ")
	}

	// Count query
	countQuery := fmt.Sprintf(`%s SELECT COUNT(*) FROM movie_status ms %s`, baseQuery, whereClause)
	var total int
	err := r.Pool.QueryRow(ctx, countQuery, args...).Scan(&total)
	if err != nil {
		return nil, 0, fmt.Errorf("count movies: %w", err)
	}

	// Data query with pagination
	offset := (f.Page - 1) * f.Limit
	dataQuery := fmt.Sprintf(`%s
SELECT ms.id, ms.title, ms.secondary_title, ms.description,
       ms.poster_url, ms.trailer_url, ms.website_url,
       ms.director, ms.casts, ms.genre, ms.provider,
       ms.release_date::text, ms.duration, ms.created_at, ms.status
FROM movie_status ms
%s
ORDER BY
    CASE ms.status WHEN 'now_showing' THEN 0 ELSE 1 END,
    ms.release_date DESC,
    ms.title ASC
LIMIT $%d OFFSET $%d`, baseQuery, whereClause, argIdx, argIdx+1)
	args = append(args, f.Limit, offset)

	rows, err := r.Pool.Query(ctx, dataQuery, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("list movies: %w", err)
	}
	defer rows.Close()

	var movies []model.Movie
	for rows.Next() {
		var m model.Movie
		err := rows.Scan(
			&m.ID, &m.Title, &m.SecondaryTitle, &m.Description,
			&m.PosterURL, &m.TrailerURL, &m.WebsiteURL,
			&m.Director, &m.Casts, &m.Genre, &m.Provider,
			&m.ReleaseDate, &m.Duration, &m.CreatedAt, &m.Status,
		)
		if err != nil {
			return nil, 0, fmt.Errorf("scan movie: %w", err)
		}
		movies = append(movies, m)
	}

	if r.Cache != nil {
		_ = r.Cache.SetMovieList(ctx, cacheFilters, movies, total)
	}

	return movies, total, nil
}

// GetMovieByID returns a single movie with its grouped schedules.
// It checks the Redis cache first, falling back to PostgreSQL on cache miss.
func (r *MovieRepo) GetMovieByID(ctx context.Context, id int64) (*model.MovieDetail, error) {
	if r.Cache != nil {
		if cachedDetail, found, err := r.Cache.GetMovieDetail(ctx, id); found && err == nil {
			return cachedDetail, nil
		}
	}

	// Fetch the movie
	movieQuery := `
SELECT m.id, m.title, m.secondary_title, m.description,
       m.poster_url, m.trailer_url, m.website_url,
       m.director, m.casts, m.genre, m.provider,
       m.release_date::text, m.duration, m.created_at,
       CASE
           WHEN EXISTS (
               SELECT 1 FROM schedules s
               WHERE s.movie_id = m.id
                 AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
           ) THEN 'now_showing'
           ELSE 'coming_soon'
       END AS status
FROM movies m
WHERE m.id = $1`

	var m model.Movie
	err := r.Pool.QueryRow(ctx, movieQuery, id).Scan(
		&m.ID, &m.Title, &m.SecondaryTitle, &m.Description,
		&m.PosterURL, &m.TrailerURL, &m.WebsiteURL,
		&m.Director, &m.Casts, &m.Genre, &m.Provider,
		&m.ReleaseDate, &m.Duration, &m.CreatedAt, &m.Status,
	)
	if err != nil {
		return nil, fmt.Errorf("get movie %d: %w", id, err)
	}

	// Fetch future schedules with cinema info
	schedQuery := `
SELECT s.id, s.cinema_id, c.name, c.branch, s.start_date::text, s.start_time::text
FROM schedules s
JOIN cinemas c ON c.id = s.cinema_id
WHERE s.movie_id = $1
  AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
ORDER BY c.name, c.branch, s.start_date, s.start_time`

	rows, err := r.Pool.Query(ctx, schedQuery, id)
	if err != nil {
		return nil, fmt.Errorf("get schedules for movie %d: %w", id, err)
	}
	defer rows.Close()

	// Group schedules by cinema → date
	type rawSched struct {
		ID         int64
		CinemaID   int64
		CinemaName string
		Branch     string
		Date       string
		Time       string
	}

	var rawSchedules []rawSched
	for rows.Next() {
		var rs rawSched
		if err := rows.Scan(&rs.ID, &rs.CinemaID, &rs.CinemaName, &rs.Branch, &rs.Date, &rs.Time); err != nil {
			return nil, fmt.Errorf("scan schedule: %w", err)
		}
		rawSchedules = append(rawSchedules, rs)
	}

	// Group by cinema
	cinemaMap := make(map[int64]*model.CinemaSchedule)
	var cinemaOrder []int64
	for _, rs := range rawSchedules {
		cs, exists := cinemaMap[rs.CinemaID]
		if !exists {
			cs = &model.CinemaSchedule{
				CinemaID:   rs.CinemaID,
				CinemaName: rs.CinemaName,
				Branch:     rs.Branch,
			}
			cinemaMap[rs.CinemaID] = cs
			cinemaOrder = append(cinemaOrder, rs.CinemaID)
		}

		// Find or create date group
		found := false
		for i := range cs.Dates {
			if cs.Dates[i].Date == rs.Date {
				cs.Dates[i].Showtimes = append(cs.Dates[i].Showtimes, model.ScheduleEntry{
					ID:        rs.ID,
					StartTime: rs.Time,
				})
				found = true
				break
			}
		}
		if !found {
			cs.Dates = append(cs.Dates, model.DateSchedule{
				Date: rs.Date,
				Showtimes: []model.ScheduleEntry{
					{ID: rs.ID, StartTime: rs.Time},
				},
			})
		}
	}

	// Build ordered result
	var schedules []model.CinemaSchedule
	for _, cid := range cinemaOrder {
		cs := cinemaMap[cid]
		// Sort dates
		sort.Slice(cs.Dates, func(i, j int) bool {
			return cs.Dates[i].Date < cs.Dates[j].Date
		})
		schedules = append(schedules, *cs)
	}

	detail := &model.MovieDetail{
		Movie:     m,
		Schedules: schedules,
	}

	if r.Cache != nil {
		_ = r.Cache.SetMovieDetail(ctx, id, detail)
	}

	return detail, nil
}
