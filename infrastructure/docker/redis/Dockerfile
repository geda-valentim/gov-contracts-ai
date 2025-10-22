FROM redis:7-alpine

LABEL maintainer="Gov Contracts AI Team"
LABEL description="Redis 7 for caching and session management"

# Install build dependencies for custom modules (if needed)
RUN apk add --no-cache \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=America/Sao_Paulo

# Create Redis configuration directory
RUN mkdir -p /usr/local/etc/redis

# Copy custom Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Create Redis data directory
RUN mkdir -p /data && \
    chown -R redis:redis /data

# Expose Redis port
EXPOSE 6379

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD redis-cli ping | grep PONG || exit 1

# Run Redis with custom configuration
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
