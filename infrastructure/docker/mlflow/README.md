# MLflow Docker Configuration

Custom MLflow image with PostgreSQL backend support.

## Base Image

- **Base**: `ghcr.io/mlflow/mlflow:v2.10.0`
- **Additional dependencies**: PostgreSQL client library

## Features

- MLflow tracking server with PostgreSQL backend
- Artifact storage via MinIO (S3-compatible)
- Web UI on port 5000

## Custom Dependencies

- **psycopg2-binary**: PostgreSQL adapter for tracking backend

## Building the Image

```bash
# From project root
docker compose build mlflow

# Or build and start
docker compose up -d mlflow
```

## Configuration

MLflow is configured via environment variables in docker-compose.yml:
- `MLFLOW_BACKEND_STORE_URI`: PostgreSQL connection for tracking
- `MLFLOW_ARTIFACT_ROOT`: MinIO S3 location for artifacts

## Usage

Access MLflow UI at: http://localhost:5000

## Related Files

- [Dockerfile](Dockerfile) - Image definition
- [/docker-compose.yml](/docker-compose.yml) - Service orchestration
