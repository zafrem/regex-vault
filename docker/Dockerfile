# Multi-stage Dockerfile for regex-vault
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY patterns/ patterns/
COPY schemas/ schemas/
COPY README.md .
COPY LICENSE .

# Install package and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 regexvault && \
    chown -R regexvault:regexvault /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/regex-vault /usr/local/bin/regex-vault

# Copy patterns and config
COPY --chown=regexvault:regexvault patterns/ /app/patterns/
COPY --chown=regexvault:regexvault schemas/ /app/schemas/
COPY --chown=regexvault:regexvault config.yml /app/config.yml

# Switch to non-root user
USER regexvault

# Expose ports
EXPOSE 8080
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Default command
CMD ["regex-vault", "serve", "--config", "/app/config.yml", "--host", "0.0.0.0", "--port", "8080"]
