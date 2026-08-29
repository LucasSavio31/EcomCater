# syntax=docker/dockerfile:1
# Contexto de build = raiz do monorepo (npm workspaces + @ecom/ui).
FROM node:20-alpine AS deps
WORKDIR /repo
COPY package.json package-lock.json ./
COPY packages/ui/package.json packages/ui/package.json
COPY admin/package.json admin/package.json
RUN npm ci

# ---------- dev ----------
FROM node:20-alpine AS dev
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY packages ./packages
COPY admin ./admin
WORKDIR /repo/admin
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3001
CMD ["npm", "run", "dev"]

# ---------- build ----------
FROM node:20-alpine AS build
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY packages ./packages
COPY admin ./admin
ARG NEXT_PUBLIC_ADMIN_API_URL
ARG NEXT_PUBLIC_ADMIN_BASE_PATH
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=admin

# ---------- prod ----------
FROM node:20-alpine AS prod
WORKDIR /repo
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /repo/node_modules ./node_modules
COPY --from=build /repo/package.json ./package.json
COPY --from=build /repo/packages ./packages
COPY --from=build /repo/admin ./admin
WORKDIR /repo/admin
EXPOSE 3001
CMD ["npm", "run", "start"]
