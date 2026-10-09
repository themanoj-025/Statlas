# Statlas web — Next.js production image (multi-stage, standalone output)
#
# Stage 1 (deps): install node_modules from the lockfile (reproducible).
# Stage 2 (builder): build the app; NEXT_PUBLIC_STATLAS_API_URL is inlined at
#   build time (client bundles), so pass the PUBLICLY reachable API URL.
# Stage 3 (runner): the standalone server (node server.js) — no node_modules,
#   no build tooling. There is no web/public dir (nothing to copy for it).

# --- deps -------------------------------------------------------------------
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- builder ----------------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_STATLAS_API_URL
ENV NEXT_PUBLIC_STATLAS_API_URL=$NEXT_PUBLIC_STATLAS_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- runner -----------------------------------------------------------------
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
