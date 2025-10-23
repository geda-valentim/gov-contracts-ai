# Storage Abstraction Layer

This document explains the storage abstraction that allows seamless switching between MinIO (development) and AWS S3 (production).

## Overview

The storage abstraction layer provides a unified interface for object storage operations, allowing the application to work with both MinIO and AWS S3 without code changes.

```python
from backend.app.core.storage_client import get_storage_client

# Automatically uses MinIO in dev, S3 in prod
storage = get_storage_client()
storage.upload_to_bronze(data, source="pncp", date=datetime.now())
```

## Architecture

### Abstract Interface

[`StorageClient`](../backend/app/core/storage_client.py) - Abstract base class defining the interface:

```python
class StorageClient(ABC):
    @abstractmethod
    def upload_to_bronze(data, source, date) -> str: ...

    @abstractmethod
    def upload_to_silver(df, table, date) -> str: ...

    @abstractmethod
    def upload_to_gold(df, feature_set, date) -> str: ...

    @abstractmethod
    def read_json_from_s3(bucket, key): ...

    @abstractmethod
    def read_parquet_from_s3(bucket, key): ...
```

### Implementations

1. **MinIOStorageClient** - For local development
   - Wraps existing `MinIOClient`
   - Uses `minio:9000` by default
   - Credentials: `minioadmin/minioadmin`

2. **S3StorageClient** - For production
   - Uses AWS SDK (boto3)
   - Supports IAM roles
   - Configurable region

## Configuration

### Environment Variables

#### Development (MinIO)

```bash
# .env or .env.local
STORAGE_TYPE=minio
MINIO_ENDPOINT_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

#### Production (S3)

```bash
# .env.production
STORAGE_TYPE=s3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Or use IAM roles (recommended)
STORAGE_TYPE=s3
AWS_REGION=us-east-1
# No keys needed - uses instance role
```

### Bucket Names

Default bucket names (can be customized):
- Bronze: `lh-bronze`
- Silver: `lh-silver`
- Gold: `lh-gold`

## Usage

### Basic Usage

```python
from backend.app.core.storage_client import get_storage_client
from datetime import datetime

# Auto-detect storage type from environment
storage = get_storage_client()

# Upload to Bronze
data = [{"id": "001", "valor": 1000}]
s3_key = storage.upload_to_bronze(
    data=data,
    source="pncp",
    date=datetime.now()
)
print(f"Uploaded to: {s3_key}")
```

### Force Specific Storage

```python
# Force MinIO (useful for testing)
storage = get_storage_client(storage_type='minio')

# Force S3 (useful for production scripts)
storage = get_storage_client(storage_type='s3')
```

### Direct Instantiation

```python
from backend.app.core.storage_client import MinIOStorageClient, S3StorageClient

# MinIO
minio = MinIOStorageClient(
    endpoint_url="http://minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin"
)

# S3
s3 = S3StorageClient(
    region="us-east-1",
    access_key="your_key",
    secret_key="your_secret"
)
```

### In Services

```python
from backend.app.services.ingestion import PNCPIngestionService
from backend.app.services.transformation import DataTransformationService
from backend.app.core.storage_client import get_storage_client

# Fetch data
ingestion = PNCPIngestionService()
result = ingestion.fetch_hourly_incremental(datetime.now(), num_pages=20)

# Transform
transformation = DataTransformationService()
df = transformation.to_dataframe(result['data'])

# Store (automatically uses MinIO or S3)
storage = get_storage_client()
s3_key = storage.upload_to_bronze(
    data=result['data'],
    source='pncp',
    date=datetime.now()
)
```

### In Airflow DAGs

```python
from backend.app.core.storage_client import get_storage_client

def upload_to_bronze(**context):
    data = context["ti"].xcom_pull(...)

    # Uses environment configuration
    storage = get_storage_client()
    s3_key = storage.upload_to_bronze(
        data=data,
        source="pncp",
        date=context["execution_date"]
    )

    return {"s3_key": s3_key, "uploaded": True}
```

## Migration Path

### Current State (Before Abstraction)

```python
# Code was tightly coupled to MinIO
from backend.app.core.minio_client import MinIOClient

minio = MinIOClient()
minio.upload_to_bronze(data, "pncp", datetime.now())
```

**Problems:**
- Hard to switch to S3
- Test code needs MinIO running
- Production requires code changes

### New State (With Abstraction)

```python
# Code works with both MinIO and S3
from backend.app.core.storage_client import get_storage_client

