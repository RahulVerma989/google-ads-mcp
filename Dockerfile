# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md MANIFEST.in ./
COPY ads_mcp ./ads_mcp

# build-essential is only needed as a fallback for architectures where
# grpcio / protobuf don't ship a prebuilt wheel; we purge it after install
# so it doesn't bloat the final image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && pip install . \
 && apt-get purge -y --auto-remove build-essential \
 && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# FastMCP binds on startup; the port opening is a good enough liveness signal.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import socket,sys; s=socket.socket(); s.settimeout(3); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

CMD ["google-ads-mcp"]
