# syntax=docker/dockerfile:1

FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --include=dev

COPY src ./src
COPY tsconfig.json wrangler.toml ./

ENV NODE_ENV=production

EXPOSE 8787

CMD ["sh", "-c", "npx wrangler dev --local --ip 0.0.0.0 --port 8787 --var TRN_API_KEY:\"$TRN_API_KEY\" --var ALLOWED_ORIGINS:\"$ALLOWED_ORIGINS\""]
