/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Rewrites so the frontend can call /api/v1/* without CORS in dev
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
