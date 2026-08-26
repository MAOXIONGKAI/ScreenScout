import Link from "next/link";
import styles from "./page.module.css";

export const metadata = {
  title: "About ScreenScout — Singapore Movie Intelligence",
  description:
    "Learn how ScreenScout aggregates real-time movie schedules across Golden Village and Shaw Theatres in Singapore.",
};

export default function AboutPage() {
  return (
    <div className="container">
      <div className={styles.landingPage}>
        {/* Hero Section */}
        <section className={styles.hero}>
          <div className={styles.heroTag}>
            <span>✨ Singapore Cinema Aggregator</span>
          </div>

          <h1 className={styles.heroTitle}>
            All Singapore Cinemas, In One Seamless Place.
          </h1>

          <p className={styles.heroSubtitle}>
            ScreenScout eliminates the hassle of jumping between cinema apps.
            Discover live showtimes, filter by exact schedule windows, and
            explore movies across Singapore&apos;s leading cinema chains.
          </p>

          <div className={styles.heroActions}>
            <Link href="/" className={styles.primaryBtn}>
              🎬 Explore Movies Now
            </Link>
            <a href="#features" className={styles.secondaryBtn}>
              ⚡ View Features
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
              <div className={styles.statValue}>2,300+</div>
              <div className={styles.statLabel}>Daily Showtimes</div>
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
            <p className={styles.sectionTag}>Features</p>
            <h2 className={styles.sectionTitle}>Engineered for Film Lovers</h2>
            <p className={styles.sectionSubtitle}>
              Everything you need to find the right movie at the right time and
              place.
            </p>
          </div>

          <div className={styles.featuresGrid}>
            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🍿</span>
              <h3 className={styles.featureTitle}>Multi-Provider Unification</h3>
              <p className={styles.featureDesc}>
                Golden Village and Shaw Theatres showtimes are scraped and
                normalised into a unified catalogue updated multiple times
                daily.
              </p>
            </div>

            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>⏱️</span>
              <h3 className={styles.featureTitle}>Smart Time Window Filter</h3>
              <p className={styles.featureDesc}>
                Filter screenings by your exact availability. ScreenScout
                computes estimated end times dynamically using movie durations.
              </p>
            </div>

            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>📍</span>
              <h3 className={styles.featureTitle}>Branch & Location Mapping</h3>
              <p className={styles.featureDesc}>
                Quickly narrow down showtimes to your preferred neighbourhood
                cinema — from VivoCity to Bugis+ and Jewel Changi.
              </p>
            </div>

            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🎞️</span>
              <h3 className={styles.featureTitle}>Trailers & Full Metadata</h3>
              <p className={styles.featureDesc}>
                Watch embedded official YouTube trailers, browse casts,
                directors, genres, and link directly to official booking pages.
              </p>
            </div>

            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>⚡</span>
              <h3 className={styles.featureTitle}>Hertz Go High-Speed API</h3>
              <p className={styles.featureDesc}>
                Powered by ByteDance&apos;s cloudwego/hertz Go framework and
                PostgreSQL connection pooling for ultra-fast query execution.
              </p>
            </div>

            <div className={styles.featureCard}>
              <span className={styles.featureIcon}>🌌</span>
              <h3 className={styles.featureTitle}>Ethereal Dark UI</h3>
              <p className={styles.featureDesc}>
                Modern glassmorphic interface with interactive light purple
                particle background physics and responsive dot pagination.
              </p>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionTag}>Architecture</p>
            <h2 className={styles.sectionTitle}>How ScreenScout Works</h2>
            <p className={styles.sectionSubtitle}>
              From automated scrapers to reactive frontend rendering.
            </p>
          </div>

          <div className={styles.pipelineGrid}>
            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>01</span>
              <div className={styles.stepIcon}>🤖</div>
              <h3 className={styles.stepTitle}>Automated Scraping</h3>
              <p className={styles.stepDesc}>
                Python scrapers continuously fetch cinema locations, current
                releases, coming soon titles, and upcoming schedule slots.
              </p>
            </div>

            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>02</span>
              <div className={styles.stepIcon}>🗄️</div>
              <h3 className={styles.stepTitle}>PostgreSQL & Hertz API</h3>
              <p className={styles.stepDesc}>
                Schedules and metadata are stored in PostgreSQL. The Hertz Go
                API performs dynamic filtering, CTE status tags, and pagination.
              </p>
            </div>

            <div className={styles.stepCard}>
              <span className={styles.stepNumber}>03</span>
              <div className={styles.stepIcon}>✨</div>
              <h3 className={styles.stepTitle}>Next.js Reactive UI</h3>
              <p className={styles.stepDesc}>
                Instant search debounce, branch filtering, dot page navigation,
                and cinema schedule grouping delivered smoothly to your browser.
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
              Live tracking across Singapore&apos;s leading entertainment venues.
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
                GV Max, and standard multiplexes across 16 locations.
              </p>
              <div className={styles.cinemaStats}>
                <div>
                  <div className={styles.cinemaStatValue}>16</div>
                  <div className={styles.cinemaStatLabel}>Locations</div>
                </div>
                <div>
                  <div className={styles.cinemaStatValue}>Live</div>
                  <div className={styles.cinemaStatLabel}>Showtimes</div>
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
                Lumiere premium halls, and Dreamers halls across 8 locations.
              </p>
              <div className={styles.cinemaStats}>
                <div>
                  <div className={styles.cinemaStatValue}>8</div>
                  <div className={styles.cinemaStatLabel}>Locations</div>
                </div>
                <div>
                  <div className={styles.cinemaStatValue}>Live</div>
                  <div className={styles.cinemaStatLabel}>Showtimes</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Banner */}
        <section className={styles.ctaBanner}>
          <h2 className={styles.ctaTitle}>Ready for Movie Night?</h2>
          <p className={styles.ctaSubtitle}>
            Browse now playing movies, check timings, and pick your seats.
          </p>
          <Link href="/" className={styles.primaryBtn}>
            🎬 Browse Movies
          </Link>
        </section>
      </div>
    </div>
  );
}
