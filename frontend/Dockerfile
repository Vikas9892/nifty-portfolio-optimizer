# ── Frontend Dockerfile ───────────────────────────────────────────────────────
# Stage 1: Build the React / Vite app
# Stage 2: Serve with Nginx (tiny, no Node runtime in the final image)

# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .

# VITE_API_URL='' means all /api/* calls are relative to the same origin.
# Nginx (in docker-compose) proxies them to the backend container.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy the built React app
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve static files + handle React Router paths
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health.txt 2>/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
