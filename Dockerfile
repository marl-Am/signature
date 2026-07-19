# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder
# Installs build tools and Python dependencies into a virtual environment.
# Build tools never make it into the final image (OWASP A05 - minimal footprint).
# ---------------------------------------------------------------------------
FROM python:3.13.5-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# build-essential + libffi-dev are needed to compile cryptography / argon2-cffi
# wheels on some platforms. Removed automatically since this stage is discarded.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime
# Slim final image, no compilers, no build tooling, non-root user.
# ---------------------------------------------------------------------------
FROM python:3.13.5-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage only.
COPY --from=builder /opt/venv /opt/venv

# Copy application code. .dockerignore controls what actually lands here -
# secrets, local DB files, tests, and dev tooling are excluded.
COPY . .

# OWASP A05: run as a non-root, unprivileged user rather than the image default (root).
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Render (and most Docker hosts) inject the listen port via $PORT at runtime.
# Falls back to 5000 for local `docker run` testing.
EXPOSE 5000

# Shell form is required here so ${PORT} is expanded at container start,
# not baked in at build time.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 3 --timeout 30 wsgi:app"]