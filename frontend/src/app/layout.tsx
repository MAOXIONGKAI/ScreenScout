import type { Metadata } from "next";
import "./globals.css";

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
        <header className="header">
          <div className="header-inner">
            <a href="/" className="logo">
              <span className="logo-icon">🎬</span>
              <span>ScreenScout</span>
            </a>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
