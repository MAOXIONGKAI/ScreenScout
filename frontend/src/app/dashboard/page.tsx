"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import styles from "./page.module.css";

export default function DashboardPage() {
  const { user, isLoading, logout, openAuthModal } = useAuth();
  const router = useRouter();

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
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
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
              Please sign in or create an account to view your user profile and manage your preferences.
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

  return (
    <div className="container">
      <div className={styles.dashboardWrapper}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.badge} style={user.role === "admin" ? { background: "rgba(234, 179, 8, 0.2)", borderColor: "rgba(251, 191, 36, 0.6)", color: "#fef08a" } : undefined}>
            <span>{user.role === "admin" ? "👑 Administrator Account" : "✨ Member Account"}</span>
          </div>
          <h1 className={styles.title}>User Dashboard</h1>
          <p className={styles.subtitle}>
            Manage your ScreenScout profile and screening preferences.
          </p>
        </div>

        {/* Profile Card */}
        <div className={styles.profileCard}>
          <div className={styles.avatarCircle} style={user.role === "admin" ? { background: "linear-gradient(135deg, #eab308, #f59e0b)", color: "#000000" } : undefined}>
            {user.role === "admin" ? "👑" : initials}
          </div>
          <div className={styles.profileInfo}>
            <h2 className={styles.profileUsername}>{user.username}</h2>
            <div className={styles.profileMeta}>
              <span>Role: <strong style={{ color: user.role === "admin" ? "#fef08a" : "#86efac", textTransform: "capitalize" }}>{user.role || "user"}</strong></span>
              <span>•</span>
              <span>Joined: {formatDate(user.created_at)}</span>
            </div>
          </div>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            Log Out
          </button>
        </div>

        {/* Section: Admin Console Link (Admin Only) */}
        {user.role === "admin" && (
          <section className={styles.sectionCard} style={{ border: "1px solid rgba(251, 191, 36, 0.4)" }}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIcon}>👑</div>
              <div>
                <h2 className={styles.sectionTitle}>Administrator Console</h2>
                <p className={styles.sectionSubtitle}>
                  Access platform-level telemetry metrics, user inventories, screening tracking jobs, and server operations.
                </p>
              </div>
            </div>

            <div className={styles.monitoringCtaBox} style={{ background: "rgba(234, 179, 8, 0.1)", borderColor: "rgba(251, 191, 36, 0.3)" }}>
              <p className={styles.monitoringCtaText}>
                View real-time movie counts, registered user base analytics, cache hit rates, and trigger server-side cache invalidation in the <strong>Admin Console</strong>.
              </p>
              <Link
                href="/admin"
                className={styles.goToMonitoringsBtn}
                style={{ background: "linear-gradient(135deg, #eab308, #f59e0b)", color: "#000000", fontWeight: 700 }}
              >
                <span>Open Admin Console</span>
                <span>→</span>
              </Link>
            </div>
          </section>
        )}

        {/* Section: Quick Link to Movie Monitorings */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>🔔</div>
            <div>
              <h2 className={styles.sectionTitle}>Movie Monitorings</h2>
              <p className={styles.sectionSubtitle}>
                Set up automated schedule tracking jobs and manage your Telegram notification settings in the Monitorings center.
              </p>
            </div>
          </div>

          <div className={styles.monitoringCtaBox}>
            <p className={styles.monitoringCtaText}>
              Manage your 24/7 movie screening detection jobs, Telegram handle settings, and triggered history in the dedicated <strong>Monitorings</strong> center.
            </p>
            <Link href="/monitorings" className={styles.goToMonitoringsBtn}>
              <span>Go to Movie Monitorings</span>
              <span>→</span>
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
