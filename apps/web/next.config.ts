import type { NextConfig } from "next";

// When API_PROXY_TARGET is set (e.g. http://<vps-ip>:8080), the dashboard
// proxies /backend/* to it server-side — gives the API an HTTPS same-origin
// path without needing a domain or TLS on the VPS. Pair with
// NEXT_PUBLIC_API_URL=/backend.
const proxyTarget = process.env.API_PROXY_TARGET;

const nextConfig: NextConfig = {
  transpilePackages: ["@voxdesk/shared"],
  async rewrites() {
    return proxyTarget ? [{ source: "/backend/:path*", destination: `${proxyTarget}/:path*` }] : [];
  },
};

export default nextConfig;
