"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  fetchAdminStats,
  invalidateAllMovieCache,
  triggerSubscriptionCheck,
} from "@/lib/api";
import { AdminStatsResponse } from "@/lib/types";
import styles from "./page.module.css";

export default function AdminDashboardPage() {
  const { user, token, isLoading: isAuthLoading, openAuthModal } = useAuth();
  const router = useRouter();

  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isActionRunning, setIsActionRunning] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<string>("");

  // Live Singapore Clock
  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(
        new Date().toLocaleTimeString("en-SG", {
          timeZone: "Asia/Singapore",
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchAdminStats(token);
      setStats(data);
    } catch (err: any) {
      setError(err.message || "Failed to load telemetry statistics");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthLoading && user && user.role === "admin" && token) {
      loadStats();
    }
  }, [isAuthLoading, user, token, loadStats]);

  const handlePurgeCache = async () => {
    try {
      setIsActionRunning(true);
      const res = await invalidateAllMovieCache(token || undefined);
      setToastMessage(`✓ Redis Cache purged successfully (${res.flushed_count || "all"} keys cleared)`);
      setTimeout(() => setToastMessage(null), 4000);
      loadStats();
    } catch (err: any) {
      alert("Error purging cache: " + err.message);
    } finally {
      setIsActionRunning(false);
    }
  };

  const handleRunSubCheck = async () => {
    try {
      setIsActionRunning(true);
      const res = await triggerSubscriptionCheck();
      setToastMessage(`✓ Subscription schedule check triggered: ${res.message || "completed"}`);
      setTimeout(() => setToastMessage(null), 4000);
      loadStats();
    } catch (err: any) {
      alert("Error triggering check: " + err.message);
    } finally {
      setIsActionRunning(false);
    }
  };

  // 1. Loading State
  if (isAuthLoading) {
    return (
      <div className="container">
        <div className={styles.adminWrapper}>
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div className="skeleton" style={{ width: 140, height: 28, margin: "0 auto 16px", borderRadius: 20 }} />
            <div className="skeleton" style={{ width: 320, height: 36, margin: "0 auto 12px" }} />
            <div className="skeleton" style={{ width: 220, height: 18, margin: "0 auto" }} />
          </div>
        </div>
      </div>
    );
  }

  // 2. Unauthenticated State
  if (!user) {
    return (
      <div className="container">
        <div className={styles.adminWrapper}>
          <div className={styles.unauthWrapper}>
            <div className={styles.unauthIcon}>🔒</div>
            <h1 className={styles.unauthTitle}>Sign In Required</h1>
            <p className={styles.unauthText}>
              You must be logged in as an administrator to access the ScreenScout Admin Console.
            </p>
            <div className={styles.unauthActions}>
              <button
                className={styles.primaryCtaBtn}
                onClick={() => openAuthModal("login")}
              >
                <span>✨</span>
                <span>Sign In to Account</span>
              </button>
              <Link href="/" className={styles.secondaryCtaBtn}>
                ← Back to Movies
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 3. Unauthorized State (Logged in as normal user, not admin)
  if (user.role !== "admin") {
    return (
      <div className="container">
        <div className={styles.adminWrapper}>
          <div className={styles.unauthWrapper}>
            <div className={styles.unauthIcon}>⛔</div>
            <h1 className={styles.unauthTitle}>Administrator Access Required</h1>
            <p className={styles.unauthText}>
              Your account (<strong>{user.username}</strong>) has the <code>member</code> role. The Admin Console is restricted to accounts with administrator privileges.
            </p>
            <div className={styles.unauthActions}>
              <Link href="/dashboard" className={styles.primaryCtaBtn}>
                <span>👤</span>
                <span>Open User Dashboard</span>
              </Link>
              <Link href="/" className={styles.secondaryCtaBtn}>
                Back to Movies
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className={styles.adminWrapper}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.titleArea}>
            <div className={styles.adminBadge}>
              <span>👑 Administrator Console</span>
            </div>
            <h1 className={styles.title}>System Telemetry & Controls</h1>
            <p className={styles.subtitle}>
              Live overview of movie catalogue inventories, platform users, screening tracking jobs, and infrastructure status.
            </p>
          </div>

          <div className={styles.headerActions}>
            <div className={styles.clockBadge}>
              <span>🇸🇬 SGT</span>
              <span>{currentTime || "15:00:00"}</span>
            </div>
            <Link
              href="/dashboard"
              className={styles.userDashboardBtn}
              title="Switch to User Dashboard & profile"
            >
              <span>👤</span>
              <span>User Dashboard</span>
            </Link>
            <button
              className={styles.refreshBtn}
              onClick={loadStats}
              disabled={isLoading}
              title="Refresh telemetry metrics"
            >
              <span>{isLoading ? "🔄 Loading..." : "🔄 Refresh"}</span>
            </button>
          </div>
        </div>

        {/* Toast Alert */}
        {toastMessage && (
          <div className={styles.toast}>
            <span>{toastMessage}</span>
            <button
              onClick={() => setToastMessage(null)}
              style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", fontWeight: 700 }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Operational Quick Actions Bar */}
        <div className={styles.opsBar}>
          <div className={styles.opsTitleArea}>
            <span className={styles.opsIcon}>⚡</span>
            <div>
              <div className={styles.opsTitle}>Operational Controls</div>
              <div className={styles.opsSubtitle}>Trigger server actions & pipeline maintenance</div>
            </div>
          </div>

          <div className={styles.opsButtons}>
            <button
              className={`${styles.opBtn} ${styles.purgeCacheBtn}`}
              onClick={handlePurgeCache}
              disabled={isActionRunning}
              title="Flush all cached movie entries in Redis"
            >
              <span>🗑️</span>
              <span>Purge Redis Movie Cache</span>
            </button>
            <button
              className={`${styles.opBtn} ${styles.checkSubBtn}`}
              onClick={handleRunSubCheck}
              disabled={isActionRunning}
              title="Evaluate active movie subscriptions against available schedules"
            >
              <span>🔔</span>
              <span>Run Schedule Match Pass</span>
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{ background: "rgba(239, 68, 68, 0.2)", border: "1px solid rgba(239, 68, 68, 0.5)", color: "#fca5a5", padding: "12px 18px", borderRadius: "var(--radius-md)", marginBottom: "var(--space-lg)" }}>
            ⚠️ {error}
          </div>
        )}

        {/* Section 1: Cinema Providers & Catalogue Coverage (Unified Section with Provider Splits) */}
        <section className={styles.providerSection}>
          <div className={styles.sectionHeaderRow}>
            <div className={styles.sectionTitleGroup}>
              <div className={styles.sectionIconLarge}>🎬</div>
              <div>
                <h2 className={styles.sectionHeading}>Cinema Providers & Catalogue Coverage</h2>
                <p className={styles.sectionSubheading}>
                  Detailed movie inventory, screening schedules, and cinema hall distribution split by cinema operator.
                </p>
              </div>
            </div>
          </div>

          {/* Overall Summary Strip */}
          <div className={styles.overallSummaryStrip}>
            <div className={styles.summaryTile}>
              <span className={styles.summaryTileLabel}>Total Movies</span>
              <span className={styles.summaryTileValue} style={{ color: "#fef08a" }}>
                {stats ? stats.movies.total.toLocaleString() : "--"}
              </span>
            </div>
            <div className={styles.summaryTile}>
              <span className={styles.summaryTileLabel}>Now Showing</span>
              <span className={styles.summaryTileValue} style={{ color: "#86efac" }}>
                {stats ? stats.movies.now_showing.toLocaleString() : "--"}
              </span>
            </div>
            <div className={styles.summaryTile}>
              <span className={styles.summaryTileLabel}>Coming Soon</span>
              <span className={styles.summaryTileValue} style={{ color: "#93c5fd" }}>
                {stats ? stats.movies.coming_soon.toLocaleString() : "--"}
              </span>
            </div>
            <div className={styles.summaryTile}>
              <span className={styles.summaryTileLabel}>Cinema Locations</span>
              <span className={styles.summaryTileValue} style={{ color: "#c084fc" }}>
                {stats ? stats.cinemas.cinemas_count.toLocaleString() : "--"}
              </span>
            </div>
            <div className={styles.summaryTile}>
              <span className={styles.summaryTileLabel}>Active Showtimes</span>
              <span className={styles.summaryTileValue} style={{ color: "#f472b6" }}>
                {stats ? stats.cinemas.schedules_count.toLocaleString() : "--"}
              </span>
            </div>
          </div>

          {/* Provider Breakdown Cards */}
          <div className={styles.providersGrid}>
            {stats && stats.providers && stats.providers.length > 0 ? (
              stats.providers.map((p) => {
                const isGV = p.code === "GV";
                const showingPercent = p.total_movies > 0 ? (p.now_showing / p.total_movies) * 100 : 0;
                const comingPercent = 100 - showingPercent;
                const scheduleShare =
                  stats.cinemas.schedules_count > 0
                    ? ((p.schedules_count / stats.cinemas.schedules_count) * 100).toFixed(1)
                    : "0";
                const avgSchedules =
                  p.cinemas_count > 0 ? (p.schedules_count / p.cinemas_count).toFixed(1) : "0";
                const isShaw = p.code === "SHAW" || p.name.toLowerCase().includes("shaw");

                return (
                  <div
                    key={p.code}
                    className={`${styles.providerCard} ${isShaw ? styles.providerCardShaw : ""}`}
                  >
                    {/* Provider Card Header */}
                    <div className={styles.providerCardHeader}>
                      <div className={styles.providerBrand}>
                        <span className={styles.providerLogoIcon}>{isGV ? "🍿" : "🎟️"}</span>
                        <div>
                          <div className={styles.providerName}>{p.name}</div>
                        </div>
                      </div>
                      <span className={styles.providerCodeBadge}>{p.code}</span>
                    </div>

                    {/* Dual Column Layout: Movie Inventory vs Cinema Coverage */}
                    <div className={styles.providerColumns}>
                      {/* Sub-block 1: Movie Inventory */}
                      <div className={styles.providerSubBlock}>
                        <div className={styles.subBlockHeader}>
                          <span>🎞️ Movie Inventory</span>
                        </div>
                        <div className={styles.subBlockMainNumber}>
                          {p.total_movies}{" "}
                          <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 500, color: "var(--text-muted)" }}>
                            titles
                          </span>
                        </div>

                        <div className={styles.subBlockDetailRow}>
                          <span style={{ color: "#86efac" }}>• Now Showing</span>
                          <span className={styles.subBlockDetailValue} style={{ color: "#86efac" }}>
                            {p.now_showing} ({showingPercent.toFixed(0)}%)
                          </span>
                        </div>

                        <div className={styles.subBlockDetailRow}>
                          <span style={{ color: "#93c5fd" }}>• Coming Soon</span>
                          <span className={styles.subBlockDetailValue} style={{ color: "#93c5fd" }}>
                            {p.coming_soon} ({comingPercent.toFixed(0)}%)
                          </span>
                        </div>

                        {/* Ratio visual track */}
                        <div className={styles.barTrack} title={`Now Showing: ${showingPercent.toFixed(0)}% | Coming Soon: ${comingPercent.toFixed(0)}%`}>
                          <div className={styles.barSegmentShowing} style={{ width: `${showingPercent}%` }} />
                          <div className={styles.barSegmentComing} style={{ width: `${comingPercent}%` }} />
                        </div>
                      </div>

                      {/* Sub-block 2: Cinema & Schedule Coverage */}
                      <div className={styles.providerSubBlock}>
                        <div className={styles.subBlockHeader}>
                          <span>🏢 Cinema Coverage</span>
                        </div>
                        <div className={styles.subBlockMainNumber}>
                          {p.cinemas_count}{" "}
                          <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 500, color: "var(--text-muted)" }}>
                            locations
                          </span>
                        </div>

                        <div className={styles.subBlockDetailRow}>
                          <span>• Showtimes</span>
                          <span className={styles.subBlockDetailValue} style={{ color: "#f472b6" }}>
                            {p.schedules_count.toLocaleString()}
                          </span>
                        </div>

                        <div className={styles.subBlockDetailRow}>
                          <span>• Market Share</span>
                          <span className={styles.subBlockDetailValue} style={{ color: "#c084fc" }}>
                            {scheduleShare}%
                          </span>
                        </div>

                        <div className={styles.subBlockDetailRow}>
                          <span>• Avg / Location</span>
                          <span className={styles.subBlockDetailValue}>
                            ~{avgSchedules}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: "var(--text-secondary)", gridColumn: "1 / -1", padding: 20, textAlign: "center" }}>
                Loading provider breakdown details...
              </div>
            )}
          </div>
        </section>

        {/* Section 2: Platform Analytics & Community */}
        <div className={styles.metricsGrid}>
          {/* Card: Platform Users */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitleGroup}>
                <div className={styles.cardIcon}>👥</div>
                <div className={styles.cardTitle}>Registered Users</div>
              </div>
            </div>
            <div className={styles.cardMainMetric}>
              {stats ? stats.users.total_users.toLocaleString() : "--"}
            </div>
            <div className={styles.breakdownList}>
              <div className={styles.breakdownItem}>
                <span>Admin Accounts</span>
                <span className={styles.breakdownValue} style={{ color: "#fef08a" }}>
                  {stats ? stats.users.admin_count.toLocaleString() : "--"}
                </span>
              </div>
              <div className={styles.breakdownItem}>
                <span>Standard Members</span>
                <span className={styles.breakdownValue}>
                  {stats ? stats.users.member_count.toLocaleString() : "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Card: Screening Tracking Jobs */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitleGroup}>
                <div className={styles.cardIcon}>🔔</div>
                <div className={styles.cardTitle}>Tracking Jobs</div>
              </div>
            </div>
            <div className={styles.cardMainMetric}>
              {stats ? stats.subscriptions.total_jobs.toLocaleString() : "--"}
            </div>
            <div className={styles.breakdownList}>
              <div className={styles.breakdownItem}>
                <span>Active 24/7 Monitorings</span>
                <span className={styles.breakdownValue} style={{ color: "#86efac" }}>
                  {stats ? stats.subscriptions.active_jobs.toLocaleString() : "--"}
                </span>
              </div>
              <div className={styles.breakdownItem}>
                <span>Paused Monitorings</span>
                <span className={styles.breakdownValue} style={{ color: "#fca5a5" }}>
                  {stats ? stats.subscriptions.paused_jobs.toLocaleString() : "--"}
                </span>
              </div>
              <div className={styles.breakdownItem}>
                <span>Triggered Notifications</span>
                <span className={styles.breakdownValue} style={{ color: "#c084fc" }}>
                  {stats ? stats.subscriptions.triggered_count.toLocaleString() : "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Card: Reviews & Ratings */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitleGroup}>
                <div className={styles.cardIcon}>🍿</div>
                <div className={styles.cardTitle}>Community Reviews</div>
              </div>
            </div>
            <div className={styles.cardMainMetric}>
              {stats ? stats.reviews.total_reviews.toLocaleString() : "--"}
            </div>
            <div className={styles.breakdownList}>
              <div className={styles.breakdownItem}>
                <span>System Average Rating</span>
                <span className={styles.breakdownValue} style={{ color: "#facc15" }}>
                  {stats ? `${stats.reviews.average_rating.toFixed(2)} / 5.0 ⭐` : "--"}
                </span>
              </div>
              <div className={styles.breakdownItem}>
                <span>Review Seeder Engine</span>
                <span className={styles.breakdownValue} style={{ color: "#86efac" }}>
                  Context-Aware (4 Tiers)
                </span>
              </div>
            </div>
          </div>

          {/* Card: Infrastructure & Pipeline */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitleGroup}>
                <div className={styles.cardIcon}>⚡</div>
                <div className={styles.cardTitle}>Cache & Pipeline</div>
              </div>
            </div>
            <div className={styles.cardMainMetric}>
              {stats && stats.system.redis_cache_status === "online" ? "Online" : "Degraded"}
            </div>
            <div className={styles.breakdownList}>
              <div className={styles.breakdownItem}>
                <span>Redis Cache Hit Rate</span>
                <span className={styles.breakdownValue} style={{ color: "#86efac" }}>
                  {stats ? `${(stats.system.redis_hit_rate * 100).toFixed(1)}%` : "--"}
                </span>
              </div>
              <div className={styles.breakdownItem}>
                <span>Notification Broker</span>
                <span className={styles.breakdownValue} style={{ color: "#c084fc" }}>
                  Redis Streams
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Infrastructure Status Section */}
        <section className={styles.systemSection}>
          <h2 style={{ fontSize: "var(--font-size-lg)", fontWeight: 700, color: "#ffffff" }}>
            🛡️ Infrastructure & Service Health
          </h2>
          <div className={styles.systemGrid}>
            <div className={styles.systemCard}>
              <div className={styles.systemLabel}>PostgreSQL Database</div>
              <div className={styles.systemValue}>
                <span className={styles.statusDot} />
                <span>Connected (Port 5432)</span>
              </div>
            </div>

            <div className={styles.systemCard}>
              <div className={styles.systemLabel}>Redis Cache & Broker</div>
              <div className={styles.systemValue}>
                <span className={styles.statusDot} />
                <span>Active (Port 6379)</span>
              </div>
            </div>

            <div className={styles.systemCard}>
              <div className={styles.systemLabel}>Notification Consumer</div>
              <div className={styles.systemValue}>
                <span className={styles.statusDot} />
                <span>Stream Consumer (Python)</span>
              </div>
            </div>

            <div className={styles.systemCard}>
              <div className={styles.systemLabel}>REST API Gateway</div>
              <div className={styles.systemValue}>
                <span className={styles.statusDot} />
                <span>CloudWeGo Hertz (Port 8080)</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
