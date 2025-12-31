"""
Storage Client - Abstract interface for object storage.

This abstraction allows switching between MinIO (development) and AWS S3 (production)
without changing application code.

Usage:
    from backend.app.core.storage_client import get_storage_client
    from backend.app.core.datetime_utils import get_now_sao_paulo

    # Automatically selects MinIO or S3 based on configuration
    storage = get_storage_client()
    storage.upload_to_bronze(data, source="pncp", date=get_now_sao_paulo())
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# Import timezone utilities
try:
    from backend.app.core.datetime_utils import (
        get_now_sao_paulo,
        to_sao_paulo,
        format_datetime,
    )
except ImportError:
    # Fallback if datetime_utils not available (shouldn't happen)
    def get_now_sao_paulo():
        from datetime import timezone, timedelta

        return datetime.now(timezone(timedelta(hours=-3)))

    def to_sao_paulo(dt):
        return dt if dt else get_now_sao_paulo()

    def format_datetime(dt=None):
        dt = dt or get_now_sao_paulo()
        return dt.strftime("%Y%m%d_%H%M%S")


class StorageClient(ABC):
    """
    Abstract base class for object storage operations.

    Implementations:
    - MinIOStorageClient: For local development with MinIO
    - S3StorageClient: For production with AWS S3

    Bucket names are read from environment variables to allow flexible configuration.
    """

    # Bucket names - read from environment variables with fallback defaults
    BUCKET_BRONZE = os.getenv("BUCKET_BRONZE", "lh-bronze")
    BUCKET_SILVER = os.getenv("BUCKET_SILVER", "lh-silver")
    BUCKET_GOLD = os.getenv("BUCKET_GOLD", "lh-gold")

    @abstractmethod
    def upload_to_bronze(
        self,
        data: Union[Dict, List[Dict], Any],
        source: str,
        date: Optional[datetime] = None,
        filename: Optional[str] = None,
        format: str = "parquet",
    ) -> str:
        """
        Upload raw data to Bronze layer as Parquet (default) or JSON.

        Args:
            data: Raw data (dict, list of dicts, or DataFrame)
            source: Data source name (e.g., 'pncp')
            date: Ingestion date (defaults to now)
            filename: Custom filename (auto-generated if None)
            format: Output format ('parquet' or 'json', default: 'parquet')

        Returns:
            S3 object key
        """
        pass

    @abstractmethod
    def upload_to_silver(
        self,
        df: pd.DataFrame,
        table: str,
        date: Optional[datetime] = None,
        partition_cols: Optional[List[str]] = None,
    ) -> str:
        """
        Upload validated data to Silver layer as Parquet.

        Args:
            df: pandas DataFrame with validated data
            table: Table name
            date: Processing date
            partition_cols: Columns to partition by

        Returns:
            S3 object key
        """
        pass

    @abstractmethod
    def upload_to_gold(
        self,
        df: pd.DataFrame,
        feature_set: str,
        date: Optional[datetime] = None,
    ) -> str:
        """
        Upload feature-engineered data to Gold layer.

        Args:
            df: DataFrame with features
            feature_set: Feature set name
            date: Processing date

        Returns:
            S3 object key
        """
        pass

    @abstractmethod
    def read_json_from_s3(self, bucket: str, key: str) -> Union[Dict, List[Dict]]:
        """Read JSON data from storage."""
        pass

    @abstractmethod
    def read_parquet_from_s3(self, bucket: str, key: str) -> pd.DataFrame:
        """Read Parquet data from storage."""
        pass

    @abstractmethod
    def list_objects(
        self, bucket: str, prefix: str = "", max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """List objects in a bucket."""
        pass

    @abstractmethod
    def ensure_buckets_exist(self) -> None:
        """Ensure all required buckets exist."""
        pass

    @abstractmethod
    def write_json_to_s3(self, bucket: str, key: str, data) -> str:
        """Write JSON data to storage."""
        pass

    @abstractmethod
    def upload_temp(
        self,
        data: Union[pd.DataFrame, Dict, List[Dict]],
        execution_id: str,
        stage: str,
        format: str = "parquet",
    ) -> str:
        """
        Upload temporary data for inter-task communication.

        This method stores intermediate data in a temporary location
        instead of using XCom, preventing database bloat.

        Args:
            data: Data to upload (DataFrame, dict, or list of dicts)
            execution_id: Unique execution identifier (e.g., DAG run ID)
            stage: Stage name (e.g., 'raw', 'transformed')
            format: Data format ('parquet' or 'json', default: 'parquet')

        Returns:
            S3 key for the temporary file

        Example:
            >>> storage = get_storage_client()
            >>> key = storage.upload_temp(
            ...     data=df,
            ...     execution_id="20251023_120000",
            ...     stage="raw",
            ...     format="parquet"
            ... )
            >>> # Returns: "_temp/20251023_120000/raw.parquet"
        """
        pass

    @abstractmethod
    def read_temp(self, bucket: str, key: str) -> Union[pd.DataFrame, Dict, List[Dict]]:
        """
        Read temporary data from storage.

        Args:
            bucket: Bucket name
            key: S3 key (from upload_temp)

        Returns:
            Data (DataFrame for parquet, dict/list for JSON)

        Example:
            >>> storage = get_storage_client()
            >>> df = storage.read_temp(
            ...     bucket=storage.BUCKET_BRONZE,
            ...     key="_temp/20251023_120000/raw.parquet"
            ... )
        """
        pass

    @abstractmethod
    def cleanup_temp(self, execution_id: str, bucket: Optional[str] = None) -> int:
        """
        Clean up temporary files for a specific execution.

        Args:
            execution_id: Execution identifier
            bucket: Bucket to clean (defaults to BUCKET_BRONZE)

        Returns:
            Number of files deleted

        Example:
            >>> storage = get_storage_client()
            >>> deleted = storage.cleanup_temp("20251023_120000")
            >>> print(f"Deleted {deleted} temporary files")
        """
        pass

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> bool:
        """
        Delete a single object from storage.

        Args:
            bucket: Bucket name
            key: Object key to delete

        Returns:
            True if deleted successfully
        """
        pass


class MinIOStorageClient(StorageClient):
    """
    MinIO implementation of StorageClient.

    Used for local development and testing.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize MinIO storage client.

        Args:
            endpoint_url: MinIO endpoint (defaults to env MINIO_ENDPOINT_URL)
            access_key: Access key (defaults to env MINIO_ACCESS_KEY)
            secret_key: Secret key (defaults to env MINIO_SECRET_KEY)
        """
        from backend.app.core.minio_client import MinIOClient

        self._client = MinIOClient(
            endpoint_url=endpoint_url
            or os.getenv("MINIO_ENDPOINT_URL", "http://minio:9000"),
            access_key=access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        )

    def upload_to_bronze(
        self, data, source, date=None, filename=None, format="parquet"
    ) -> str:
        return self._client.upload_to_bronze(data, source, date, filename, format)

    def upload_to_silver(self, df, table, date=None, partition_cols=None) -> str:
        return self._client.upload_to_silver(df, table, date, partition_cols)

    def upload_to_gold(self, df, feature_set, date=None) -> str:
        return self._client.upload_to_gold(df, feature_set, date)

    def read_json_from_s3(self, bucket, key):
        return self._client.read_json_from_s3(bucket, key)

    def read_parquet_from_s3(self, bucket, key):
        return self._client.read_parquet_from_s3(bucket, key)

    def list_objects(self, bucket, prefix="", max_keys=1000):
        return self._client.list_objects(bucket, prefix, max_keys)

    def ensure_buckets_exist(self):
        return self._client.ensure_buckets_exist()

    def write_json_to_s3(self, bucket, key, data):
        return self._client.write_json_to_s3(bucket, key, data)

    def upload_temp(self, data, execution_id, stage, format="parquet") -> str:
        return self._client.upload_temp(data, execution_id, stage, format)

    def read_temp(self, bucket, key):
        return self._client.read_temp(bucket, key)

    def cleanup_temp(self, execution_id, bucket=None):
        return self._client.cleanup_temp(execution_id, bucket)

    def delete_object(self, bucket, key):
        """Delete a single object from storage."""
        return self._client.delete_object(bucket, key)


class S3StorageClient(StorageClient):
    """
    AWS S3 implementation of StorageClient.

    Used for production deployment.
    """

    def __init__(
        self,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize S3 storage client.

        Args:
            region: AWS region (defaults to env AWS_REGION)
            access_key: AWS access key (defaults to env AWS_ACCESS_KEY_ID)
            secret_key: AWS secret key (defaults to env AWS_SECRET_ACCESS_KEY)
        """
        import boto3

        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def upload_to_bronze(
        self, data, source, date=None, filename=None, format="parquet"
    ) -> str:
        """Upload to S3 Bronze layer as Parquet (default) or JSON."""
        import io

        # Ensure timezone-aware date in São Paulo timezone
        if date is None:
            date = get_now_sao_paulo()
        else:
            date = to_sao_paulo(date)

        # Convert to DataFrame if needed
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Generate S3 key with Hive partitioning (using São Paulo timezone)
        if filename is None:
            timestamp = format_datetime(date)
            extension = "parquet" if format == "parquet" else "json"
            filename = f"{source}_{timestamp}.{extension}"

        s3_key = (
            f"{source}/year={date.year}/month={date.month:02d}/"
            f"day={date.day:02d}/{filename}"
        )

        # Upload based on format
        if format == "parquet":
            # Convert to Parquet bytes
            buffer = io.BytesIO()
            df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
            buffer.seek(0)

            self.s3_client.put_object(
                Bucket=self.BUCKET_BRONZE,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType="application/x-parquet",
            )
        else:
            # Convert to JSON bytes (legacy)
            json_data = df.to_json(orient="records", date_format="iso")
            json_bytes = json_data.encode("utf-8")

            self.s3_client.put_object(
                Bucket=self.BUCKET_BRONZE,
                Key=s3_key,
                Body=json_bytes,
                ContentType="application/json",
            )

        return s3_key

    def upload_to_silver(self, df, table, date=None, partition_cols=None) -> str:
        """Upload to S3 Silver layer."""
        import io

        # Ensure timezone-aware date in São Paulo timezone
        if date is None:
            date = get_now_sao_paulo()
        else:
            date = to_sao_paulo(date)

        timestamp = format_datetime(date)
        s3_key = (
            f"{table}/year={date.year}/month={date.month:02d}/"
            f"day={date.day:02d}/{table}_{timestamp}.parquet"
        )

        # Convert DataFrame to Parquet bytes
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
        buffer.seek(0)

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.BUCKET_SILVER,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType="application/x-parquet",
        )

        return s3_key

    def upload_to_gold(self, df, feature_set, date=None) -> str:
        """Upload to S3 Gold layer."""
        import io

        # Ensure timezone-aware date in São Paulo timezone
        if date is None:
            date = get_now_sao_paulo()
        else:
            date = to_sao_paulo(date)

        timestamp = format_datetime(date)
        s3_key = (
            f"{feature_set}/year={date.year}/month={date.month:02d}/"
            f"day={date.day:02d}/{feature_set}_{timestamp}.parquet"
        )

        # Convert DataFrame to Parquet bytes
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
        buffer.seek(0)

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.BUCKET_GOLD,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType="application/x-parquet",
        )

        return s3_key

    def read_json_from_s3(self, bucket, key):
        """Read JSON from S3."""
        import json

        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def read_parquet_from_s3(self, bucket, key):
        """Read Parquet from S3."""
        import io

        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return pd.read_parquet(io.BytesIO(response["Body"].read()))

    def list_objects(self, bucket, prefix="", max_keys=1000):
        """List objects in S3 bucket."""
        response = self.s3_client.list_objects_v2(
            Bucket=bucket, Prefix=prefix, MaxKeys=max_keys
        )

        objects = []
        for obj in response.get("Contents", []):
            objects.append(
                {
                    "Key": obj["Key"],
                    "Size": obj["Size"],
                    "LastModified": obj["LastModified"].isoformat(),
                    "ETag": obj["ETag"],
                }
            )

        return objects

    def ensure_buckets_exist(self):
        """Ensure all required S3 buckets exist."""
        for bucket in [self.BUCKET_BRONZE, self.BUCKET_SILVER, self.BUCKET_GOLD]:
            try:
                self.s3_client.head_bucket(Bucket=bucket)
            except Exception:
                # Create bucket if it doesn't exist
                self.s3_client.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": self.region}
                    if self.region != "us-east-1"
                    else {},
                )

    def write_json_to_s3(self, bucket, key, data):
        """Write JSON data to S3."""
        import json

        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        self.s3_client.put_object(
            Bucket=bucket, Key=key, Body=json_bytes, ContentType="application/json"
        )

        return key

    def upload_temp(self, data, execution_id, stage, format="parquet") -> str:
        """Upload temporary data to S3."""
        import io

        # Generate temporary key
        extension = "parquet" if format == "parquet" else "json"
        temp_key = f"_temp/{execution_id}/{stage}.{extension}"

        # Convert to DataFrame if needed
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, (list, dict)):
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported data type for temp upload: {type(data)}")

        # Upload based on format
        if format == "parquet":
            buffer = io.BytesIO()
            df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
            buffer.seek(0)

            self.s3_client.put_object(
                Bucket=self.BUCKET_BRONZE,
                Key=temp_key,
                Body=buffer.getvalue(),
                ContentType="application/x-parquet",
            )
        else:
            json_data = df.to_json(orient="records", date_format="iso")
            json_bytes = json_data.encode("utf-8")

            self.s3_client.put_object(
                Bucket=self.BUCKET_BRONZE,
                Key=temp_key,
                Body=json_bytes,
                ContentType="application/json",
            )

        return temp_key

    def read_temp(self, bucket, key):
        """Read temporary data from S3."""
        import io

        # Detect format from extension
        if key.endswith(".parquet"):
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return pd.read_parquet(io.BytesIO(response["Body"].read()))
        elif key.endswith(".json"):
            return self.read_json_from_s3(bucket, key)
        else:
            raise ValueError(f"Unsupported temp file format: {key}")

    def cleanup_temp(self, execution_id, bucket=None):
        """Clean up temporary files from S3."""
        if bucket is None:
            bucket = self.BUCKET_BRONZE

        prefix = f"_temp/{execution_id}/"
        deleted = 0

        try:
            # List all objects with this prefix
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

            if "Contents" in response:
                # Delete all objects
                objects_to_delete = [
                    {"Key": obj["Key"]} for obj in response["Contents"]
                ]

                if objects_to_delete:
                    self.s3_client.delete_objects(
                        Bucket=bucket, Delete={"Objects": objects_to_delete}
                    )
                    deleted = len(objects_to_delete)

        except Exception as e:
            print(f"Warning: Failed to cleanup temp files: {e}")

        return deleted

    def delete_object(self, bucket, key):
        """Delete a single object from S3."""
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception as e:
            print(f"Warning: Failed to delete {key}: {e}")
            return False


