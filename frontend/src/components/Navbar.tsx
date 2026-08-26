"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import styles from "./Navbar.module.css";

export default function Navbar() {
  const { user, isLoading, openAuthModal, logout } = useAuth();

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>🎬</span>
          <span>ScreenScout</span>
        </Link>

        <nav className={styles.navLinks}>
          <Link href="/" className={styles.navLink}>
            Movies
          </Link>
          <Link href="/monitorings" className={styles.navLink}>
            Monitorings
          </Link>
          <Link href="/about" className={styles.navLink}>
            About
          </Link>

          {/* Auth Controls */}
          {!isLoading && (
            <div className={styles.authGroup}>
              {user ? (
                <>
                  <Link
                    href="/dashboard"
                    className={styles.userBadge}
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
