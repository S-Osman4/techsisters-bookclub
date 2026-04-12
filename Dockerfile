# Dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
FROM base AS python-deps

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Frontend build ────────────────────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY tailwind.config.js tsconfig.json ./
COPY app/static/src ./app/static/src
COPY app/templates   ./app/templates

RUN npm run build

# ── Final image ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages \
    /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy compiled frontend assets
COPY --from=frontend-build /app/app/static/dist ./app/static/dist

# Copy application code
COPY app ./app
COPY run.py seed.py ./

# Create non-root user
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=10s \
    --start-period=10s \
    --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "run.py", "--prod"]