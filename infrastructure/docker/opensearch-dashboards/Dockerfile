# Dockerfile for OpenSearch Dashboards
# Visualization and exploration UI for OpenSearch

FROM opensearchproject/opensearch-dashboards:3

# Expose Dashboards port
EXPOSE 5601

# Set environment defaults (can be overridden in docker-compose)
ENV OPENSEARCH_HOSTS='["http://opensearch:9200"]'
ENV DISABLE_SECURITY_DASHBOARDS_PLUGIN=true

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=5 \
    CMD curl -f http://localhost:5601/api/status || exit 1
