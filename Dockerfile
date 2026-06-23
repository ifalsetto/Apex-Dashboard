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
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    APEX_DASHBOARD_DATA_DIR=/data

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=app:app . .
RUN mkdir -p /data \
    && chown -R app:app /app /data

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5).read()"

CMD ["streamlit", "run", "apex_dashboard.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
