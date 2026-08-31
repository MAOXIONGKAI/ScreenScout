import Link from "next/link";
import { Movie } from "@/lib/types";
import styles from "./MovieCard.module.css";

interface MovieCardProps {
  movie: Movie;
  index?: number;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function MovieCard({ movie, index = 0 }: MovieCardProps) {
  const statusBadge =
    movie.status === "now_showing" ? (
      <span className="badge badge-showing">Now Showing</span>
    ) : movie.status === "advance_sales" ? (
      <span className="badge badge-advance">Advance Sales</span>
    ) : (
      <span className="badge badge-coming">Coming Soon</span>
    );

  const providerBadge = (
    <span
      className={`badge ${
        movie.provider === "GV" ? "badge-gv" : "badge-shaw"
      }`}
    >
      {movie.provider === "GV" ? "GV" : "SHAW"}
    </span>
  );

  return (
    <Link href={`/movies/${movie.id}`}>
      <div
        className={`${styles.card} fade-in-up`}
        style={{ animationDelay: `${index * 50}ms` }}
      >
        <div className={styles.posterWrapper}>
          {movie.poster_url ? (
            <img
              src={movie.poster_url}
              alt={movie.title}
              className={styles.poster}
              loading="lazy"
            />
          ) : (
            <div className={styles.noPoster}>🎬</div>
          )}
          <div className={styles.posterOverlay} />

          <div className={styles.badges}>
            {providerBadge}
            {statusBadge}
          </div>

          <div className={styles.info}>
            <h3 className={styles.title}>{movie.title}</h3>
            <div className={styles.meta}>
              {movie.genre && (
                <>
                  <span>{movie.genre.split(",")[0].split("/")[0].trim()}</span>
                  <span className={styles.metaDot} />
                </>
              )}
              {movie.duration > 0 && (
                <>
                  <span>{formatDuration(movie.duration)}</span>
                  <span className={styles.metaDot} />
                </>
              )}
              <span>{formatDate(movie.release_date)}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
