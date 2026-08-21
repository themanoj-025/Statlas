/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // `output: "standalone"` produces a self-contained server (node server.js)
  // for the production Docker image (web/Dockerfile) — far smaller than
  // shipping node_modules + the full build output.
  output: "standalone",
  // The browser reads the API at NEXT_PUBLIC_STATLAS_API_URL (inlined at build
  // time — must be publicly reachable). Server components read
  // STATLAS_API_URL from the RUNTIME environment via lib/api.ts; it is
  // intentionally not baked here so one image can target different API hosts
  // per environment (e.g. http://api:8000 inside compose).
  env: {
    NEXT_PUBLIC_STATLAS_API_URL:
      process.env.NEXT_PUBLIC_STATLAS_API_URL || "http://127.0.0.1:8000",
  },
  async headers() {
    return [
      {
        // Apply security headers to all routes
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
        ],
      },
      {
        // Cache static assets aggressively
        source: "/_next/static/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
    ];
  },
};

export default nextConfig;
