# Airflow Docker Configuration

Custom Apache Airflow image with additional dependencies for Gov Contracts AI pipelines.

## Base Image

- **Base**: `apache/airflow:3.1.0-python3.11`
- **Custom dependencies**: See [requirements.txt](requirements.txt)

## Custom Dependencies

The image includes additional Python packages required for DAGs:

### Data Processing
- **pandas**: DataFrame operations
- **pyarrow**: Parquet file handling
- **python-dateutil**: Date/time utilities

### Object Storage
- **boto3**: AWS S3 / MinIO client
- **s3fs**: S3 filesystem for pandas

### Data Validation
- **great-expectations**: Data quality checks

### Database
- **psycopg2-binary**: PostgreSQL adapter
- **sqlalchemy**: Database ORM

### Utilities
- **pydantic**: Data validation
- **python-dotenv**: Environment configuration
- **tenacity**: Retry logic for API calls
- **requests**: HTTP client

## Building the Image

The image is built automatically when running:

```bash
# From project root
docker compose build airflow-webserver

# Or build all services
docker compose build
```

## Updating Dependencies

To add new dependencies:

1. Edit [requirements.txt](requirements.txt)
2. Rebuild the image:
   ```bash
   docker compose build airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
   ```
3. Restart services:
   ```bash
   docker compose up -d
   ```

## Image Size Optimization

The Dockerfile uses:
- `--no-cache-dir` for pip to reduce layer size
- `apt-get clean` to remove package cache
- Multi-stage pattern could be added for further optimization

## Security Considerations

- Base image is from official Apache Airflow repository
- All dependencies are pinned to specific versions
- System packages are kept minimal
- Image runs as `airflow` user (non-root)

## Related Files

- [Dockerfile](Dockerfile) - Image definition
- [requirements.txt](requirements.txt) - Python dependencies
- [/airflow/dags/](/airflow/dags/) - DAG definitions
- [/docker-compose.yml](/docker-compose.yml) - Service orchestration
