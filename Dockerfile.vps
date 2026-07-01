# ─── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# ─── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        gettext \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --system platanus \
    && useradd --system --gid platanus --create-home --home-dir /home/platanus platanus

# Install Python packages from builder wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy project source
COPY . .

# Compile translations (msgfmt, no Django env needed)
RUN find locale -name "*.po" -exec sh -c \
      'msgfmt -o "${1%.po}.mo" "$1"' _ {} \;

# Create writable directories and set ownership
RUN mkdir -p src/media staticfiles \
    && chown -R platanus:platanus /app /home/platanus

# Copy and enable entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER platanus

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
