/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
};

export default nextConfig;
