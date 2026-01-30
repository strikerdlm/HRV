// Author: Dr Diego Malpica MD
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable experimental features for better performance
  experimental: {
    optimizePackageImports: ["lucide-react", "echarts-for-react"],
  },
  // API proxy to FastAPI backend (default: 8180)
  async rewrites() {
    const apiUrl = process.env.API_URL || "http://localhost:8180";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
