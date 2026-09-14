import { networkInterfaces } from "os";

import type { NextConfig } from "next";

const api =
  process.env.API_PROXY_URL ??
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8080" : undefined);

function lanHosts(): string[] {
  const hosts = ["127.0.0.1"];
  for (const addrs of Object.values(networkInterfaces())) {
    for (const addr of addrs ?? []) {
      if ((addr.family === "IPv4" || addr.family === 4) && !addr.internal) {
        hosts.push(addr.address);
      }
    }
  }
  return hosts;
}

const nextConfig: NextConfig = {
  allowedDevOrigins: lanHosts(),
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
