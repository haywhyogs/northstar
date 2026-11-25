# syntax=docker/dockerfile:1
# Customer web page: build the static files with Node, then serve them with nginx (no Node at runtime).
# Build from apps/payments/web:  docker build -t northstar-payments-web:local .

# ---------- Stage 1: build (Node + dev tools; thrown away afterwards) ----------
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# No BuildKit-only features (e.g. RUN --mount), so it also builds with ACR Tasks' classic builder.
RUN npm ci
COPY . .
RUN npm run build

# ---------- Stage 2: runtime (nginx only, runs as a non-root user on port 8080) ----------
# Supported nginx line: 1.27 stopped receiving updates in 2025, so its OS packages had unpatched critical CVEs.
FROM nginxinc/nginx-unprivileged:1.30-alpine
# Apply any OS security fixes released since the base image was published, then drop back to the non-root user.
USER root
RUN apk upgrade --no-cache
USER 101
# Where to forward /api requests. Kubernetes Service name or Compose service name of the backend API.
ENV API_UPSTREAM=api:8000
# nginx fills ${API_UPSTREAM} into this template when the container starts.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
