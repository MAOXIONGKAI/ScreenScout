"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  fetchNotificationChannel,
  saveNotificationChannel,
  fetchSubscriptions,
  createSubscription,
  deleteSubscription,
  toggleSubscription,
} from "@/lib/api";
import { NotificationChannel, Subscription, MatchedMovieItem } from "@/lib/types";
import styles from "./page.module.css";

export default function DashboardPage() {
  const { user, token, isLoading, logout, openAuthModal } = useAuth();
  const router = useRouter();

  // Notification Channel & Subscriptions State
  const [channel, setChannel] = useState<NotificationChannel | null>(null);
  const [telegramHandle, setTelegramHandle] = useState("");
  const [savingChannel, setSavingChannel] = useState(false);
  const [channelSuccess, setChannelSuccess] = useState("");
  const [channelError, setChannelError] = useState("");

  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [subsLoading, setSubsLoading] = useState(true);
  const [movieQuery, setMovieQuery] = useState("");
  const [creatingSub, setCreatingSub] = useState(false);
  const [subSuccess, setSubSuccess] = useState("");
  const [subError, setSubError] = useState("");
  const [activeTab, setActiveTab] = useState<"active" | "triggered">("active");

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "N/A";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-SG", {
        timeZone: "Asia/Singapore",
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  // Load User Data
  const loadUserData = useCallback(async () => {
    if (!token) return;
    setSubsLoading(true);
    try {
      const [ch, subs] = await Promise.all([
        fetchNotificationChannel(token).catch(() => null),
        fetchSubscriptions(token).catch(() => []),
      ]);
      if (ch) {
        setChannel(ch);
        setTelegramHandle(ch.channel_user_id);
      } else if (user) {
        setTelegramHandle(`@${user.username}`);
      }
      setSubscriptions(subs);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setSubsLoading(false);
    }
  }, [token, user]);

  useEffect(() => {
    if (token) {
      loadUserData();
    }
  }, [token, loadUserData]);

  // Handle Telegram Handle Update
  const handleSaveTelegram = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setChannelError("");
    setChannelSuccess("");

    const handle = telegramHandle.trim();
    if (!handle) {
      setChannelError("Please enter your Telegram handle (e.g. @your_username)");
      return;
    }

    setSavingChannel(true);
    try {
      const updated = await saveNotificationChannel(token, handle);
      setChannel(updated);
      setTelegramHandle(updated.channel_user_id);
      setChannelSuccess("✓ Telegram handle saved successfully!");
      setTimeout(() => setChannelSuccess(""), 4000);
    } catch (err: any) {
      setChannelError(err.message || "Failed to save Telegram handle");
    } finally {
      setSavingChannel(false);
    }
  };

  // Handle Create Subscription
  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSubError("");
    setSubSuccess("");

    const query = movieQuery.trim();
    if (!query) {
      setSubError("Please enter a movie title or keyword to monitor");
      return;
    }

    setCreatingSub(true);
    try {
      const newSub = await createSubscription(token, query);
      setMovieQuery("");
      if (!newSub.is_active) {
        const matchCount = newSub.matched_movies?.length || 1;
        setSubSuccess(
          `🎉 Matched ${matchCount} movie${matchCount > 1 ? "s" : ""} for "${query}"! Instant alert dispatched to Telegram.`
        );
        setActiveTab("triggered");
      } else {
        setSubSuccess(`✓ Tracking "${query}"! We will alert you on Telegram once available.`);
        setActiveTab("active");
      }
      await loadUserData();
      setTimeout(() => setSubSuccess(""), 5000);
    } catch (err: any) {
      setSubError(err.message || "Failed to create subscription");
    } finally {
      setCreatingSub(false);
    }
  };

  // Handle Delete Subscription
  const handleDeleteSubscription = async (id: number) => {
    if (!token) return;
    try {
      await deleteSubscription(token, id);
      setSubscriptions((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete subscription");
    }
  };

  // Handle Toggle (Re-monitor) Subscription
  const handleToggleSubscription = async (id: number) => {
    if (!token) return;
    try {
      const updated = await toggleSubscription(token, id);
      setSubscriptions((prev) =>
        prev.map((s) => (s.id === id ? updated : s))
      );
      if (updated.is_active) {
        setActiveTab("active");
      }
    } catch (err: any) {
      alert(err.message || "Failed to update subscription");
    }
  };

  if (isLoading) {
    return (
      <div className="container">
        <div className={styles.dashboardWrapper}>
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <div className="skeleton" style={{ width: 120, height: 120, borderRadius: "50%", margin: "0 auto 20px" }} />
            <div className="skeleton" style={{ width: 240, height: 28, margin: "0 auto 12px" }} />
            <div className="skeleton" style={{ width: 180, height: 16, margin: "0 auto" }} />
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container">
        <div className={styles.dashboardWrapper}>
          <div className={styles.unauthWrapper}>
            <div className={styles.unauthIcon}>🔒</div>
            <h1 className={styles.unauthTitle}>Sign In Required</h1>
            <p className={styles.unauthText}>
              Please sign in or create an account to view your user profile and manage your movie alert subscriptions.
            </p>
            <div className={styles.unauthActions}>
              <button
                className={styles.signInCtaBtn}
                onClick={() => openAuthModal("login")}
              >
                <span>✨</span>
                <span>Sign In to Account</span>
              </button>
              <button
                className={styles.registerCtaBtn}
                onClick={() => openAuthModal("register")}
              >
                Create Account
              </button>
            </div>
            <div style={{ marginTop: "var(--space-xl)" }}>
              <Link href="/" className={styles.backLink}>
                ← Back to Movies
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const initials = user.username ? user.username.slice(0, 2).toUpperCase() : "U";
  const activeSubs = subscriptions.filter((s) => s.is_active);
  const triggeredSubs = subscriptions.filter((s) => !s.is_active);

  return (
    <div className="container">
      <div className={styles.dashboardWrapper}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.badge}>
            <span>✨ Member Account</span>
          </div>
          <h1 className={styles.title}>User Dashboard</h1>
          <p className={styles.subtitle}>
            Manage your ScreenScout profile, Telegram notifications, and movie schedule subscriptions.
          </p>
        </div>

        {/* Profile Card */}
        <div className={styles.profileCard}>
          <div className={styles.avatarCircle}>{initials}</div>
          <div className={styles.profileInfo}>
            <h2 className={styles.profileUsername}>{user.username}</h2>
            <div className={styles.profileMeta}>
              <span>Joined: {formatDate(user.created_at)}</span>
            </div>
          </div>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            Log Out
          </button>
        </div>

        {/* Section 1: Telegram Notification Settings */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>💬</div>
            <div>
              <h2 className={styles.sectionTitle}>Telegram Notification Handle</h2>
              <p className={styles.sectionSubtitle}>
                Register your Telegram handle to receive instant alerts when your subscribed movies are published.
              </p>
            </div>
          </div>

          {channelSuccess && (
            <div className={styles.successBanner}>{channelSuccess}</div>
          )}
          {channelError && (
            <div className={styles.errorBanner}>{channelError}</div>
          )}

          <form className={styles.handleForm} onSubmit={handleSaveTelegram}>
            <div className={styles.handleInputWrapper}>
              <span className={styles.handlePrefix}>@</span>
              <input
                type="text"
                className={styles.handleInput}
                placeholder="your_telegram_handle"
                value={telegramHandle.startsWith("@") ? telegramHandle.slice(1) : telegramHandle}
                onChange={(e) => setTelegramHandle(`@${e.target.value.replace(/^@+/, "")}`)}
                required
              />
            </div>
            <button
              type="submit"
              className={styles.saveHandleBtn}
              disabled={savingChannel}
            >
              {savingChannel ? "Saving..." : "Save Handle"}
            </button>
          </form>

          {channel ? (
            <div className={styles.channelStatus}>
              <span className={styles.statusDotActive} />
              <span>
                Connected to <strong>{channel.channel_user_id}</strong> (Real-time alerts active)
              </span>
            </div>
          ) : (
            <div className={styles.channelStatus}>
              <span className={styles.statusDotWarning} />
              <span>No Telegram handle registered yet. Enter your handle above to enable alerts.</span>
            </div>
          )}
        </section>

        {/* Section 2: Movie Monitoring Subscriptions */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>🔔</div>
            <div>
              <h2 className={styles.sectionTitle}>Movie Schedule Subscriptions</h2>
              <p className={styles.sectionSubtitle}>
                Monitor upcoming movies by exact name or substring keyword. Multiple matching movies across Singapore cinemas will all be detected and notified simultaneously.
              </p>
            </div>
          </div>

          {subSuccess && (
            <div className={styles.successBanner}>{subSuccess}</div>
          )}
          {subError && (
            <div className={styles.errorBanner}>{subError}</div>
          )}

          {/* New Subscription Form */}
          <form className={styles.subscriptionForm} onSubmit={handleCreateSubscription}>
            <div className={styles.subInputWrapper}>
              <input
                type="text"
                className={styles.subInput}
                placeholder="Enter movie keyword (e.g. Odyssey, Superman, Avatar, Captain)..."
                value={movieQuery}
                onChange={(e) => setMovieQuery(e.target.value)}
                required
              />
            </div>
            <button
              type="submit"
              className={styles.subscribeBtn}
              disabled={creatingSub}
            >
              {creatingSub ? "Tracking..." : "+ Track Movie"}
            </button>
          </form>

          {/* Subscriptions Tabs */}
          <div className={styles.subTabs}>
            <button
              className={`${styles.subTab} ${activeTab === "active" ? styles.activeSubTab : ""}`}
              onClick={() => setActiveTab("active")}
            >
              <span>Active Monitoring</span>
              <span className={styles.countBadge}>{activeSubs.length}</span>
            </button>
            <button
              className={`${styles.subTab} ${activeTab === "triggered" ? styles.activeSubTab : ""}`}
              onClick={() => setActiveTab("triggered")}
            >
              <span>Triggered History</span>
              <span className={styles.countBadge}>{triggeredSubs.length}</span>
            </button>
          </div>

          {/* Tab Content */}
          {subsLoading ? (
            <div style={{ textAlign: "center", padding: "30px 0" }}>
              <div className="skeleton" style={{ width: "100%", height: 60, borderRadius: "var(--radius-md)" }} />
            </div>
          ) : activeTab === "active" ? (
            <div className={styles.subList}>
              {activeSubs.length > 0 ? (
                activeSubs.map((sub) => (
                  <div key={sub.id} className={styles.subCard}>
                    <div className={styles.subCardMain}>
                      <div className={styles.subStatusBadgeActive}>
                        <span className={styles.pulseDot} />
                        <span>Monitoring</span>
                      </div>
                      <h3 className={styles.subQueryTitle}>&ldquo;{sub.movie_query}&rdquo;</h3>
                      <p className={styles.subMetaText}>
                        Tracking started: {formatDate(sub.created_at)}
                      </p>
                    </div>
                    <div className={styles.subCardActions}>
                      <button
                        className={styles.deleteSubBtn}
                        onClick={() => handleDeleteSubscription(sub.id)}
                        title="Cancel monitoring"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.emptySubs}>
                  <div className={styles.emptySubsIcon}>🎯</div>
                  <p className={styles.emptySubsTitle}>No active monitoring jobs</p>
                  <p className={styles.emptySubsText}>
                    Type a movie name above and click &ldquo;Track Movie&rdquo; to start automated 24/7 screening detection.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className={styles.subList}>
              {triggeredSubs.length > 0 ? (
                triggeredSubs.map((sub) => {
                  const matches: MatchedMovieItem[] =
                    sub.matched_movies && sub.matched_movies.length > 0
                      ? sub.matched_movies
                      : sub.matched_movie_id && sub.matched_movie_title
                      ? [
                          {
                            id: sub.matched_movie_id,
                            title: sub.matched_movie_title,
                            provider: "Cinema",
                            status: "now_showing",
                            release_date: "",
                          },
                        ]
                      : [];

                  return (
                    <div key={sub.id} className={`${styles.subCard} ${styles.subCardTriggered}`}>
                      <div className={styles.subCardMain}>
                        <div className={styles.subHeaderRow}>
                          <div className={styles.subStatusBadgeTriggered}>
                            <span>✓ Alert Triggered</span>
                          </div>
                          <span className={styles.matchCountBadge}>
                            {matches.length} {matches.length === 1 ? "Movie" : "Movies"} Matched
                          </span>
                        </div>

                        <h3 className={styles.subQueryTitle}>
                          Tracked Keyword: &ldquo;{sub.movie_query}&rdquo;
                        </h3>

                        {/* Matched Movies Grid */}
                        {matches.length > 0 && (
                          <div className={styles.matchedMoviesGrid}>
                            {matches.map((m) => {
                              const isGV = m.provider === "GV" || m.provider === "Golden Village";
                              const isShowing = m.status === "now_showing" || m.status === "LIVE";
                              return (
                                <div key={m.id} className={styles.matchedMovieCard}>
                                  <div className={styles.matchedMovieTop}>
                                    <span className={styles.movieIcon}>🎥</span>
                                    <Link
                                      href={`/movies/${m.id}`}
                                      className={styles.matchedTitleLink}
                                    >
                                      {m.title}
                                    </Link>
                                  </div>
                                  <div className={styles.matchedMovieTags}>
                                    <span
                                      className={`${styles.cinemaTag} ${
                                        isGV ? styles.gvTag : styles.shawTag
                                      }`}
                                    >
                                      {isGV ? "Golden Village" : "Shaw Theatres"}
                                    </span>
                                    <span
                                      className={`${styles.statusTag} ${
                                        isShowing ? styles.showingTag : styles.comingTag
                                      }`}
                                    >
                                      {isShowing ? "Now Showing" : "Coming Soon"}
                                    </span>
                                    {m.release_date && (
                                      <span className={styles.releaseDateTag}>
                                        📅 {m.release_date}
                                      </span>
                                    )}
                                    <Link
                                      href={`/movies/${m.id}`}
                                      className={styles.viewShowtimesLink}
                                    >
                                      Showtimes →
                                    </Link>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}

                        <p className={styles.subMetaText}>
                          Notified on: {formatDate(sub.triggered_at || sub.updated_at)}
                        </p>
                      </div>

                      <div className={styles.subCardActions}>
                        <button
                          className={styles.remonitorBtn}
                          onClick={() => handleToggleSubscription(sub.id)}
                          title="Re-activate monitoring"
                        >
                          Re-monitor
                        </button>
                        <button
                          className={styles.deleteSubBtn}
                          onClick={() => handleDeleteSubscription(sub.id)}
                          title="Delete record"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className={styles.emptySubs}>
                  <div className={styles.emptySubsIcon}>📬</div>
                  <p className={styles.emptySubsTitle}>No triggered alerts yet</p>
                  <p className={styles.emptySubsText}>
                    When a monitored movie is published by Singapore cinemas, the alert will be dispatched and archived here.
                  </p>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
