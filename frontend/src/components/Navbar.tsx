"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import styles from "./Navbar.module.css";

export default function Navbar() {
  const { user, isLoading, openAuthModal, logout } = useAuth();
  const [isScrolled, setIsScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const isMoviesActive = pathname === "/" || pathname.startsWith("/movies");
  const isMonitoringsActive = pathname.startsWith("/monitorings");
  const isAboutActive = pathname.startsWith("/about");
  const isDashboardActive = pathname.startsWith("/dashboard");

  return (
    <header className={`${styles.header} ${isScrolled ? styles.headerScrolled : ""}`}>
      <div className={styles.headerInner}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>🎬</span>
          <span>ScreenScout</span>
        </Link>

        <nav className={styles.navLinks}>
          <Link
            href="/"
            className={`${styles.navLink} ${isMoviesActive ? styles.navLinkActive : ""}`}
          >
            Movies
          </Link>
          <Link
            href="/monitorings"
            className={`${styles.navLink} ${isMonitoringsActive ? styles.navLinkActive : ""}`}
          >
            Monitorings
          </Link>
          <Link
            href="/about"
            className={`${styles.navLink} ${isAboutActive ? styles.navLinkActive : ""}`}
          >
            About
          </Link>

          {/* Auth Controls */}
          {!isLoading && (
            <div className={styles.authGroup}>
              {user ? (
                <>
                  <Link
                    href="/dashboard"
                    className={`${styles.userBadge} ${
                      isDashboardActive ? styles.userBadgeActive : ""
                    }`}
                    title="Open User Dashboard"
                  >
                    <span>👤</span>
                    <span>{user.username}</span>
                  </Link>
                  <button
                    className={styles.logoutBtn}
                    onClick={logout}
                    title="Log out of account"
                  >
                    Log Out
                  </button>
                </>
              ) : (
                <>
                  <button
                    className={styles.signInBtn}
                    onClick={() => openAuthModal("login")}
                  >
                    Sign In
                  </button>
                  <button
                    className={styles.registerBtn}
                    onClick={() => openAuthModal("register")}
                  >
                    Register
                  </button>
                </>
              )}
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
