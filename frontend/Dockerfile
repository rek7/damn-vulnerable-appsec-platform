# syntax=docker/dockerfile:1
# Multi-stage: build the Vite bundle with Node, serve it with nginx.

# ---- build stage ------------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

# Install deps first for layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# Build.
COPY . .
RUN npm run build

# ---- serve stage ------------------------------------------------------------
FROM nginx:1.27-alpine AS serve

# Drop the default site, install ours.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/dvap.conf

# Static build output.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx runs as the unprivileged 'nginx' worker by default; master needs root to
# bind :80 inside the container, which is standard for the official image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
