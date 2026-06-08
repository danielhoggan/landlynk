/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The web app is a thin client. Heavy geospatial work runs in the Python
  // worker, never in a Next.js request cycle (CLAUDE.md, architecture rules).
};

export default nextConfig;
