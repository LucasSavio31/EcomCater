# syntax=docker/dockerfile:1
# Contexto de build = raiz do monorepo (npm workspaces + @ecom/ui).
FROM node:20-alpine AS deps
WORKDIR /repo
COPY package.json package-lock.json ./
COPY packages/ui/package.json packages/ui/package.json
COPY frontend/package.json frontend/package.json
RUN npm ci

# ---------- dev (hot reload; código vem por bind mount no compose) ----------
FROM node:20-alpine AS dev
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY packages ./packages
COPY frontend ./frontend
WORKDIR /repo/frontend
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---------- build ----------
FROM node:20-alpine AS build
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY packages ./packages
COPY frontend ./frontend
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=frontend

# ---------- prod ----------
FROM node:20-alpine AS prod
WORKDIR /repo
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /repo/node_modules ./node_modules
COPY --from=build /repo/package.json ./package.json
COPY --from=build /repo/packages ./packages
COPY --from=build /repo/frontend ./frontend
WORKDIR /repo/frontend
EXPOSE 3000
CMD ["npm", "run", "start"]
