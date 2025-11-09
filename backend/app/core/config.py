# backend/app/core/config.py
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def is_docker_environment() -> bool:
    """
    Detect if code is running inside a Docker container.

    Returns:
        bool: True if running in Docker, False otherwise
    """
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"


def get_project_root() -> Path:
    """
    Get the project root directory (where .env file is located).

    Returns:
        Path: Absolute path to project root
    """
    # From backend/app/core/config.py -> go up 3 levels to project root
    return Path(__file__).parent.parent.parent.parent.resolve()


class Settings(BaseSettings):
    """
    Application settings with environment-aware defaults.

    Supports hybrid deployments:
    - Docker: Auto-detects and uses Docker service names
    - Localhost: Uses localhost with external ports
    - Remote: Uses custom hostnames from environment variables
    """

    # App
    APP_NAME: str = "Gov Contracts AI"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TZ: str = "America/Sao_Paulo"

    # Database
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "dev123"
    POSTGRES_DB: str = "govcontracts"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        """
        Build PostgreSQL connection URL with environment-aware defaults.

        Priority:
        1. POSTGRES_SERVER from env
        2. Docker service name 'postgres' if in Docker
        3. localhost as fallback
        """
        server = self.POSTGRES_SERVER
        if not server:
            server = "postgres" if is_docker_environment() else "localhost"

        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{server}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        """
        Build Redis connection URL with environment-aware defaults.

        Priority:
        1. REDIS_HOST from env
        2. Docker service name 'redis' if in Docker
        3. localhost as fallback
        """
        host = self.REDIS_HOST
        if not host:
            host = "redis" if is_docker_environment() else "localhost"

        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{host}:{self.REDIS_PORT}"

    # MLflow
    MLFLOW_TRACKING_URI: Optional[str] = None

    def get_mlflow_uri(self) -> str:
        """
        Get MLflow tracking URI with environment-aware defaults.

        Priority:
        1. MLFLOW_TRACKING_URI from env
        2. Docker service name 'http://mlflow:5000' if in Docker
        3. http://localhost:5000 as fallback
        """
        if self.MLFLOW_TRACKING_URI:
            return self.MLFLOW_TRACKING_URI
        return (
            "http://mlflow:5000" if is_docker_environment() else "http://localhost:5000"
        )

    # OpenSearch
    OPENSEARCH_HOST: Optional[str] = None
    OPENSEARCH_PORT: int = 9200
    OPENSEARCH_USER: str = "admin"
    OPENSEARCH_PASSWORD: str = "admin"

    def get_opensearch_url(self) -> str:
        """
        Get OpenSearch URL with environment-aware defaults.

        Priority:
        1. OPENSEARCH_HOST from env
        2. Docker service name 'opensearch' if in Docker
        3. localhost as fallback
        """
        host = self.OPENSEARCH_HOST
        if not host:
            host = "opensearch" if is_docker_environment() else "localhost"

        return f"http://{host}:{self.OPENSEARCH_PORT}"

    # MinIO / S3
    MINIO_ENDPOINT_URL: Optional[str] = None
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_REGION_NAME: str = "us-east-1"

    # MinIO Buckets (Data Lake)
    BUCKET_BRONZE: str = "govcontracts-bronze"
    BUCKET_SILVER: str = "govcontracts-silver"
    BUCKET_GOLD: str = "govcontracts-gold"

    def get_minio_endpoint(self) -> str:
        """
        Get MinIO endpoint with environment-aware defaults.

        Priority:
        1. MINIO_ENDPOINT_URL from env
        2. Docker service name 'http://minio:9000' if in Docker
        3. http://localhost:9000 as fallback
        """
        if self.MINIO_ENDPOINT_URL:
            return self.MINIO_ENDPOINT_URL
        return (
            "http://minio:9000" if is_docker_environment() else "http://localhost:9000"
        )

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None

    # AWS (Production)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None

    class Config:
        # Load from project root .env file
        env_file = str(get_project_root() / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


settings = Settings()
