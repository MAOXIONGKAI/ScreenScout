import Link from "next/link";
import styles from "./page.module.css";

export const metadata = {
  title: "About ScreenScout — Singapore Movie Intelligence & 24/7 Screening Alerts",
  description:
    "Learn how ScreenScout unifies Singapore cinema showtimes across Golden Village and Shaw Theatres, powers 24/7 screening tracking, and delivers real-time Telegram alerts.",
};

export default function AboutPage() {
  return (
    <div className="container">
      <div className={styles.landingPage}>
        {/* Hero Section */}
        <section className={styles.hero}>
          <div className={styles.heroTag}>
            <span>✨ Singapore Cinema Intelligence & 24/7 Screening Alerts</span>
          </div>

          <h1 className={styles.heroTitle}>
            <span>All Singapore Cinemas</span>
            <span className={styles.heroTitleAmpersand}>&amp;</span>
            <span>24/7 Screening Alerts</span>
            <span className={styles.heroTitlePlace}>in One Place</span>
          </h1>

          <p className={styles.heroSubtitle}>
            ScreenScout eliminates the hassle of jumping between cinema apps.
            Discover live showtimes across Golden Village & Shaw Theatres, filter by your exact schedule windows, and receive instant Telegram alerts the second your favorite movies hit theaters.
          </p>

          <div className={styles.heroActions}>
            <Link href="/" className={styles.primaryBtn}>
              🎬 Explore Movies
            </Link>
            <Link href="/monitorings" className={styles.secondaryBtn}>
              🔔 24/7 Movie Monitorings
            </Link>
            <a
              href="https://t.me/The_ScreenScout_Bot"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.telegramBtn}
            >
              <span>💬 @The_ScreenScout_Bot ↗</span>
            </a>
          </div>

          {/* Stats Strip */}
          <div className={styles.statsStrip}>
            <div className={styles.statItem}>
              <div className={styles.statValue}>24+</div>
              <div className={styles.statLabel}>Cinema Branches</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statValue}>120+</div>
              <div className={styles.statLabel}>Movies Tracked</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statValue}>24/7</div>
              <div className={styles.statLabel}>Automated Alerts</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statValue}>&lt; 10ms</div>
              <div className={styles.statLabel}>Search Latency</div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionTag}>Features & Capabilities</p>
            <h2 className={styles.sectionTitle}>Engineered for Film Lovers</h2>
            <p className={styles.sectionSubtitle}>
              From real-time multi-cinema aggregation to automated 24/7 schedule surveillance.
            </p>
          </div>

          <div className={styles.featuresGrid}>
            {/* Feature 1: Real-time Telegram Notifications */}
            <div className={`${styles.featureCard} ${styles.featureCardHighlight}`}>
              <div className={styles.featureBadge}>NEW</div>
              <span className={styles.featureIcon}>🤖</span>
              <h3 className={styles.featureTitle}>24/7 Telegram Screening Alerts</h3>
              <p className={styles.featureDesc}>
                Connect directly to our official bot (<strong>@The_ScreenScout_Bot</strong>). ScreenScout monitors cinema schedule releases in the background and sends you instant alerts with cinema names, dates, and direct booking links.
              </p>
            </div>

            {/* Feature 2: 3-Tab Task Management */}
            <div className={`${styles.featureCard} ${styles.featureCardHighlight}`}>
              <div className={styles.featureBadge}>NEW</div>
              <span className={styles.featureIcon}>🎯</span>
              <h3 className={styles.featureTitle}>3-Tab Monitoring Hub</h3>
              <p className={styles.featureDesc}>
                Organize tracking tasks effortlessly across <strong>Active Monitoring</strong>, <strong>Disabled Tasks</strong> (paused), and <strong>Triggered History</strong> with on/off pause switches and collapsible matched movie galleries.
              </p>
            </div>

            {/* Feature 3: Safety Net & Quota Engine */}
            <div className={`${styles.featureCard} ${styles.featureCardHighlight}`}>
              <div className={styles.featureBadge}>NEW</div>
              <span className={styles.featureIcon}>🛡️</span>
              <h3 className={styles.featureTitle}>Safety Net & Active Task Limits</h3>
              <p className={styles.featureDesc}>
                Guaranteed high reliability with quota enforcement allowing up to 10 active concurrent monitoring jobs per user, accompanied by interactive floating glassmorphic Toast alerts.
              </p>
            </div>

            {/* Feature 4: Multi-Provider Unification */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🍿</span>
              <h3 className={styles.featureTitle}>Multi-Provider Unification</h3>
              <p className={styles.featureDesc}>
                Golden Village and Shaw Theatres showtimes are scraped and normalised into a unified catalog updated continuously throughout the day.
              </p>
            </div>

            {/* Feature 5: Smart Time Window Filter */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>⏱️</span>
              <h3 className={styles.featureTitle}>Smart Time Window Filter</h3>
              <p className={styles.featureDesc}>
                Filter screenings by your exact availability. ScreenScout computes estimated end times dynamically using movie durations.
              </p>
            </div>

            {/* Feature 6: Safe Deletion Dialogue */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🗑️</span>
              <h3 className={styles.featureTitle}>Safe History Deletion</h3>
              <p className={styles.featureDesc}>
                Prevents accidental data loss with dedicated confirmation dialogues displaying tracked keyword highlights before removing triggered records.
              </p>
            </div>

            {/* Feature 7: Branch & Location Mapping */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>📍</span>
              <h3 className={styles.featureTitle}>Branch & Location Mapping</h3>
              <p className={styles.featureDesc}>
                Narrow down showtimes to your preferred neighborhood cinema — from VivoCity and Bugis+ to PLQ Mall, Nex, and Jewel Changi.
              </p>
            </div>

            {/* Feature 8: Trailers & Full Metadata */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🎞️</span>
              <h3 className={styles.featureTitle}>Trailers & Full Metadata</h3>
              <p className={styles.featureDesc}>
                Watch embedded official YouTube trailers, browse cast, directors, ratings, genres, and link directly to official cinema booking pages.
              </p>
            </div>

            {/* Feature 9: Translucent Dark Theme */}
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🌌</span>
              <h3 className={styles.featureTitle}>Translucent Glass UI & Particles</h3>
              <p className={styles.featureDesc}>
                Modern glassmorphic interface with interactive purple particle physics, scroll-squeezed fixed navbar, and active route navigation pills.
              </p>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionTag}>Architecture & Workflow</p>
            <h2 className={styles.sectionTitle}>How ScreenScout Delivers Alerts</h2>
            <p className={styles.sectionSubtitle}>
              From automated scrapers to instant Telegram messaging.
            </p>
          </div>

          <div className={styles.pipelineGrid}>
            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>01</span>
              <div className={styles.stepIcon}>🤖</div>
              <h3 className={styles.stepTitle}>Continuous Scrapers</h3>
              <p className={styles.stepDesc}>
                Autonomous Python scrapers scan Golden Village and Shaw Theatres every few minutes for new releases, hall updates, and showtime slots.
              </p>
            </div>

            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>02</span>
              <div className={styles.stepIcon}>🗄️</div>
              <h3 className={styles.stepTitle}>Hertz Go Engine & Postgres</h3>
              <p className={styles.stepDesc}>
                High-performance Go backend indexes screenings with CTE status tagging, normalized branch data, and millisecond query execution.
              </p>
            </div>

            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>03</span>
              <div className={styles.stepIcon}>🎯</div>
              <h3 className={styles.stepTitle}>Automated Match Check</h3>
              <p className={styles.stepDesc}>
                Background subscription checker cross-evaluates active keyword subscriptions against freshly scraped screening dates and cinema halls.
              </p>
            </div>

            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>04</span>
              <div className={styles.stepIcon}>💬</div>
              <h3 className={styles.stepTitle}>Instant Telegram Dispatch</h3>
              <p className={styles.stepDesc}>
                The moment a match is detected, <strong>@The_ScreenScout_Bot</strong> dispatches formatted alerts directly to your Telegram chat with direct showtime links.
              </p>
            </div>
          </div>
        </section>

        {/* Supported Cinema Chains */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionTag}>Cinemas</p>
            <h2 className={styles.sectionTitle}>Supported Cinema Chains</h2>
            <p className={styles.sectionSubtitle}>
              Live tracking across Singapore&apos;s leading entertainment exhibitors.
            </p>
          </div>

          <div className={styles.cinemaGrid}>
            <div className={`${styles.cinemaCard} ${styles.cinemaCardGv}`}>
              <span className={`${styles.cinemaBadge} ${styles.cinemaBadgeGv}`}>
                Golden Village
              </span>
              <h3 className={styles.cinemaCardTitle}>Golden Village (GV)</h3>
              <p className={styles.cinemaCardDesc}>
                Singapore&apos;s leading cinema exhibitor featuring Gold Class,
                GV Max, Duo Deluxe, and standard multiplexes across 16 locations.
              </p>
              <div className={styles.cinemaStats}>
                <div>
                  <div className={styles.cinemaStatValue}>16</div>
                  <div className={styles.cinemaStatLabel}>Locations</div>
                </div>
                <div>
                  <div className={styles.cinemaStatValue}>24/7</div>
                  <div className={styles.cinemaStatLabel}>Live Showtimes</div>
                </div>
              </div>
            </div>

            <div className={`${styles.cinemaCard} ${styles.cinemaCardShaw}`}>
              <span
                className={`${styles.cinemaBadge} ${styles.cinemaBadgeShaw}`}
              >
                Shaw Theatres
              </span>
              <h3 className={styles.cinemaCardTitle}>Shaw Theatres</h3>
              <p className={styles.cinemaCardDesc}>
                Singapore&apos;s premier cinema provider with IMAX with Laser,
                Lumiere premium halls, and Dreamers family halls across 8 locations.
              </p>
              <div className={styles.cinemaStats}>
                <div>
                  <div className={styles.cinemaStatValue}>8</div>
                  <div className={styles.cinemaStatLabel}>Locations</div>
                </div>
                <div>
                  <div className={styles.cinemaStatValue}>24/7</div>
                  <div className={styles.cinemaStatLabel}>Live Showtimes</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Banner */}
        <section className={styles.ctaBanner}>
          <h2 className={styles.ctaTitle}>Ready for Movie Night?</h2>
          <p className={styles.ctaSubtitle}>
            Browse now playing movies, set up automated screening alerts, and never miss opening night tickets again.
          </p>
          <div className={styles.ctaActions}>
            <Link href="/" className={styles.primaryBtn}>
              🎬 Browse Movies
            </Link>
            <Link href="/monitorings" className={styles.secondaryBtn}>
              🔔 Track a Movie Now
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
