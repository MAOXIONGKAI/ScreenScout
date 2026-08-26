import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import ParticleBackground from "@/components/ParticleBackground";

export const metadata: Metadata = {
  title: "ScreenScout — Singapore Movie Showtimes",
  description:
    "Real-time movie availability across all major Singapore cinemas. Browse showtimes for Golden Village and Shaw Theatres in one place.",
  keywords: ["movies", "singapore", "cinema", "showtimes", "golden village", "shaw theatres"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ParticleBackground />
        <header className="header">
          <div className="header-inner">
            <Link href="/" className="logo">
              <span className="logo-icon">🎬</span>
              <span>ScreenScout</span>
            </Link>
            <nav className="nav-links">
              <Link href="/" className="nav-link">
                Movies
              </Link>
              <Link href="/about" className="nav-link">
                About
              </Link>
            </nav>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
