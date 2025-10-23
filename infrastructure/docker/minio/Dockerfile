FROM minio/minio:RELEASE.2024-10-13T13-34-11Z

LABEL maintainer="Gov Contracts AI Team"
LABEL description="MinIO S3-compatible object storage for Data Lake"

# Create healthcheck script
RUN echo '#!/bin/sh' > /healthcheck.sh && \
    echo 'curl -f http://minio:9000/minio/health/live || exit 1' >> /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose ports
# 9000: S3 API
# 9001: Console UI
EXPOSE 9000 9001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["/healthcheck.sh"]

# Default command (can be overridden in docker-compose)
CMD ["server", "/data", "--console-address", ":9001"]
