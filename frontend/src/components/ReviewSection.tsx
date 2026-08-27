"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Review, MovieReviewsResponse } from "@/lib/types";
import { fetchMovieReviews, submitMovieReview, deleteMovieReview } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import styles from "./ReviewSection.module.css";

interface ReviewSectionProps {
  movieId: number;
}

const RATING_MEANINGS: Record<number, string> = {
  1: "Terrible 😞",
  2: "Poor 😕",
  3: "Average 😐",
  4: "Great! 😊",
  5: "Masterpiece! 🤩",
};

const ITEMS_PER_PAGE = 5;

function formatReviewDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 2) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return d.toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function getPageNumbers(currentPage: number, totalPages: number): (number | string)[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | string)[] = [1];

  if (currentPage > 3) {
    pages.push("...");
  }

  const start = Math.max(2, currentPage - 1);
  const end = Math.min(totalPages - 1, currentPage + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (currentPage < totalPages - 2) {
    pages.push("...");
  }

  pages.push(totalPages);
  return pages;
}

export function ReviewSection({ movieId }: ReviewSectionProps) {
  const { user, token, openAuthModal } = useAuth();

  const [reviewsData, setReviewsData] = useState<MovieReviewsResponse>({
    reviews: [],
    total: 0,
    page: 1,
    limit: ITEMS_PER_PAGE,
    total_pages: 0,
    average_rating: 0,
    rating_counts: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
  });
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [page, setPage] = useState(1);

  // Form State
  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [content, setContent] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reset to page 1 on movieId change
  useEffect(() => {
    setPage(1);
  }, [movieId]);

  // Load reviews for current page
  const loadReviews = useCallback(async (pageToLoad: number = page) => {
    if (!movieId) return;
    try {
      setLoading(true);
      const data = await fetchMovieReviews(movieId, pageToLoad, ITEMS_PER_PAGE);
      setReviewsData(data);
    } catch (err: any) {
      console.error("Failed to load reviews:", err);
    } finally {
      setLoading(false);
    }
  }, [movieId, page]);

  useEffect(() => {
    loadReviews(page);
  }, [loadReviews, page]);

  // Check if current user has already written a review
  const userReview = useMemo(() => {
    if (!user || !reviewsData.reviews.length) return null;
    return reviewsData.reviews.find((r) => r.user_id === user.id) || null;
  }, [user, reviewsData.reviews]);

  // Populate form if user has an existing review on current view
  useEffect(() => {
    if (userReview) {
      setRating(userReview.rating);
      setContent(userReview.content);
    } else if (!submitting && !content) {
      setRating(5);
    }
  }, [userReview]);

  const activeRating = hoverRating !== null ? hoverRating : rating;

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || (reviewsData.total_pages && newPage > reviewsData.total_pages)) {
      return;
    }
    setPage(newPage);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      openAuthModal("login");
      return;
    }

    if (!rating || rating < 1 || rating > 5) {
      setErrorMessage("Please select a rating from 1 to 5 stars.");
      return;
    }

    if (!content.trim()) {
      setErrorMessage("Please write a review comment before submitting.");
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);
      await submitMovieReview(token, movieId, {
        rating,
        content: content.trim(),
      });
      // Refresh current page
      await loadReviews(page);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to submit review. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (reviewId: number) => {
    if (!token) return;
    if (!window.confirm("Are you sure you want to delete your review?")) {
      return;
    }

    try {
      setSubmitting(true);
      await deleteMovieReview(token, movieId, reviewId);
      setContent("");
      setRating(5);
      await loadReviews(page);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to delete review.");
    } finally {
      setSubmitting(false);
    }
  };

  const totalReviews = reviewsData.total;
  const avgRating = reviewsData.average_rating;
  const totalPages = reviewsData.total_pages || (totalReviews > 0 ? Math.ceil(totalReviews / ITEMS_PER_PAGE) : 0);
  const pageNumbers = useMemo(() => getPageNumbers(page, totalPages), [page, totalPages]);

  return (
    <section
      className={`${styles.reviewsSection} ${
        isCollapsed ? styles.reviewsSectionCollapsed : ""
      }`}
    >
      {/* Header with collapse toggle */}
      <div
        className={styles.sectionHeader}
        onClick={() => setIsCollapsed(!isCollapsed)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsCollapsed(!isCollapsed);
          }
        }}
        title={
          isCollapsed
            ? "Click to expand audience reviews"
            : "Click to collapse audience reviews"
        }
        aria-expanded={!isCollapsed}
      >
        <div className={styles.sectionTitleRow}>
          <h2 className={styles.sectionTitle}>💬 Audience Reviews & Ratings</h2>
          <span className={styles.reviewCountBadge}>
            {totalReviews} {totalReviews === 1 ? "review" : "reviews"}
          </span>
        </div>

        <div className={styles.sectionHeaderRight}>
          {totalReviews > 0 && (
            <div className={styles.avgRatingPill}>
              <span>★</span>
              <span>{avgRating.toFixed(1)}</span>
            </div>
          )}
          <div className={styles.collapseToggle}>
            <span
              className={`${styles.chevron} ${
                isCollapsed ? styles.chevronCollapsed : ""
              }`}
            >
              ▲
            </span>
          </div>
        </div>
      </div>

      {!isCollapsed && (
        <div className={styles.reviewsBody}>
          {/* Ratings Breakdown Summary */}
          {totalReviews > 0 && (
            <div className={styles.summaryCard}>
              <div className={styles.scoreCol}>
                <div className={styles.avgScore}>
                  {avgRating.toFixed(1)}
                  <span className={styles.maxScore}>/5</span>
                </div>
                <div className={styles.starDisplay}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span key={star}>
                      {avgRating >= star ? "★" : avgRating >= star - 0.5 ? "★" : "☆"}
                    </span>
                  ))}
                </div>
                <span className={styles.totalReviewsLabel}>
                  Based on {totalReviews} rating{totalReviews === 1 ? "" : "s"}
                </span>
              </div>

              <div className={styles.breakdownCol}>
                {[5, 4, 3, 2, 1].map((star) => {
                  const count = reviewsData.rating_counts[star.toString()] || 0;
                  const percent = totalReviews > 0 ? (count / totalReviews) * 100 : 0;
                  return (
                    <div key={star} className={styles.breakdownRow}>
                      <span className={styles.starLevel}>
                        {star} <span>★</span>
                      </span>
                      <div className={styles.barTrack}>
                        <div
                          className={styles.barFill}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <span className={styles.countLabel}>{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Review Composer Form (Logged in vs Guest) */}
          {user ? (
            <div className={styles.composerCard}>
              <div className={styles.composerHeader}>
                <h3 className={styles.composerTitle}>
                  {userReview ? "✏️ Edit Your Review" : "✨ Write a Review"}
                </h3>
                {userReview && (
                  <span className={styles.editingBadge}>You reviewed this</span>
                )}
              </div>

              {errorMessage && (
                <div className={styles.errorBanner}>{errorMessage}</div>
              )}

              <form onSubmit={handleSubmit}>
                {/* Interactive Stars */}
                <div className={styles.ratingPickerRow}>
                  <span className={styles.ratingLabel}>Your Rating:</span>
                  <div
                    className={styles.starsInteractive}
                    onMouseLeave={() => setHoverRating(null)}
                  >
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        className={`${styles.starBtn} ${
                          activeRating >= star ? styles.starBtnActive : ""
                        }`}
                        onClick={() => setRating(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        title={`${star} star${star === 1 ? "" : "s"}`}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                  <span className={styles.starMeaning}>
                    {RATING_MEANINGS[activeRating] || ""}
                  </span>
                </div>

                {/* Content Textarea */}
                <div className={styles.textareaWrapper}>
                  <textarea
                    className={styles.textarea}
                    placeholder="What did you think of the plot, acting, pacing, and overall experience?"
                    value={content}
                    maxLength={1000}
                    onChange={(e) => setContent(e.target.value)}
                    disabled={submitting}
                  />
                  <div className={styles.charCount}>
                    {content.length} / 1000
                  </div>
                </div>

                {/* Actions */}
                <div className={styles.formActions}>
                  {userReview && (
                    <button
                      type="button"
                      className={styles.deleteOwnBtn}
                      onClick={() => handleDelete(userReview.id)}
                      disabled={submitting}
                    >
                      Delete Review
                    </button>
                  )}
                  <button
                    type="submit"
                    className={styles.submitBtn}
                    disabled={submitting || !content.trim()}
                  >
                    {submitting
                      ? "Saving..."
                      : userReview
                      ? "Update Review"
                      : "Post Review"}
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <div className={styles.guestCard}>
              <div className={styles.guestContent}>
                <span className={styles.guestIcon}>✍️</span>
                <h3 className={styles.guestTitle}>Share Your Review</h3>
                <p className={styles.guestText}>
                  Watched this movie? Sign in to rate it and share your thoughts with fellow moviegoers in Singapore!
                </p>
                <button
                  type="button"
                  className={styles.guestLoginBtn}
                  onClick={() => openAuthModal("login")}
                >
                  Sign In to Review
                </button>
              </div>
            </div>
          )}

          {/* Reviews Feed */}
          {reviewsData.reviews.length > 0 ? (
            <>
              <div className={styles.reviewList}>
                {reviewsData.reviews.map((rev) => {
                  const isOwnReview = user && user.id === rev.user_id;
                  const initial = rev.username ? rev.username.charAt(0).toUpperCase() : "?";

                  return (
                    <div key={rev.id} className={styles.reviewCard}>
                      <div className={styles.reviewCardHeader}>
                        <div className={styles.authorInfo}>
                          <div className={styles.avatar}>{initial}</div>
                          <div className={styles.authorMeta}>
                            <span className={styles.authorName}>
                              {rev.username}
                              {isOwnReview && (
                                <span className={styles.youBadge}>You</span>
                              )}
                            </span>
                            <span className={styles.reviewDate}>
                              {formatReviewDate(rev.created_at)}
                            </span>
                          </div>
                        </div>

                        <div className={styles.reviewHeaderRight}>
                          <div className={styles.starsPill}>
                            <span>★</span>
                            <span>{rev.rating}.0</span>
                          </div>
                          {isOwnReview && (
                            <button
                              type="button"
                              className={styles.deleteBtn}
                              onClick={() => handleDelete(rev.id)}
                              title="Delete your review"
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      </div>

                      <p className={styles.reviewContent}>{rev.content}</p>
                    </div>
                  );
                })}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className={styles.paginationRow}>
                  <div className={styles.paginationInfo}>
                    Showing <strong>{(page - 1) * ITEMS_PER_PAGE + 1}</strong> –{" "}
                    <strong>{Math.min(page * ITEMS_PER_PAGE, totalReviews)}</strong> of{" "}
                    <strong>{totalReviews}</strong> reviews
                  </div>

                  <div className={styles.paginationControls}>
                    <button
                      type="button"
                      className={styles.pageArrowBtn}
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                      aria-label="Previous Page"
                    >
                      ← Previous
                    </button>

                    <div className={styles.pageNumbers}>
                      {pageNumbers.map((p, idx) => {
                        if (p === "...") {
                          return (
                            <span key={`ellipsis-${idx}`} className={styles.pageEllipsis}>
                              …
                            </span>
                          );
                        }
                        const pageNum = Number(p);
                        const isActive = pageNum === page;
                        return (
                          <button
                            key={pageNum}
                            type="button"
                            className={`${styles.pageNumberBtn} ${
                              isActive ? styles.pageNumberBtnActive : ""
                            }`}
                            onClick={() => handlePageChange(pageNum)}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>

                    <button
                      type="button"
                      className={styles.pageArrowBtn}
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= totalPages}
                      aria-label="Next Page"
                    >
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            !loading && (
              <div className={styles.emptyReviews}>
                <div className={styles.emptyIcon}>🍿</div>
                <h3 className={styles.emptyTitle}>No reviews yet</h3>
                <p className={styles.emptyText}>
                  Be the first to share your rating and review for this movie!
                </p>
              </div>
            )
          )}
        </div>
      )}
    </section>
  );
}
