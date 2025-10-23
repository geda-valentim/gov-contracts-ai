"""
Business logic services for Gov Contracts AI.

These services are framework-agnostic and can be used independently
or integrated with orchestration frameworks like Airflow.

Organization:
- ingestion/: Services for data ingestion from different sources
  - pncp.py: PNCP API ingestion
- transformation/: Services for data transformation and validation
  - data.py: Data transformation, validation, deduplication

Example standalone usage:
    >>> from backend.app.services.ingestion import PNCPIngestionService
    >>> from backend.app.services.transformation import DataTransformationService
    >>> from backend.app.core.minio_client import MinIOClient
    >>> from datetime import datetime
    >>>
    >>> # Fetch data
    >>> ingestion = PNCPIngestionService()
    >>> result = ingestion.fetch_hourly_incremental(
    ...     execution_date=datetime(2024, 10, 22, 14, 0),
    ...     num_pages=20
    ... )
    >>>
    >>> # Transform
    >>> transformation = DataTransformationService()
    >>> df = transformation.to_dataframe(result['data'])
    >>>
    >>> # Store in Bronze (uses MinIO in dev, S3 in prod)
    >>> from backend.app.core.storage_client import get_storage_client
    >>> storage = get_storage_client()
    >>> s3_key = storage.upload_to_bronze(
    ...     data=result['data'],
    ...     source='pncp',
    ...     date=datetime(2024, 10, 22)
    ... )
"""

from .ingestion import PNCPIngestionService
from .transformation import DataTransformationService

__all__ = [
    "PNCPIngestionService",
    "DataTransformationService",
]
