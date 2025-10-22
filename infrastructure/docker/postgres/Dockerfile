# Use official pgvector image (already includes pg_vector extension)
# Tag format: pg{VERSION}-alpine or pg{VERSION}
FROM pgvector/pgvector:0.8.1-pg16

LABEL maintainer="Gov Contracts AI Team"
LABEL description="PostgreSQL 16 with pg_vector, pg_trgm, and custom extensions for Data Warehouse"

# Create custom PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf
COPY pg_hba.conf /etc/postgresql/pg_hba.conf

# Copy initialization scripts
COPY init-scripts/ /docker-entrypoint-initdb.d/

# Set permissions
RUN chmod -R 755 /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-govcontracts} || exit 1

# Use custom PostgreSQL configuration
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
