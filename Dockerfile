# syntax=docker/dockerfile:1

FROM node:22-slim AS build

WORKDIR /app

COPY FalseTech-Apex-Trial/frontend/package.json FalseTech-Apex-Trial/frontend/package-lock.json ./
RUN npm ci

COPY FalseTech-Apex-Trial/frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY FalseTech-Apex-Trial/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5173

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD wget -qO- http://127.0.0.1:5173/ >/dev/null || exit 1
