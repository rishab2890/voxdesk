import type { NextConfig } from "next";

// The dashboard proxies /backend/* to the VoxDesk API server-side, giving the
// API an HTTPS same-origin path without needing a domain or TLS on the VPS.
// Paired with NEXT_PUBLIC_API_URL=/backend (see apps/web/.env.production).
// Override the target with API_PROXY_TARGET when the backend moves.
const proxyTarget = process.env.API_PROXY_TARGET || "http://216.22.13.29:8080";

const nextConfig: NextConfig = {
  transpilePackages: ["@voxdesk/shared"],
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${proxyTarget}/:path*` }];
  },
};

export default nextConfig;
