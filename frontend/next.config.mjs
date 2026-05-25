/** @type {import('next').NextConfig} */
const nextConfig = {
  trailingSlash: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${process.env.NEXT_PUBLIC_API_BASE || "http://backend:8000"}/api/:path*` },
    ];
  },
};

export default nextConfig;
