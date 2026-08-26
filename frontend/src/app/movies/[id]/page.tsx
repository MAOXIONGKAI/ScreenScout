"use client";

import { useState, useEffect } from "react";
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

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchMovieById(id)
      .then(setDetail)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

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

  if (error || !detail) {
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

  const { movie, schedules } = detail;
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
          <h2 className={styles.sectionTitle}>Showtimes</h2>

          {schedules && schedules.length > 0 ? (
            schedules.map((cs) => (
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
              <div className={styles.noSchedulesIcon}>📅</div>
              <p className={styles.noSchedulesText}>
                {movie.status === "coming_soon"
                  ? "Showtimes will be available closer to the release date."
                  : "No upcoming showtimes available."}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
