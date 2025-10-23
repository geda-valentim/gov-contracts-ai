# Dockerfile for OpenSearch
# Search and analytics engine for Gov Contracts AI

FROM opensearchproject/opensearch:3

# Install additional plugins if needed
# RUN /usr/share/opensearch/bin/opensearch-plugin install analysis-icu

# Expose ports
EXPOSE 9200 9300

# Set environment defaults (can be overridden in docker-compose)
ENV discovery.type=single-node
ENV DISABLE_SECURITY_PLUGIN=true
ENV OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9200/_cluster/health || exit 1
