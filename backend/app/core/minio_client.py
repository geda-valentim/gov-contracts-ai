"""
MinIO Client for Data Lake Operations.

Provides S3-compatible storage operations for the Data Lake architecture:
- Bronze layer: Raw data (JSON)
- Silver layer: Validated data (Parquet)
- Gold layer: Feature-engineered data (Parquet)
"""

import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Union

import boto3
import pandas as pd
from botocore.client import Config
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO client for Data Lake operations with S3-compatible API.

    Supports the Medallion Architecture:
    - Bronze: Raw data ingestion (JSON, CSV)
    - Silver: Cleaned and validated data (Parquet)
    - Gold: Business-ready aggregated data (Parquet)
    """

    # Data Lake buckets
    BUCKET_BRONZE = "bronze"
    BUCKET_SILVER = "silver"
    BUCKET_GOLD = "gold"
    BUCKET_MLFLOW = "mlflow"
    BUCKET_BACKUPS = "backups"
    BUCKET_TMP = "tmp"

    def __init__(
        self,
        endpoint_url: str = "http://localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        region: str = "us-east-1",
    ):
        """
        Initialize MinIO client.

        Args:
            endpoint_url: MinIO API endpoint
            access_key: Access key ID
            secret_key: Secret access key
            region: AWS region (not used by MinIO but required by boto3)
        """
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

        # Create S3 client
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

        # Create S3 resource for higher-level operations
        self.s3_resource = boto3.resource(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

        logger.info(f"MinIO client initialized: {endpoint_url}")

    # ==========================================
    # Bucket Operations
    # ==========================================

    def list_buckets(self) -> List[str]:
        """List all buckets."""
        try:
            response = self.s3_client.list_buckets()
            return [bucket["Name"] for bucket in response.get("Buckets", [])]
        except ClientError as e:
            logger.error(f"Error listing buckets: {e}")
            raise

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    def create_bucket(self, bucket_name: str) -> bool:
        """Create bucket if it doesn't exist."""
        try:
            if self.bucket_exists(bucket_name):
                logger.info(f"Bucket already exists: {bucket_name}")
                return False

            self.s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Bucket created: {bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            raise

    # ==========================================
    # Object Operations - Generic
    # ==========================================

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_file(
        self,
        file_path: Union[str, Path],
        bucket_name: str,
        object_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to MinIO.

        Args:
            file_path: Path to local file
            bucket_name: Target bucket
            object_name: S3 object name (uses filename if None)
            metadata: Optional metadata dict

        Returns:
            S3 object key
        """
        file_path = Path(file_path)

        if object_name is None:
            object_name = file_path.name

        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.upload_file(
                str(file_path), bucket_name, object_name, ExtraArgs=extra_args or None
            )

            logger.info(f"Uploaded: {file_path} → s3://{bucket_name}/{object_name}")
            return object_name

        except ClientError as e:
            logger.error(f"Error uploading {file_path}: {e}")
            raise

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        bucket_name: str,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file-like object to MinIO.

        Args:
            file_obj: File-like object
            bucket_name: Target bucket
            object_name: S3 object name
            metadata: Optional metadata

        Returns:
            S3 object key
        """
        extra_args: Dict[str, Any] = {}
        if metadata:
            extra_args["Metadata"] = metadata

        # Preserve payload so we can recreate a fresh buffer on retries.
        stream_factory: Optional[Callable[[], BinaryIO]] = None

        if isinstance(file_obj, io.BytesIO):
            payload = file_obj.getvalue()

            def stream_factory() -> io.BytesIO:
                return io.BytesIO(payload)

        elif isinstance(file_obj, (bytes, bytearray)):
            payload = bytes(file_obj)

            def stream_factory() -> io.BytesIO:
                return io.BytesIO(payload)

        else:
            original_obj = file_obj

            def stream_factory() -> BinaryIO:
                if getattr(original_obj, "closed", False):
                    raise ValueError("File object is closed")
                if hasattr(original_obj, "seek"):
                    original_obj.seek(0)
                return original_obj

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        )
        def _upload_with_retry() -> str:
            stream = stream_factory()
            try:
                self.s3_client.upload_fileobj(
                    stream, bucket_name, object_name, ExtraArgs=extra_args or None
                )
                logger.info(f"Uploaded fileobj → s3://{bucket_name}/{object_name}")
                return object_name
            except ClientError as e:
                logger.error(f"Error uploading fileobj: {e}")
                raise
            finally:
                # Close temporary streams created for retries to free memory.
                if stream is not file_obj and hasattr(stream, "close"):
                    try:
                        stream.close()
                    except Exception:
                        pass

        return _upload_with_retry()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def download_file(
        self, bucket_name: str, object_name: str, file_path: Union[str, Path]
    ) -> Path:
        """Download file from MinIO."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.s3_client.download_file(bucket_name, object_name, str(file_path))
            logger.info(f"Downloaded: s3://{bucket_name}/{object_name} → {file_path}")
            return file_path

        except ClientError as e:
            logger.error(f"Error downloading {object_name}: {e}")
            raise

    def get_object(self, bucket_name: str, object_name: str) -> bytes:
        """Get object content as bytes."""
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_name)
            return response["Body"].read()

        except ClientError as e:
            logger.error(f"Error getting object {object_name}: {e}")
            raise

    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """Delete object from MinIO."""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_name)
            logger.info(f"Deleted: s3://{bucket_name}/{object_name}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting {object_name}: {e}")
            raise

    def list_objects(
        self, bucket_name: str, prefix: str = "", max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in bucket with optional prefix.

        Returns:
            List of object metadata dicts
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=prefix, MaxKeys=max_keys
            )

            return response.get("Contents", [])

        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            raise

    # ==========================================
    # Data Lake Operations - Bronze Layer
    # ==========================================

    def upload_to_bronze(
        self,
        data: Union[Dict, List[Dict]],
        source: str,
        date: Optional[datetime] = None,
        filename: Optional[str] = None,
    ) -> str:
        """
        Upload raw data to Bronze layer.

        Args:
            data: Raw data (dict or list of dicts)
            source: Data source name (e.g., 'pncp', 'comprasnet')
            date: Ingestion date (defaults to now)
            filename: Custom filename (auto-generated if None)

        Returns:
            S3 object key

        Example:
            >>> client.upload_to_bronze(
            ...     data=[{"id": 1, "name": "Item 1"}],
            ...     source="pncp",
            ...     date=datetime(2024, 10, 22)
            ... )
            'pncp/year=2024/month=10/day=22/pncp_20241022_123456.json'
        """
        if date is None:
            date = datetime.now()

        # Hive-style partitioning
        partition = (
            f"{source}/year={date.year}/month={date.month:02d}/day={date.day:02d}"
        )

        if filename is None:
            timestamp = date.strftime("%Y%m%d_%H%M%S")
            filename = f"{source}_{timestamp}.json"

        object_name = f"{partition}/{filename}"

        # Convert to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        file_obj = io.BytesIO(json_data.encode("utf-8"))

        # Metadata
        metadata = {
            "source": source,
            "ingestion_date": date.isoformat(),
            "record_count": str(len(data) if isinstance(data, list) else 1),
        }

        return self.upload_fileobj(file_obj, self.BUCKET_BRONZE, object_name, metadata)

    # ==========================================
    # Data Lake Operations - Silver Layer
    # ==========================================

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
            df: Pandas DataFrame with validated data
            table: Table name
            date: Processing date
            partition_cols: Columns to partition by

        Returns:
            S3 object key
        """
        if date is None:
            date = datetime.now()

        timestamp = date.strftime("%Y%m%d_%H%M%S")
        filename = f"{table}_{timestamp}.parquet"

        # Hive-style partitioning
        partition = (
            f"{table}/year={date.year}/month={date.month:02d}/day={date.day:02d}"
        )
        object_name = f"{partition}/{filename}"

        # Convert to Parquet
        parquet_buffer = io.BytesIO()
        df.to_parquet(
            parquet_buffer, engine="pyarrow", compression="snappy", index=False
        )
        parquet_buffer.seek(0)

        # Metadata
        metadata = {
            "table": table,
            "processing_date": date.isoformat(),
            "record_count": str(len(df)),
            "columns": ",".join(df.columns.tolist()),
        }

        return self.upload_fileobj(
            parquet_buffer, self.BUCKET_SILVER, object_name, metadata
        )

    # ==========================================
    # Data Lake Operations - Gold Layer
    # ==========================================

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
            feature_set: Feature set name (e.g., 'price_anomaly_features')
            date: Processing date

        Returns:
            S3 object key
        """
        if date is None:
            date = datetime.now()

        timestamp = date.strftime("%Y%m%d_%H%M%S")
        filename = f"{feature_set}_{timestamp}.parquet"

        # Hive-style partitioning
        partition = (
            f"{feature_set}/year={date.year}/month={date.month:02d}/day={date.day:02d}"
        )
        object_name = f"{partition}/{filename}"

        # Convert to Parquet with optimal compression
        parquet_buffer = io.BytesIO()
        df.to_parquet(
            parquet_buffer,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )
        parquet_buffer.seek(0)

        # Metadata
        metadata = {
            "feature_set": feature_set,
            "processing_date": date.isoformat(),
            "record_count": str(len(df)),
            "feature_count": str(len(df.columns)),
        }

        return self.upload_fileobj(
            parquet_buffer, self.BUCKET_GOLD, object_name, metadata
        )

    # ==========================================
    # Utility Methods
    # ==========================================

    def read_parquet_from_s3(self, bucket_name: str, object_name: str) -> pd.DataFrame:
        """Read Parquet file directly from S3 into DataFrame."""
        try:
            obj = self.s3_client.get_object(Bucket=bucket_name, Key=object_name)
            return pd.read_parquet(io.BytesIO(obj["Body"].read()))

        except ClientError as e:
            logger.error(f"Error reading Parquet {object_name}: {e}")
            raise

    def read_json_from_s3(
        self, bucket_name: str, object_name: str
    ) -> Union[Dict, List]:
        """Read JSON file from S3."""
        try:
            content = self.get_object(bucket_name, object_name)
            return json.loads(content.decode("utf-8"))

        except ClientError as e:
            logger.error(f"Error reading JSON {object_name}: {e}")
            raise

    def get_s3_uri(self, bucket_name: str, object_name: str) -> str:
        """Get S3 URI for object."""
        return f"s3://{bucket_name}/{object_name}"

    def get_presigned_url(
        self, bucket_name: str, object_name: str, expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access.

        Args:
            bucket_name: Bucket name
            object_name: Object key
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return url

        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize client
    client = MinIOClient()

    # Upload to Bronze (raw JSON)
    raw_data = [
        {"licitacao_id": "123", "valor": 50000, "modalidade": "Pregão Eletrônico"},
        {"licitacao_id": "124", "valor": 75000, "modalidade": "Concorrência"},
    ]

    bronze_key = client.upload_to_bronze(
        data=raw_data, source="pncp", date=datetime(2024, 10, 22)
    )
    print(f"Bronze key: {bronze_key}")

    # Upload to Silver (validated Parquet)
    df_silver = pd.DataFrame(raw_data)
    silver_key = client.upload_to_silver(
        df_silver, table="licitacoes", date=datetime(2024, 10, 22)
    )
    print(f"Silver key: {silver_key}")

    # Read back from Silver
    df_read = client.read_parquet_from_s3(client.BUCKET_SILVER, silver_key)
    print(f"\nRead {len(df_read)} records from Silver")
