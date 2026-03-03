# Stage 0: Development (used by compose.dev.yaml)
FROM node:20-alpine AS dev
WORKDIR /app
COPY web/package.json ./
RUN npm install
EXPOSE 3000

# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY web/package.json ./
RUN npm install --omit=dev

# Stage 2: Build the application
FROM node:20-alpine AS builder
WORKDIR /app
COPY web/package.json ./
RUN npm install
COPY web/ .
# Run next build directly, bypassing the prebuild/generate step.
# The TypeScript client is generated separately via `make generate`.
RUN npx next build

# Stage 3: Production runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
