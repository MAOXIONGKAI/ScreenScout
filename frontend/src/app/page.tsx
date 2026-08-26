"use client";

import { useState, useEffect, useCallback } from "react";
import { Movie } from "@/lib/types";
import { fetchMovies } from "@/lib/api";
import FilterBar from "@/components/FilterBar";
import MovieCard from "@/components/MovieCard";

const LIMIT = 20;

export default function HomePage() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Filters
  const [provider, setProvider] = useState("");
  const [branch, setBranch] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [provider, branch, status, timeFrom, timeTo]);

  const loadMovies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMovies({
        provider,
        branch,
        status,
        search,
        time_from: timeFrom,
        time_to: timeTo,
        page,
        limit: LIMIT,
      });
      setMovies(data.movies || []);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch movies:", err);
      setMovies([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [provider, branch, status, search, timeFrom, timeTo, page]);

  useEffect(() => {
    loadMovies();
  }, [loadMovies]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <>
      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <h1 className="hero-title">Discover Movies</h1>
          <p className="hero-subtitle">
            Real-time showtimes across Singapore&apos;s top cinemas, all in one place.
          </p>

          {/* Search Bar */}
          <div className="search-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search movies by title..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>

          {/* Filter Bar */}
          <FilterBar
            provider={provider}
            branch={branch}
            status={status}
            timeFrom={timeFrom}
            timeTo={timeTo}
            onProviderChange={setProvider}
            onBranchChange={setBranch}
            onStatusChange={setStatus}
            onTimeFromChange={setTimeFrom}
            onTimeToChange={setTimeTo}
          />
        </div>
      </section>

      {/* Movie Grid */}
      <section className="container">
        {/* Results Count */}
        {!loading && (
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "var(--font-size-sm)",
              marginBottom: "var(--space-lg)",
            }}
          >
            {total} movie{total !== 1 ? "s" : ""} found
          </p>
        )}

        {loading ? (
          <div className="movie-grid">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        ) : movies.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🎞️</div>
            <p className="empty-state-text">No movies found</p>
            <p className="empty-state-subtext">
              Try adjusting your filters or search query
            </p>
          </div>
        ) : (
          <div className="movie-grid">
            {movies.map((movie, index) => (
              <MovieCard key={movie.id} movie={movie} index={index} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button
              className="pagination-btn"
              onClick={() => {
                setPage((p) => Math.max(1, p - 1));
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              disabled={page <= 1}
              aria-label="Previous page"
            >
              ← Previous
            </button>

            <div className="pagination-dots">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                <button
                  key={pageNum}
                  className={`pagination-dot ${pageNum === page ? "active" : ""}`}
                  onClick={() => {
                    setPage(pageNum);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  aria-label={`Go to page ${pageNum}`}
                  title={`Page ${pageNum}`}
                >
                  {pageNum}
                </button>
              ))}
            </div>

            <button
              className="pagination-btn"
              onClick={() => {
                setPage((p) => Math.min(totalPages, p + 1));
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              disabled={page >= totalPages}
              aria-label="Next page"
            >
              Next →
            </button>
          </div>
        )}
      </section>
    </>
  );
}
