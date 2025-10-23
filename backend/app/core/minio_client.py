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
import os
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

    Bucket names are read from environment variables to allow flexible configuration.
    """

    # Data Lake buckets - read from environment variables with fallback defaults
    BUCKET_BRONZE = os.getenv("BUCKET_BRONZE", "lh-bronze")
    BUCKET_SILVER = os.getenv("BUCKET_SILVER", "lh-silver")
    BUCKET_GOLD = os.getenv("BUCKET_GOLD", "lh-gold")
    BUCKET_MLFLOW = os.getenv("BUCKET_MLFLOW", "mlflow")
    BUCKET_BACKUPS = os.getenv("BUCKET_BACKUPS", "backups")
    BUCKET_TMP = os.getenv("BUCKET_TMP", "tmp")

    def __init__(
        self,
        endpoint_url: str = "http://minio:9000",
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
        logger.debug(
            f"Using buckets: Bronze={self.BUCKET_BRONZE}, "
            f"Silver={self.BUCKET_SILVER}, Gold={self.BUCKET_GOLD}"
        )

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
        data: Union[Dict, List[Dict], pd.DataFrame],
        source: str,
        date: Optional[datetime] = None,
        filename: Optional[str] = None,
        format: str = "parquet",
    ) -> str:
        """
        Upload raw data to Bronze layer as Parquet (default) or JSON.

        Args:
            data: Raw data (dict, list of dicts, or DataFrame)
            source: Data source name (e.g., 'pncp', 'comprasnet')
            date: Ingestion date (defaults to now)
            filename: Custom filename (auto-generated if None)
            format: Output format ('parquet' or 'json', default: 'parquet')

        Returns:
            S3 object key

        Example:
            >>> # Upload as Parquet (recommended)
            >>> client.upload_to_bronze(
            ...     data=[{"id": 1, "name": "Item 1"}],
            ...     source="pncp",
            ...     date=datetime(2024, 10, 22)
            ... )
            'pncp/year=2024/month=10/day=22/pncp_20241022_123456.parquet'

            >>> # Upload as JSON (legacy)
            >>> client.upload_to_bronze(
            ...     data=[{"id": 1, "name": "Item 1"}],
            ...     source="pncp",
            ...     format="json"
            ... )
        """
        if date is None:
            date = datetime.now()

        # Hive-style partitioning
        partition = (
            f"{source}/year={date.year}/month={date.month:02d}/day={date.day:02d}"
        )

        # Convert to DataFrame if needed
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        record_count = len(df)

        # Generate filename based on format
        if filename is None:
            timestamp = date.strftime("%Y%m%d_%H%M%S")
            extension = "parquet" if format == "parquet" else "json"
            filename = f"{source}_{timestamp}.{extension}"

        object_name = f"{partition}/{filename}"

        # Metadata
        metadata = {
            "source": source,
            "ingestion_date": date.isoformat(),
            "record_count": str(record_count),
            "format": format,
        }

        # Upload based on format
        if format == "parquet":
            # Convert to Parquet
            parquet_buffer = io.BytesIO()
            df.to_parquet(
                parquet_buffer,
                engine="pyarrow",
                compression="snappy",
                index=False,
            )
            parquet_buffer.seek(0)

            logger.info(
                f"Uploading {record_count} records to Bronze as Parquet: {object_name}"
            )
            return self.upload_fileobj(
                parquet_buffer, self.BUCKET_BRONZE, object_name, metadata
            )
        else:
            # Convert to JSON (legacy)
            json_data = df.to_json(orient="records", date_format="iso")
            file_obj = io.BytesIO(json_data.encode("utf-8"))

            logger.info(
                f"Uploading {record_count} records to Bronze as JSON: {object_name}"
            )
            return self.upload_fileobj(
                file_obj, self.BUCKET_BRONZE, object_name, metadata
            )

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

    # ==========================================
    # State Management Operations
    # ==========================================

    def write_json_to_s3(self, bucket: str, key: str, data: Union[Dict, List]) -> str:
        """
        Write JSON data to S3.

        Args:
            bucket: Target bucket name
            key: S3 object key
            data: Data to write (dict or list)

        Returns:
            S3 object key

        Example:
            >>> client.write_json_to_s3(
            ...     'bronze',
            ...     'pncp/_state/state_20251022.json',
            ...     {'processed_ids': ['001', '002']}
            ... )
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            file_obj = io.BytesIO(json_data.encode("utf-8"))

            self.upload_fileobj(file_obj, bucket, key)
            logger.info(f"Wrote JSON to s3://{bucket}/{key}")
            return key

        except Exception as e:
            logger.error(f"Error writing JSON to {key}: {e}")
            raise

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
        instead of using XCom, preventing Airflow database bloat.

        Args:
            data: Data to upload (DataFrame, dict, or list of dicts)
            execution_id: Unique execution identifier (e.g., DAG run ID)
            stage: Stage name (e.g., 'raw', 'transformed')
            format: Data format ('parquet' or 'json', default: 'parquet')

        Returns:
            S3 key for the temporary file

        Example:
            >>> client = MinIOClient()
            >>> key = client.upload_temp(
            ...     data=df,
            ...     execution_id="20251023_120000",
            ...     stage="raw",
            ...     format="parquet"
            ... )
            >>> # Returns: "_temp/20251023_120000/raw.parquet"
        """
        # Generate temporary key
        extension = "parquet" if format == "parquet" else "json"
        temp_key = f"_temp/{execution_id}/{stage}.{extension}"

        # Convert to DataFrame if needed
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported data type for temp upload: {type(data)}")

        # Upload based on format
        if format == "parquet":
            # Upload as Parquet
            buffer = io.BytesIO()
            df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
            buffer.seek(0)
            self.upload_fileobj(buffer, self.BUCKET_BRONZE, temp_key)
            logger.info(
                f"Uploaded temp data (parquet): {len(df)} rows -> {temp_key} "
                f"(size: {buffer.getbuffer().nbytes / 1024:.1f} KB)"
            )
        else:
            # Upload as JSON
            json_data = df.to_json(orient="records", date_format="iso")
            file_obj = io.BytesIO(json_data.encode("utf-8"))
            self.upload_fileobj(file_obj, self.BUCKET_BRONZE, temp_key)
            logger.info(
                f"Uploaded temp data (json): {len(df)} rows -> {temp_key} "
                f"(size: {len(json_data) / 1024:.1f} KB)"
            )

        return temp_key

    def read_temp(self, bucket: str, key: str) -> Union[pd.DataFrame, Dict, List[Dict]]:
        """
        Read temporary data from storage.

        Args:
            bucket: Bucket name
            key: S3 key (from upload_temp)

        Returns:
            Data (DataFrame for parquet, dict/list for JSON)

        Example:
            >>> client = MinIOClient()
            >>> df = client.read_temp(
            ...     bucket=client.BUCKET_BRONZE,
            ...     key="_temp/20251023_120000/raw.parquet"
            ... )
        """
        # Detect format from extension
        if key.endswith(".parquet"):
            df = self.read_parquet_from_s3(bucket, key)
            logger.info(f"Read temp data (parquet): {len(df)} rows from {key}")
            return df
        elif key.endswith(".json"):
            data = self.read_json_from_s3(bucket, key)
            logger.info(f"Read temp data (json): {key}")
            return data
        else:
            raise ValueError(f"Unsupported temp file format: {key}")

    def cleanup_temp(self, execution_id: str, bucket: Optional[str] = None) -> int:
        """
        Clean up temporary files for a specific execution.

        Args:
            execution_id: Execution identifier
            bucket: Bucket to clean (defaults to BUCKET_BRONZE)

        Returns:
            Number of files deleted

        Example:
            >>> client = MinIOClient()
            >>> deleted = client.cleanup_temp("20251023_120000")
            >>> print(f"Deleted {deleted} temporary files")
        """
        if bucket is None:
            bucket = self.BUCKET_BRONZE

        prefix = f"_temp/{execution_id}/"
        deleted = 0

        try:
            # List all objects with this prefix
            objects = self.list_objects(bucket, prefix=prefix)

            if objects:
                # Delete each object
                for obj in objects:
                    try:
                        self.s3_client.delete_object(Bucket=bucket, Key=obj["Key"])
                        deleted += 1
                        logger.debug(f"Deleted temp file: {obj['Key']}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {obj['Key']}: {e}")

                logger.info(
                    f"Cleaned up {deleted} temporary files for execution {execution_id}"
                )
            else:
                logger.info(f"No temporary files found for execution {execution_id}")

        except Exception as e:
            logger.error(f"Error during temp cleanup: {e}")

        return deleted

    def ensure_buckets_exist(self) -> None:
        """
        Ensure all required Data Lake buckets exist.

        Creates buckets if they don't exist yet.
        """
        buckets = [
            self.BUCKET_BRONZE,
            self.BUCKET_SILVER,
            self.BUCKET_GOLD,
            self.BUCKET_MLFLOW,
            self.BUCKET_BACKUPS,
            self.BUCKET_TMP,
        ]

        for bucket in buckets:
            self.create_bucket(bucket)


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