storage = get_storage_client()  # Auto-selects based on env
storage.upload_to_bronze(data, "pncp", datetime.now())
```

**Benefits:**
- ✅ Switch storage with env variable
- ✅ Easy to mock for testing
- ✅ Production-ready without code changes

## Testing

### Unit Tests (Mock Storage)

```python
from unittest.mock import Mock
from backend.app.core.storage_client import StorageClient

def test_ingestion():
    # Mock storage
    mock_storage = Mock(spec=StorageClient)
    mock_storage.upload_to_bronze.return_value = "s3://bucket/key"

    # Test your code
    result = my_function(storage=mock_storage)
    assert result == expected
```

### Integration Tests (MinIO)

```python
from backend.app.core.storage_client import MinIOStorageClient

def test_upload_integration():
    # Use real MinIO for integration tests
    storage = MinIOStorageClient()

    data = [{"id": "test"}]
    s3_key = storage.upload_to_bronze(data, "test", datetime.now())

    # Verify upload
    read_data = storage.read_json_from_s3(storage.BUCKET_BRONZE, s3_key)
    assert read_data == data
```

## Deployment

### Local Development

```bash
# Start MinIO with Docker Compose
docker compose up -d minio

# Application automatically uses MinIO
export STORAGE_TYPE=minio
python scripts/run_pncp_ingestion.py --mode hourly
```

### Staging/Production (AWS)

```bash
# Use S3 with IAM role
export STORAGE_TYPE=s3
export AWS_REGION=us-east-1

# Deploy to ECS - uses instance role automatically
terraform apply -var environment=production
```

### Environment-Specific Configuration

#### docker-compose.yml
```yaml
services:
  backend:
    environment:
      - STORAGE_TYPE=minio
      - MINIO_ENDPOINT_URL=http://minio:9000
```

#### Terraform (ECS)
```hcl
resource "aws_ecs_task_definition" "backend" {
  container_definitions = jsonencode([{
    environment = [
      { name = "STORAGE_TYPE", value = "s3" },
      { name = "AWS_REGION", value = var.aws_region }
    ]
  }])
}
```

## Performance Considerations

### MinIO (Development)
- **Pros**: Fast, local, no network latency
- **Cons**: Not distributed, limited by disk I/O

### S3 (Production)
- **Pros**: Distributed, scalable, durable (99.999999999%)
- **Cons**: Network latency (~50-100ms per operation)

### Optimization Tips

1. **Batch uploads**: Upload larger files instead of many small ones
2. **Multipart upload**: For files > 100MB (implemented in both MinIO and S3)
3. **Compression**: Use Parquet with Snappy compression
4. **Partitioning**: Hive-style partitioning for efficient queries

## Monitoring

### Metrics to Track

```python
import time

storage = get_storage_client()

start = time.time()
s3_key = storage.upload_to_bronze(data, "pncp", datetime.now())
duration = time.time() - start

# Log metrics
logger.info(f"Upload duration: {duration:.2f}s")
logger.info(f"Data size: {len(data)} records")
logger.info(f"Storage type: {type(storage).__name__}")
```

### CloudWatch Metrics (S3)

Enable S3 metrics in AWS Console:
- Request metrics
- Storage metrics
- Replication metrics

### MinIO Metrics

MinIO exposes Prometheus metrics at `/minio/v2/metrics/cluster`:
```bash
curl http://minio:9000/minio/v2/metrics/cluster
```

## Troubleshooting

### Error: "No module named 'boto3'"

```bash
cd backend
poetry add boto3
```

### Error: "Unable to locate credentials"

For S3, ensure either:
1. Environment variables are set (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. IAM role is attached to EC2/ECS instance
3. `~/.aws/credentials` file exists

### Error: "Connection refused" (MinIO)

```bash
# Check if MinIO is running
docker compose ps minio

# Restart if needed
docker compose restart minio

# Check endpoint URL
echo $MINIO_ENDPOINT_URL  # Should be http://minio:9000
```

### Switching between MinIO and S3

```bash
# Switch to MinIO
export STORAGE_TYPE=minio

# Switch to S3
export STORAGE_TYPE=s3

# Verify
python -c "from backend.app.core.storage_client import get_storage_client; print(type(get_storage_client()))"
```

## Future Enhancements

- [ ] Add Azure Blob Storage support
- [ ] Add Google Cloud Storage support
- [ ] Implement automatic retry with exponential backoff
- [ ] Add caching layer for frequent reads
- [ ] Support custom bucket names per environment
- [ ] Add metrics/telemetry integration

## See Also

- [MinIO Client Documentation](../backend/app/core/minio_client.py)
- [Setup Dependencies Guide](setup-dependencies.md)
- [Standalone Services Guide](standalone-services-guide.md)
