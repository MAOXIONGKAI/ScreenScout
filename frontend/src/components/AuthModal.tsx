"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import styles from "./AuthModal.module.css";

export default function AuthModal() {
  const {
    isAuthModalOpen,
    authModalTab,
    closeAuthModal,
    openAuthModal,
    login,
    register,
  } = useAuth();

  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setTab(authModalTab);
    setError("");
    setUsername("");
    setPassword("");
    setConfirmPassword("");
  }, [authModalTab, isAuthModalOpen]);

  if (!isAuthModalOpen) return null;

  const hasMinLength = password.length >= 8;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`§±]/.test(password);
  const isPasswordValid = hasMinLength && hasUpperCase && hasLowerCase && hasSpecialChar;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!username.trim()) {
      setError("Please enter a username");
      return;
    }

    if (tab === "register") {
      if (!isPasswordValid) {
        setError(
          "Password must be at least 8 characters, with 1 uppercase letter, 1 lowercase letter, and 1 special character."
        );
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }
    }

    setLoading(true);
    try {
      if (tab === "login") {
        await login({ username: username.trim(), password });
      } else {
        await register({ username: username.trim(), password });
      }
    } catch (err: any) {
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={styles.overlay}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeAuthModal();
      }}
    >
      <div className={styles.modal}>
        {/* Close Button */}
        <button
          className={styles.closeBtn}
          onClick={closeAuthModal}
          aria-label="Close modal"
        >
          ✕
        </button>

        {/* Tab Switcher */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${tab === "login" ? styles.activeTab : ""}`}
            onClick={() => {
              setTab("login");
              setError("");
            }}
          >
            Sign In
          </button>
          <button
            className={`${styles.tab} ${tab === "register" ? styles.activeTab : ""}`}
            onClick={() => {
              setTab("register");
              setError("");
            }}
          >
            Create Account
          </button>
        </div>

        {/* Title & Subtitle */}
        <h2 className={styles.title}>
          {tab === "login" ? "Welcome Back" : "Join ScreenScout"}
        </h2>
        <p className={styles.subtitle}>
          {tab === "login"
            ? "Sign in to access your saved movies & custom preferences."
            : "Create your free account with a secure password."}
        </p>

        {/* Error Banner */}
        {error && (
          <div className={styles.errorBanner}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Username</label>
            <input
              type="text"
              className={styles.input}
              placeholder="e.g. cinemafan"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Password</label>
            <div className={styles.inputWrapper}>
              <input
                type={showPassword ? "text" : "password"}
                className={styles.input}
                placeholder={
                  tab === "register"
                    ? "Min. 8 chars, Upper, Lower, Special"
                    : "Enter your password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={
                  tab === "login" ? "current-password" : "new-password"
                }
                required
              />
              <button
                type="button"
                className={styles.passwordToggle}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? "👁️" : "👁️‍🗨️"}
              </button>
            </div>

            {/* Password rules checklist for registration */}
            {tab === "register" && (
              <div className={styles.rulesList}>
                <span
                  className={`${styles.ruleChip} ${
                    hasMinLength ? styles.ruleMet : ""
                  }`}
                >
                  {hasMinLength ? "✓" : "○"} 8+ chars
                </span>
                <span
                  className={`${styles.ruleChip} ${
                    hasUpperCase ? styles.ruleMet : ""
                  }`}
                >
                  {hasUpperCase ? "✓" : "○"} 1 Uppercase
                </span>
                <span
                  className={`${styles.ruleChip} ${
                    hasLowerCase ? styles.ruleMet : ""
                  }`}
                >
                  {hasLowerCase ? "✓" : "○"} 1 Lowercase
                </span>
                <span
                  className={`${styles.ruleChip} ${
                    hasSpecialChar ? styles.ruleMet : ""
                  }`}
                >
                  {hasSpecialChar ? "✓" : "○"} 1 Special (!@#$)
                </span>
              </div>
            )}
          </div>

          {tab === "register" && (
            <div className={styles.formGroup}>
              <label className={styles.label}>Confirm Password</label>
              <div className={styles.inputWrapper}>
                <input
                  type={showPassword ? "text" : "password"}
                  className={styles.input}
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : tab === "login"
              ? "Sign In"
              : "Create Account"}
          </button>
        </form>

        {/* Footer switch */}
        <p className={styles.switchText}>
          {tab === "login" ? (
            <>
              Don&apos;t have an account?
              <button
                type="button"
                className={styles.switchLink}
                onClick={() => {
                  setTab("register");
                  setError("");
                }}
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?
              <button
                type="button"
                className={styles.switchLink}
                onClick={() => {
                  setTab("login");
                  setError("");
                }}
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
