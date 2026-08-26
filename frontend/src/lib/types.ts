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
