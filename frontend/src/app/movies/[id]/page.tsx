"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { MovieDetail } from "@/lib/types";
import { fetchMovieById } from "@/lib/api";
import styles from "./page.module.css";

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-SG", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatScheduleDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-SG", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatTime(timeStr: string): string {
  // Input: "HH:MM:SS" or "HH:MM"
  const parts = timeStr.split(":");
  const h = parseInt(parts[0]);
  const m = parts[1];
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${h12}:${m} ${ampm}`;
}

function getYouTubeEmbedUrl(url: string): string | null {
  try {
    const u = new URL(url);
    let videoId = "";
    if (u.hostname.includes("youtube.com")) {
      videoId = u.searchParams.get("v") || "";
    } else if (u.hostname === "youtu.be") {
      videoId = u.pathname.slice(1);
    }
    return videoId ? `https://www.youtube.com/embed/${videoId}` : null;
  } catch {
    return null;
  }
}

export default function MovieDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [detail, setDetail] = useState<MovieDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Detail Filters State
  const [selectedBranch, setSelectedBranch] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchMovieById(id)
      .then(setDetail)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  const handleResetFilters = () => {
    setSelectedBranch("");
    setSelectedDate("");
    setTimeFrom("");
    setTimeTo("");
  };

  const schedules = detail?.schedules || [];
  const movie = detail?.movie;

  // Extract unique branches
  const branchOptions = useMemo(() => {
    if (!schedules.length) return [];
    const branches = new Set<string>();
    schedules.forEach((cs) => {
      if (cs.branch) branches.add(cs.branch);
    });
    return Array.from(branches).sort();
  }, [schedules]);

  // Extract unique dates
  const dateOptions = useMemo(() => {
    if (!schedules.length) return [];
    const dates = new Set<string>();
    schedules.forEach((cs) => {
      cs.dates.forEach((d) => {
        if (d.date) dates.add(d.date);
      });
    });
    return Array.from(dates).sort();
  }, [schedules]);

  // Helper to convert HH:MM(:SS) to minutes from midnight
  const timeToMinutes = (timeStr: string) => {
    const parts = timeStr.split(":").map(Number);
    return (parts[0] || 0) * 60 + (parts[1] || 0);
  };

  // Filtered schedules computation
  const filteredSchedules = useMemo(() => {
    if (!schedules.length) return [];

    const fromMin = timeFrom ? timeToMinutes(timeFrom) : null;
    const toMin = timeTo ? timeToMinutes(timeTo) : null;
    const duration = movie?.duration || 0;

    return schedules
      .filter((cs) => {
        if (selectedBranch && cs.branch !== selectedBranch) return false;
        return true;
      })
      .map((cs) => {
        const filteredDates = cs.dates
          .filter((ds) => {
            if (selectedDate && ds.date !== selectedDate) return false;
            return true;
          })
          .map((ds) => {
            const filteredShowtimes = ds.showtimes.filter((st) => {
              const startMin = timeToMinutes(st.start_time);
              if (fromMin !== null && startMin < fromMin) {
                return false;
              }
              const endMin = startMin + duration;
              if (toMin !== null && endMin > toMin) {
                return false;
              }
              return true;
            });
            return {
              ...ds,
              showtimes: filteredShowtimes,
            };
          })
          .filter((ds) => ds.showtimes.length > 0);

        return {
          ...cs,
          dates: filteredDates,
        };
      })
      .filter((cs) => cs.dates.length > 0);
  }, [schedules, selectedBranch, selectedDate, timeFrom, timeTo, movie?.duration]);

  const totalMatchingShowtimes = useMemo(() => {
    return filteredSchedules.reduce(
      (sum, cs) => sum + cs.dates.reduce((dSum, ds) => dSum + ds.showtimes.length, 0),
      0
    );
  }, [filteredSchedules]);

  const hasActiveFilters = Boolean(
    selectedBranch || selectedDate || timeFrom || timeTo
  );

  if (loading) {
    return (
      <div className="container">
        <div className={styles.loadingWrapper}>
          <div className={styles.spinner} />
          <p className={styles.loadingText}>Loading movie details…</p>
        </div>
      </div>
    );
  }

  if (error || !detail || !movie) {
    return (
      <div className="container">
        <div className={styles.detailPage}>
          <div className="empty-state">
            <div className="empty-state-icon">😞</div>
            <p className="empty-state-text">Movie not found</p>
            <button className={styles.backBtn} onClick={() => router.push("/")}>
              ← Back to movies
            </button>
          </div>
        </div>
      </div>
    );
  }

  const embedUrl = movie.trailer_url
    ? getYouTubeEmbedUrl(movie.trailer_url)
    : null;

  return (
    <div className="container">
      <div className={styles.detailPage}>
        {/* Back Button */}
        <button className={styles.backBtn} onClick={() => router.push("/")}>
          ← Back to movies
        </button>

        {/* Hero: Poster + Info */}
        <div className={styles.hero}>
          <div className={styles.posterContainer}>
            {movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={movie.title}
                className={styles.poster}
              />
            ) : (
              <div className={styles.noPoster}>🎬</div>
            )}
          </div>

          <div className={styles.info}>
            {/* Badges */}
            <div className={styles.badges}>
              <span
                className={`badge ${
                  movie.provider === "GV" ? "badge-gv" : "badge-shaw"
                }`}
              >
                {movie.provider === "GV" ? "Golden Village" : "Shaw Theatres"}
              </span>
              <span
                className={`badge ${
                  movie.status === "now_showing"
                    ? "badge-showing"
                    : "badge-coming"
                }`}
              >
                {movie.status === "now_showing" ? "Now Showing" : "Coming Soon"}
              </span>
            </div>

            {/* Title */}
            <h1 className={styles.title}>{movie.title}</h1>
            {movie.secondary_title && (
              <p className={styles.secondaryTitle}>{movie.secondary_title}</p>
            )}

            {/* Meta */}
            <div className={styles.meta}>
              {movie.genre && (
                <div className={styles.metaItem}>
                  <span>🎭</span>
                  <span>{movie.genre}</span>
                </div>
              )}
              {movie.duration > 0 && (
                <div className={styles.metaItem}>
                  <span>⏱️</span>
                  <span>{formatDuration(movie.duration)}</span>
                </div>
              )}
              <div className={styles.metaItem}>
                <span>📅</span>
                <span>{formatDate(movie.release_date)}</span>
              </div>
            </div>

            {/* Description */}
            {movie.description && (
              <p className={styles.description}>{movie.description}</p>
            )}

            {/* Cast & Director */}
            {(movie.director || movie.casts) && (
              <div className={styles.castGrid}>
                {movie.director && (
                  <div className={styles.castBlock}>
                    <p className={styles.castLabel}>Director</p>
                    <p className={styles.castValue}>{movie.director}</p>
                  </div>
                )}
                {movie.casts && (
                  <div className={styles.castBlock}>
                    <p className={styles.castLabel}>Cast</p>
                    <p className={styles.castValue}>{movie.casts}</p>
                  </div>
                )}
              </div>
            )}

            {/* Website Link */}
            {movie.website_url && (
              <a
                href={movie.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.websiteLink}
              >
                🔗 View on Official Website
              </a>
            )}
          </div>
        </div>

        {/* Trailer */}
        {embedUrl && (
          <section className={styles.trailerSection}>
            <h2 className={styles.sectionTitle}>Trailer</h2>
            <div className={styles.trailerContainer}>
              <iframe
                src={embedUrl}
                title={`${movie.title} Trailer`}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </section>
        )}

        {/* Schedules */}
        <section className={styles.schedulesSection}>
          <div className={styles.schedulesHeadingRow}>
            <h2 className={styles.sectionTitle}>Showtimes</h2>
            {schedules.length > 0 && (
              <span className={styles.showtimeCountBadge}>
                {totalMatchingShowtimes} showtime
                {totalMatchingShowtimes === 1 ? "" : "s"} available
              </span>
            )}
          </div>

          {/* Showtime Filters Bar */}
          {schedules.length > 0 && (
            <div className={styles.filterSection}>
              {/* Branch Filter */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>Branch</label>
                <select
                  className={styles.select}
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                >
                  <option value="">All Branches ({branchOptions.length})</option>
                  {branchOptions.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date Filter */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>Date</label>
                <select
                  className={styles.select}
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                >
                  <option value="">All Dates ({dateOptions.length})</option>
                  {dateOptions.map((d) => (
                    <option key={d} value={d}>
                      {formatScheduleDate(d)} ({d})
                    </option>
                  ))}
                </select>
              </div>

              {/* Showtime From */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>Showtime From</label>
                <input
                  type="time"
                  className={styles.timeInput}
                  value={timeFrom}
                  onChange={(e) => setTimeFrom(e.target.value)}
                />
              </div>

              {/* Estimated End Time Until */}
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>Showtime Until</label>
                <input
                  type="time"
                  className={styles.timeInput}
                  value={timeTo}
                  onChange={(e) => setTimeTo(e.target.value)}
                />
              </div>

              {/* Reset Filters Button */}
              {hasActiveFilters && (
                <button
                  type="button"
                  className={styles.resetBtn}
                  onClick={handleResetFilters}
                  title="Reset all showtime filters"
                >
                  ✕ Reset Filters
                </button>
              )}
            </div>
          )}

          {filteredSchedules.length > 0 ? (
            filteredSchedules.map((cs) => (
              <div key={cs.cinema_id} className={styles.cinemaSchedule}>
                <div className={styles.cinemaHeader}>
                  <span className={styles.cinemaName}>{cs.cinema_name}</span>
                  <span className={styles.cinemaBranch}>{cs.branch}</span>
                </div>

                {cs.dates.map((ds) => (
                  <div key={ds.date} className={styles.dateGroup}>
                    <p className={styles.dateLabel}>
                      {formatScheduleDate(ds.date)}
                    </p>
                    <div className={styles.showtimes}>
                      {ds.showtimes.map((st) => (
                        <span key={st.id} className={styles.showtimePill}>
                          {formatTime(st.start_time)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div className={styles.noSchedules}>
              <div className={styles.noSchedulesIcon}>
                {hasActiveFilters ? "🔍" : "📅"}
              </div>
              <p className={styles.noSchedulesText}>
                {hasActiveFilters
                  ? "No showtimes match the selected branch, date, or time range."
                  : movie.status === "coming_soon"
                  ? "Showtimes will be available closer to the release date."
                  : "No upcoming showtimes available."}
              </p>
              {hasActiveFilters && (
                <button
                  className={styles.resetFiltersActionBtn}
                  onClick={handleResetFilters}
                >
                  Clear Filters
                </button>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
