"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  fetchNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteNotification,
  clearAllNotifications,
} from "@/lib/api";
import { InAppNotification } from "@/lib/types";
import styles from "./NotificationBell.module.css";

export default function NotificationBell() {
  const { token, user } = useAuth();
  const router = useRouter();

  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Format relative timestamp
  const formatRelativeTime = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHr = Math.floor(diffMin / 60);
      const diffDays = Math.floor(diffHr / 24);

      if (diffSec < 45) return "Just now";
      if (diffMin < 60) return `${diffMin}m ago`;
      if (diffHr < 24) return `${diffHr}h ago`;
      if (diffDays === 1) return "Yesterday";
      if (diffDays < 7) return `${diffDays}d ago`;

      return date.toLocaleDateString("en-SG", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // Load notifications from backend
  const loadNotifications = useCallback(
    async (isBackground = false) => {
      if (!token) return;
      if (!isBackground) setLoading(true);

      try {
        const res = await fetchNotifications(token);
        setNotifications(res.notifications || []);
        setUnreadCount(res.unread_count || 0);
      } catch (err) {
        console.error("Failed to load in-app notifications:", err);
      } finally {
        if (!isBackground) setLoading(false);
      }
    },
    [token]
  );

  // Initial load and periodic polling (every 20s)
  useEffect(() => {
    if (!token) return;
    loadNotifications();

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        loadNotifications(true);
      }
    }, 20000);

    const handleFocus = () => {
      loadNotifications(true);
    };

    const handleCustomUpdate = () => {
      loadNotifications(true);
    };

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleFocus);
    window.addEventListener("screenscout:notifications-updated", handleCustomUpdate);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleFocus);
      window.removeEventListener("screenscout:notifications-updated", handleCustomUpdate);
    };
  }, [token, loadNotifications]);

  // Click outside and Escape key to close popover
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleToggle = () => {
    setIsOpen((prev) => !prev);
    if (!isOpen && token) {
      loadNotifications(true);
    }
  };

  const handleMarkAllRead = async () => {
    if (!token || unreadCount === 0) return;
    try {
      await markAllNotificationsAsRead(token);
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true }))
      );
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    }
  };

  const handleClearAll = async () => {
    if (!token || notifications.length === 0) return;
    try {
      await clearAllNotifications(token);
      setNotifications([]);
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to clear all notifications:", err);
    }
  };

  const handleItemClick = async (notif: InAppNotification) => {
    if (token && !notif.is_read) {
      // Optimistically update
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
      markNotificationAsRead(token, notif.id).catch(console.error);
    }

    setIsOpen(false);

    // Route to movie detail page if matched_movie_id is available
    if (notif.matched_movie_id) {
      router.push(`/movies/${notif.matched_movie_id}`);
    } else if (notif.matched_movies && notif.matched_movies.length > 0) {
      router.push(`/movies/${notif.matched_movies[0].id}`);
    } else {
      router.push("/monitorings");
    }
  };

  const handleSingleMarkRead = async (
    e: React.MouseEvent,
    id: number
  ) => {
    e.stopPropagation();
    if (!token) return;
    try {
      await markNotificationAsRead(token, id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  const handleSingleDelete = async (
    e: React.MouseEvent,
    id: number,
    wasUnread: boolean
  ) => {
    e.stopPropagation();
    if (!token) return;
    try {
      await deleteNotification(token, id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (wasUnread) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error("Failed to delete notification:", err);
    }
  };

  if (!user) return null;

  return (
    <div className={styles.bellContainer} ref={containerRef}>
      {/* Bell Button */}
      <button
        type="button"
        className={`${styles.bellButton} ${isOpen ? styles.bellButtonActive : ""}`}
        onClick={handleToggle}
        aria-label={
          unreadCount > 0
            ? `${unreadCount} unread screening notifications`
            : "Screening notifications"
        }
        aria-expanded={isOpen}
        title={
          unreadCount > 0
            ? `${unreadCount} new tracking alert${unreadCount > 1 ? "s" : ""}`
            : "Tracking alerts"
        }
      >
        <svg
          className={styles.bellIcon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {unreadCount > 0 && (
          <span className={styles.badge}>
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className={styles.popover} role="dialog" aria-label="Notifications panel">
          {/* Header */}
          <div className={styles.popoverHeader}>
            <div className={styles.headerLeft}>
              <span className={styles.headerTitle}>Tracking Alerts</span>
              {unreadCount > 0 ? (
                <span className={styles.unreadPill}>
                  {unreadCount} New
                </span>
              ) : (
                <span className={styles.caughtUpPill}>
                  ✓ All Caught Up
                </span>
              )}
            </div>

            <div className={styles.headerActions}>
              {unreadCount > 0 && (
                <button
                  type="button"
                  className={styles.headerActionBtn}
                  onClick={handleMarkAllRead}
                  title="Mark all notifications as read"
                >
                  ✓ Read All
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  type="button"
                  className={styles.headerActionBtn}
                  onClick={handleClearAll}
                  title="Clear all alerts"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>

          {/* List Content */}
          <div className={styles.notifList}>
            {notifications.length > 0 ? (
              notifications.map((notif) => {
                const isUnread = !notif.is_read;
                const primaryMovie =
                  notif.matched_movies && notif.matched_movies.length > 0
                    ? notif.matched_movies[0]
                    : null;
                const movieTitle =
                  primaryMovie?.title ||
                  notif.matched_movie_title ||
                  "Screening Available";
                const provider = primaryMovie?.provider || "Cinema";
                const isGV = provider === "GV" || provider === "Golden Village";
                const status = primaryMovie?.status || "now_showing";
                const isShowing = status === "now_showing" || status === "LIVE";
                const isAdvance = status === "advance_sales";
                const statusLabel = isShowing
                  ? "Now Showing"
                  : isAdvance
                  ? "Advance Sales"
                  : "Coming Soon";
                const statusClass = isShowing
                  ? styles.showingTag
                  : isAdvance
                  ? styles.advanceTag
                  : styles.comingTag;

                return (
                  <div
                    key={notif.id}
                    className={`${styles.notifCard} ${
                      isUnread ? styles.notifCardUnread : ""
                    }`}
                    onClick={() => handleItemClick(notif)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleItemClick(notif);
                      }
                    }}
                  >
                    {/* Top Row: Keyword Badge & Unread Dot */}
                    <div className={styles.notifCardTop}>
                      <span className={styles.keywordBadge}>
                        🎯 &ldquo;{notif.movie_query || "Movie Alert"}&rdquo;
                      </span>
                      {isUnread && <span className={styles.unreadDot} />}
                    </div>

                    {/* Movie Info */}
                    <div className={styles.notifContent}>
                      <div className={styles.movieMatchRow}>
                        <span className={styles.movieIcon}>🎬</span>
                        <h4 className={styles.movieTitle} title={movieTitle}>
                          {movieTitle}
                        </h4>
                      </div>

                      <div className={styles.tagsRow}>
                        <span
                          className={`${styles.cinemaTag} ${
                            isGV ? styles.gvTag : styles.shawTag
                          }`}
                        >
                          {isGV ? "Golden Village" : "Shaw Theatres"}
                        </span>
                        <span className={`${styles.statusTag} ${statusClass}`}>
                          {statusLabel}
                        </span>
                        {notif.matched_movies && notif.matched_movies.length > 1 && (
                          <span className={styles.keywordBadge} style={{ fontSize: 10 }}>
                            +{notif.matched_movies.length - 1} more match{notif.matched_movies.length > 2 ? "es" : ""}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Bottom Row: Timestamp and Item Actions */}
                    <div className={styles.notifBottom}>
                      <span className={styles.timeText}>
                        {formatRelativeTime(notif.created_at)}
                      </span>

                      <div className={styles.itemActions}>
                        {isUnread && (
                          <button
                            type="button"
                            className={styles.itemActionBtn}
                            onClick={(e) => handleSingleMarkRead(e, notif.id)}
                            title="Mark as read"
                          >
                            ✓
                          </button>
                        )}
                        <button
                          type="button"
                          className={`${styles.itemActionBtn} ${styles.deleteItemBtn}`}
                          onClick={(e) =>
                            handleSingleDelete(e, notif.id, isUnread)
                          }
                          title="Dismiss notification"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>🍿</div>
                <h4 className={styles.emptyTitle}>No Tracking Alerts Yet</h4>
                <p className={styles.emptyText}>
                  Subscribe to upcoming movies in <strong>Monitorings</strong> and we will alert you here as soon as tickets or showtimes go live!
                </p>
                <Link
                  href="/monitorings"
                  className={styles.emptyCta}
                  onClick={() => setIsOpen(false)}
                >
                  Go to Monitorings →
                </Link>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className={styles.popoverFooter}>
            <Link
              href="/monitorings"
              className={styles.viewAllLink}
              onClick={() => setIsOpen(false)}
            >
              <span>Manage Tracking Tasks</span>
              <span>→</span>
            </Link>
            <div className={styles.liveIndicator}>
              <span className={styles.liveDot} />
              <span>Live sync</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
