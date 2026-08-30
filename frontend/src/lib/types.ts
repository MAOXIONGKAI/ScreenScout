// Movie represents a movie from the API.
export interface Movie {
  id: number;
  title: string;
  secondary_title?: string;
  description?: string;
  poster_url?: string;
  trailer_url?: string;
  website_url?: string;
  director?: string;
  casts?: string;
  genre?: string;
  provider: string;
  release_date: string;
  duration: number;
  status: string; // "now_showing" | "coming_soon"
}

// Cinema represents a cinema location.
export interface Cinema {
  id: number;
  name: string;
  branch: string;
  postal_code: string;
  address?: string;
}

// ScheduleEntry is a single showtime.
export interface ScheduleEntry {
  id: number;
  start_time: string;
}

// DateSchedule groups showtimes by date.
export interface DateSchedule {
  date: string;
  showtimes: ScheduleEntry[];
}

// CinemaSchedule groups schedules by cinema.
export interface CinemaSchedule {
  cinema_id: number;
  cinema_name: string;
  branch: string;
  dates: DateSchedule[];
}

// MovieDetail is the full movie detail with schedules.
export interface MovieDetail {
  movie: Movie;
  schedules: CinemaSchedule[];
}

// MoviesResponse is the paginated movies list response.
export interface MoviesResponse {
  movies: Movie[];
  total: number;
  page: number;
  limit: number;
}

// User represents the authenticated user profile.
export interface User {
  id: number;
  username: string;
  role?: "user" | "admin";
  created_at: string;
}

// Admin stats telemetry interfaces
export interface MovieStats {
  total: number;
  now_showing: number;
  coming_soon: number;
}

export interface CinemaStats {
  cinemas_count: number;
  providers_count: number;
  schedules_count: number;
}

export interface UserStats {
  total_users: number;
  admin_count: number;
  member_count: number;
}

export interface ReviewStats {
  total_reviews: number;
  average_rating: number;
}

export interface SubscriptionStats {
  total_jobs: number;
  active_jobs: number;
  paused_jobs: number;
  triggered_count: number;
}

export interface SystemStatus {
  database_status: string;
  redis_cache_status: string;
  redis_hit_rate: number;
  notification_pipeline: string;
  server_time: string;
}

export interface ProviderStat {
  code: string;
  name: string;
  total_movies: number;
  now_showing: number;
  coming_soon: number;
  cinemas_count: number;
  schedules_count: number;
}

export interface AdminStatsResponse {
  movies: MovieStats;
  cinemas: CinemaStats;
  providers: ProviderStat[];
  users: UserStats;
  reviews: ReviewStats;
  subscriptions: SubscriptionStats;
  system: SystemStatus;
}

// AuthResponse is returned on successful login / registration.
export interface AuthResponse {
  token: string;
  user: User;
}

// LoginPayload for POST /api/auth/login
export interface LoginPayload {
  username: string;
  password: string;
}

// RegisterPayload for POST /api/auth/register
export interface RegisterPayload {
  username: string;
  password: string;
}

// NotificationChannel represents a registered alert channel (Telegram)
export interface NotificationChannel {
  id: number;
  user_id: number;
  channel_type: string;
  channel_user_id: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// MatchedMovieItem represents a single movie matched by a subscription
export interface MatchedMovieItem {
  id: number;
  title: string;
  provider: string;
  status: string;
  release_date: string;
  poster_url?: string;
}

// Subscription represents a movie monitoring subscription job
export interface Subscription {
  id: number;
  user_id: number;
  movie_query: string;
  is_active: boolean;
  matched_movie_id?: number;
  matched_movie_title?: string;
  matched_movies?: MatchedMovieItem[];
  triggered_at?: string;
  created_at: string;
  updated_at: string;
}

// Review represents a user review and rating for a movie
export interface Review {
  id: number;
  movie_id: number;
  user_id: number;
  username: string;
  rating: number; // 1 - 5
  content: string;
  created_at: string;
  updated_at: string;
}

// CreateReviewPayload for POST /api/movies/:id/reviews
export interface CreateReviewPayload {
  rating: number;
  content: string;
}

// MovieReviewsResponse wraps paginated reviews list and aggregate metrics
export interface MovieReviewsResponse {
  reviews: Review[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  average_rating: number;
  rating_counts: Record<string, number>;
}

// ScrapeResponse represents the response from triggering a manual scrape pass
export interface ScrapeResponse {
  success: boolean;
  message: string;
  duration_ms?: number;
  flushed_keys_count?: number;
}


