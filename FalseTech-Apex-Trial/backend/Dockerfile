# syntax=docker/dockerfile:1

FROM node:22-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates openssl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci --include=dev

COPY src ./src
COPY tsconfig.json wrangler.toml ./

ENV NODE_ENV=production \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_DIR=/etc/ssl/certs \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

EXPOSE 8787

CMD ["sh", "-c", "npx wrangler dev --local --ip 0.0.0.0 --port 8787 --var TRN_API_KEY:\"$TRN_API_KEY\" --var ALLOWED_ORIGINS:\"$ALLOWED_ORIGINS\""]
