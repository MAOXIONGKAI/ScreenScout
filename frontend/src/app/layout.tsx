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
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
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
