/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  typescript: {
    // Typecheck is already verified in CI prior to build
    ignoreBuildErrors: true,
  },
  eslint: {
    // Linting is already verified in CI prior to build
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

module.exports = nextConfig;

