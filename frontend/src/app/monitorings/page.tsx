"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
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

export default function MonitoringsPage() {
  const { user, token, isLoading, openAuthModal } = useAuth();

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
  const [activeTab, setActiveTab] = useState<"active" | "disabled" | "triggered">("active");

  // Collapsible States
  const [guideCollapsed, setGuideCollapsed] = useState(false);
  const [collapsedTriggeredSubs, setCollapsedTriggeredSubs] = useState<Record<number, boolean>>({});

  const toggleTriggeredSubCollapse = (subId: number) => {
    setCollapsedTriggeredSubs((prev) => ({
      ...prev,
      [subId]: !prev[subId],
    }));
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
      console.error("Error loading monitorings data:", err);
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

  // Handle Toggle (Activate / Deactivate) Subscription - remains in current tab
  const handleToggleSubscription = async (id: number) => {
    if (!token) return;
    try {
      const updated = await toggleSubscription(token, id);
      setSubscriptions((prev) =>
        prev.map((s) => (s.id === id ? updated : s))
      );
    } catch (err: any) {
      alert(err.message || "Failed to update subscription");
    }
  };

  if (isLoading) {
    return (
      <div className="container">
        <div className={styles.wrapper}>
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
        <div className={styles.wrapper}>
          <div className={styles.unauthWrapper}>
            <div className={styles.unauthIcon}>🔔</div>
            <h1 className={styles.unauthTitle}>Sign In to Monitor Movies</h1>
            <p className={styles.unauthText}>
              Create customized schedule tracking alerts and receive real-time Telegram notifications when screenings are published across Singapore cinemas.
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

  const activeSubs = subscriptions.filter((s) => s.is_active);
  const disabledSubs = subscriptions.filter((s) => !s.is_active && !s.triggered_at);
  const triggeredSubs = subscriptions.filter((s) => !s.is_active && Boolean(s.triggered_at));

  return (
    <div className="container">
      <div className={styles.wrapper}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.badge}>
            <span>✨ 24/7 Screening Detection</span>
          </div>
          <h1 className={styles.title}>Movie Monitorings</h1>
          <p className={styles.subtitle}>
            Subscribe to upcoming movies by name or keyword. We continuously scan Golden Village & Shaw Theatres and notify your Telegram the moment showtimes become available.
          </p>
        </div>

        {/* Section 1: Telegram Notification Settings */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>💬</div>
            <div>
              <h2 className={styles.sectionTitle}>Telegram Notification Settings</h2>
              <p className={styles.sectionSubtitle}>
                Link your Telegram account to receive instant alerts when your subscribed movies are published across Singapore cinemas.
              </p>
            </div>
          </div>

          {/* Collapsible Setup Guide (Inside Card) */}
          <div
            className={`${styles.cardSetupGuide} ${
              guideCollapsed ? styles.cardSetupGuideCollapsed : ""
            }`}
          >
            <div
              className={styles.cardSetupHeader}
              onClick={() => setGuideCollapsed((prev) => !prev)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setGuideCollapsed((prev) => !prev);
                }
              }}
              title={
                guideCollapsed
                  ? "Click to expand Setup Guide"
                  : "Click to collapse Setup Guide"
              }
              aria-expanded={!guideCollapsed}
            >
              <h3 className={styles.cardSetupTitle}>📖 Setup Guide</h3>
              <div className={styles.guideCollapseToggle}>
                <span
                  className={`${styles.chevron} ${
                    guideCollapsed ? styles.chevronCollapsed : ""
                  }`}
                >
                  ▲
                </span>
              </div>
            </div>

            {!guideCollapsed && (
              <div className={styles.cardStepsList}>
                <div className={styles.cardStepItem}>
                  <span className={styles.cardStepNum}>1</span>
                  <div>
                    <strong>Start the Bot:</strong> Open{" "}
                    <a
                      href="https://t.me/screenscoutBot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.botLink}
                    >
                      @screenscoutBot ↗
                    </a>{" "}
                    in Telegram and tap <strong>Start</strong> (<code className={styles.inlineCode}>/start</code>) so Telegram authorizes alerts.
                  </div>
                </div>
                <div className={styles.cardStepItem}>
                  <span className={styles.cardStepNum}>2</span>
                  <div>
                    <strong>Save Your Handle:</strong> Enter your Telegram username (e.g. <code className={styles.inlineCode}>@your_username</code>) below and click <strong>Save Handle</strong>.
                  </div>
                </div>
                <div className={styles.cardStepItem}>
                  <span className={styles.cardStepNum}>3</span>
                  <div>
                    <strong>Receive Alerts:</strong> When your monitored movies are detected, <strong>@screenscoutBot</strong> will message you with direct showtime links!
                  </div>
                </div>
              </div>
            )}
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
              <span>No Telegram handle registered yet. Complete steps 1 & 2 above to enable alerts.</span>
            </div>
          )}
        </section>

        {/* Section 2: Movie Monitoring Subscriptions */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>🔔</div>
            <div>
              <h2 className={styles.sectionTitle}>Active Subscriptions & Screening Alerts</h2>
              <p className={styles.sectionSubtitle}>
                Track any movie by exact name or substring keyword. Multiple matching movies across Singapore cinemas will all be detected and notified simultaneously.
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
              className={`${styles.subTab} ${activeTab === "disabled" ? styles.activeSubTab : ""}`}
              onClick={() => setActiveTab("disabled")}
            >
              <span>Disabled Tasks</span>
              <span className={styles.countBadge}>{disabledSubs.length}</span>
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
                    <div className={styles.subCardRightActions}>
                      <div className={styles.toggleControlWrapper}>
                        <span className={styles.toggleControlLabel}>
                          Active
                        </span>
                        <label
                          className={styles.toggleSwitch}
                          title="Click to pause monitoring (move to Disabled Tasks)"
                        >
                          <input
                            type="checkbox"
                            checked={true}
                            onChange={() => handleToggleSubscription(sub.id)}
                            aria-label={`Pause monitoring for ${sub.movie_query}`}
                          />
                          <span className={styles.toggleSlider} />
                        </label>
                      </div>
                      <button
                        className={styles.deleteSubBtn}
                        onClick={() => handleDeleteSubscription(sub.id)}
                        title="Cancel and remove monitoring"
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
                    Type a movie keyword above and click &ldquo;Track Movie&rdquo; to start automated 24/7 screening detection.
                  </p>
                </div>
              )}
            </div>
          ) : activeTab === "disabled" ? (
            <div className={styles.subList}>
              {disabledSubs.length > 0 ? (
                disabledSubs.map((sub) => (
                  <div key={sub.id} className={styles.subCard}>
                    <div className={styles.subCardMain}>
                      <div className={styles.subStatusBadgePaused}>
                        <span>⏸ Paused</span>
                      </div>
                      <h3 className={styles.subQueryTitle}>&ldquo;{sub.movie_query}&rdquo;</h3>
                      <p className={styles.subMetaText}>
                        Tracking created: {formatDate(sub.created_at)}
                      </p>
                    </div>
                    <div className={styles.subCardRightActions}>
                      <div className={styles.toggleControlWrapper}>
                        <span className={styles.toggleControlLabel}>
                          Paused
                        </span>
                        <label
                          className={styles.toggleSwitch}
                          title="Click to resume monitoring (move to Active Monitoring)"
                        >
                          <input
                            type="checkbox"
                            checked={false}
                            onChange={() => handleToggleSubscription(sub.id)}
                            aria-label={`Resume monitoring for ${sub.movie_query}`}
                          />
                          <span className={styles.toggleSlider} />
                        </label>
                      </div>
                      <button
                        className={styles.deleteSubBtn}
                        onClick={() => handleDeleteSubscription(sub.id)}
                        title="Cancel and remove monitoring"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className={styles.emptySubs}>
                  <div className={styles.emptySubsIcon}>⏸</div>
                  <p className={styles.emptySubsTitle}>No disabled tasks</p>
                  <p className={styles.emptySubsText}>
                    When you pause an active monitoring job using its toggle switch, it will appear here.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className={`${styles.subList} ${styles.triggeredSubList}`}>
              {triggeredSubs.length > 0 ? (
                triggeredSubs.map((sub) => {
                  const isCollapsed = Boolean(collapsedTriggeredSubs[sub.id]);
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
                    <div
                      key={sub.id}
                      className={`${styles.subCard} ${styles.subCardTriggered} ${
                        isCollapsed ? styles.subCardCollapsed : ""
                      }`}
                    >
                      <div className={styles.subCardTopRow}>
                        <div
                          className={styles.subCardHeaderClickable}
                          onClick={() => toggleTriggeredSubCollapse(sub.id)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              toggleTriggeredSubCollapse(sub.id);
                            }
                          }}
                          title={
                            isCollapsed
                              ? "Click to expand matched movie details"
                              : "Click to collapse card"
                          }
                          aria-expanded={!isCollapsed}
                        >
                          <div className={styles.subHeaderRow}>
                            <div className={styles.subStatusBadgeTriggered}>
                              <span>✓ Alert Triggered</span>
                            </div>
                            <span className={styles.matchCountBadge}>
                              {matches.length}{" "}
                              {matches.length === 1 ? "Movie" : "Movies"} Matched
                            </span>
                          </div>

                          <h3 className={styles.subQueryTitle}>
                            Tracked Keyword: &ldquo;{sub.movie_query}&rdquo;
                          </h3>
                        </div>

                        <div className={styles.subCardActions}>
                          <button
                            className={styles.deleteSubBtn}
                            onClick={() => handleDeleteSubscription(sub.id)}
                            title="Delete record"
                          >
                            Delete
                          </button>
                          <button
                            className={styles.collapseToggleBtn}
                            onClick={() => toggleTriggeredSubCollapse(sub.id)}
                            title={isCollapsed ? "Expand details" : "Collapse card"}
                            aria-label="Toggle details"
                          >
                            <span
                              className={`${styles.chevron} ${
                                isCollapsed ? styles.chevronCollapsed : ""
                              }`}
                            >
                              ▲
                            </span>
                          </button>
                        </div>
                      </div>

                      {/* Expanded Content: Matched Movies Grid & Notified Timestamp */}
                      {!isCollapsed && (
                        <div className={styles.subCardBody}>
                          {matches.length > 0 && (
                            <div className={styles.matchedMoviesGrid}>
                              {matches.map((m) => {
                                const isGV =
                                  m.provider === "GV" ||
                                  m.provider === "Golden Village";
                                const isShowing =
                                  m.status === "now_showing" ||
                                  m.status === "LIVE";
                                return (
                                  <Link
                                    key={m.id}
                                    href={`/movies/${m.id}`}
                                    className={styles.matchedMovieCard}
                                    title={`View showtimes and details for ${m.title}`}
                                  >
                                    <div className={styles.matchedMovieTop}>
                                      <span className={styles.movieIcon}>🎥</span>
                                      <h4 className={styles.matchedTitle}>
                                        {m.title}
                                      </h4>
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
                                          isShowing
                                            ? styles.showingTag
                                            : styles.comingTag
                                        }`}
                                      >
                                        {isShowing ? "Now Showing" : "Coming Soon"}
                                      </span>
                                      {m.release_date && (
                                        <span className={styles.releaseDateTag}>
                                          📅 {m.release_date}
                                        </span>
                                      )}
                                    </div>
                                  </Link>
                                );
                              })}
                            </div>
                          )}

                          <p className={styles.subMetaText}>
                            Notified on:{" "}
                            {formatDate(sub.triggered_at || sub.updated_at)}
                          </p>
                        </div>
                      )}
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
