# OpenSearch Dashboards Docker Configuration

Custom OpenSearch Dashboards image for data visualization.

## Base Image

- **Base**: `opensearchproject/opensearch-dashboards:3`
- **Security**: Disabled (development only)

## Features

- Interactive visualizations and dashboards
- Data exploration and querying
- Index pattern management
- Dev Tools for OpenSearch queries

## Configuration

- **OpenSearch Hosts**: Configured to connect to opensearch service
- **Security Plugin**: Disabled for easier development
- **Port**: 5601 (mapped to 5602 on host to avoid conflicts)

## Building the Image

```bash
# From project root
docker compose build opensearch-dashboards

# Or build and start
docker compose up -d opensearch-dashboards
```

## Usage

Access Dashboards UI at: http://localhost:5602

## Use Cases

- Visualize procurement data trends
- Create dashboards for contract analysis
- Explore search results interactively
- Test and debug OpenSearch queries

## Production Considerations

For production:
1. Enable security plugin
2. Configure authentication
3. Set up proper RBAC
4. Enable TLS/SSL
5. Configure proper logging

## Related Files

- [Dockerfile](Dockerfile) - Image definition
- [/docker-compose.yml](/docker-compose.yml) - Service orchestration
