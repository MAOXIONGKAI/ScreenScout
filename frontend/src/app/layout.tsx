import type { Metadata } from "next";
import "./globals.css";
import ParticleBackground from "@/components/ParticleBackground";
import Navbar from "@/components/Navbar";
import AuthModal from "@/components/AuthModal";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "ScreenScout — Singapore Movie Showtimes",
  description:
    "Real-time movie availability across all major Singapore cinemas. Browse showtimes for Golden Village and Shaw Theatres in one place.",
  keywords: ["movies", "singapore", "cinema", "showtimes", "golden village", "shaw theatres"],
  icons: {
    icon: [
      {
        url: "/brand-icon.svg",
        type: "image/svg+xml",
      },
    ],
    shortcut: ["/brand-icon.svg"],
    apple: [
      {
        url: "/brand-icon.svg",
        type: "image/svg+xml",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/svg+xml" href="/brand-icon.svg" />
        <link rel="shortcut icon" href="/brand-icon.svg" />
        <link rel="apple-touch-icon" href="/brand-icon.svg" />
      </head>
      <body>
        <AuthProvider>
          <ParticleBackground />
          <Navbar />
          <AuthModal />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
