import type { NextConfig } from "next";

const api = process.env.API_PROXY_URL;

const nextConfig: NextConfig = {
  async rewrites() {
    if (!api) {
      return [];
    }
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/ping", destination: `${api}/ping` },
      { source: "/invocations", destination: `${api}/invocations` },
    ];
  },
};

export default nextConfig;
