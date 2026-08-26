"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  fetchNotificationChannel,
  saveNotificationChannel,
} from "@/lib/api";
import { NotificationChannel } from "@/lib/types";
import styles from "./page.module.css";

export default function DashboardPage() {
  const { user, token, isLoading, logout, openAuthModal } = useAuth();
  const router = useRouter();

  // Notification Channel State
  const [channel, setChannel] = useState<NotificationChannel | null>(null);
  const [telegramHandle, setTelegramHandle] = useState("");
  const [savingChannel, setSavingChannel] = useState(false);
  const [channelSuccess, setChannelSuccess] = useState("");
  const [channelError, setChannelError] = useState("");

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

  // Load User Data
  const loadUserData = useCallback(async () => {
    if (!token) return;
    try {
      const ch = await fetchNotificationChannel(token).catch(() => null);
      if (ch) {
        setChannel(ch);
        setTelegramHandle(ch.channel_user_id);
      } else if (user) {
        setTelegramHandle(`@${user.username}`);
      }
    } catch (err) {
      console.error("Error loading dashboard data:", err);
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
          <div className={styles.badge}>
            <span>✨ Member Account</span>
          </div>
          <h1 className={styles.title}>User Dashboard</h1>
          <p className={styles.subtitle}>
            Manage your ScreenScout profile and notification preferences.
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

        {/* Section 2: Quick Link to Movie Monitorings */}
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionIcon}>🔔</div>
            <div>
              <h2 className={styles.sectionTitle}>Movie Monitorings</h2>
              <p className={styles.sectionSubtitle}>
                Set up automated schedule tracking jobs to monitor Singapore cinemas 24/7 for your favorite movies.
              </p>
            </div>
          </div>

          <div className={styles.monitoringCtaBox}>
            <p className={styles.monitoringCtaText}>
              Manage your active subscription jobs and browse triggered screening alerts in the dedicated <strong>Monitorings</strong> center.
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
