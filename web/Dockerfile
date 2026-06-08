# LandLynk web. Multi-stage build producing a small standalone Next.js server.
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Build args become public NEXT_PUBLIC_* at build time if needed; runtime secrets
# (Azure AD, worker URL) are read at runtime from the environment.
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# Bind to all interfaces. Next's standalone server otherwise defaults to
# localhost, which makes the container unreachable behind Railway's proxy and
# fails the health check.
ENV HOSTNAME=0.0.0.0
# The standalone output bundles only the files the server needs.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