def get_storage_client(
    storage_type: Optional[str] = None,
) -> StorageClient:
    """
    Factory function to get the appropriate storage client.

    Automatically selects MinIO for development and S3 for production
    based on environment variables.

    Args:
        storage_type: Force specific storage type ('minio' or 's3')
                     If None, auto-detects based on STORAGE_TYPE env var

    Returns:
        StorageClient instance (MinIO or S3)

    Environment Variables:
        STORAGE_TYPE: 'minio' or 's3' (defaults to 'minio')
        MINIO_ENDPOINT_URL: MinIO endpoint
        MINIO_ACCESS_KEY: MinIO access key
        MINIO_SECRET_KEY: MinIO secret key
        AWS_REGION: AWS region for S3
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key

    Example:
        >>> # Auto-detect based on environment
        >>> storage = get_storage_client()
        >>>
        >>> # Force MinIO
        >>> storage = get_storage_client(storage_type='minio')
        >>>
        >>> # Force S3
        >>> storage = get_storage_client(storage_type='s3')
    """
    if storage_type is None:
        storage_type = os.getenv("STORAGE_TYPE", "minio").lower()

    if storage_type == "s3":
        return S3StorageClient()
    elif storage_type == "minio":
        return MinIOStorageClient()
    else:
        raise ValueError(
            f"Invalid storage_type: {storage_type}. Must be 'minio' or 's3'"
        )


# Convenience exports
__all__ = [
    "StorageClient",
    "MinIOStorageClient",
    "S3StorageClient",
    "get_storage_client",
]
