# OpenSearch Docker Configuration

Custom OpenSearch image for search and analytics in Gov Contracts AI.

## Base Image

- **Base**: `opensearchproject/opensearch:3`
- **Mode**: Single-node (development)
- **Security**: Disabled (development only)

## Features

- Full-text search for procurement documents
- Analytics and aggregations
- RESTful API on port 9200
- Inter-node communication on port 9300

## Configuration

- **Discovery Type**: single-node (no cluster setup needed)
- **Security Plugin**: Disabled for easier development
- **Java Heap**: 512MB min/max (adjust via OPENSEARCH_JAVA_OPTS)

## Building the Image

```bash
# From project root
docker compose build opensearch

# Or build and start
docker compose up -d opensearch
```

## Usage

Access OpenSearch REST API at: http://localhost:9201

Test the connection:
```bash
curl http://localhost:9201/_cluster/health
```

## Production Considerations

For production:
1. Enable security plugin
2. Set up multi-node cluster
3. Increase Java heap size
4. Configure proper backup strategy
5. Enable TLS/SSL

## Related Files

- [Dockerfile](Dockerfile) - Image definition
- [/docker-compose.yml](/docker-compose.yml) - Service orchestration
