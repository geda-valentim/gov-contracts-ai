"""
Shared client instances for DAGs.

Provides singleton-like access to PNCP and MinIO clients.
"""

import os

# Import from backend (mounted in Docker)
import sys
from typing import Optional

sys.path.insert(0, "/opt/airflow")

from backend.app.core.minio_client import MinIOClient
from backend.app.core.pncp_client import PNCPClient

# Singleton instances (lazy initialization)
_pncp_client: Optional[PNCPClient] = None
_minio_client: Optional[MinIOClient] = None


def get_pncp_client() -> PNCPClient:
    """Get PNCP client singleton."""
    global _pncp_client

    if _pncp_client is None:
        _pncp_client = PNCPClient(rate_limit_delay=float(os.getenv("PNCP_RATE_LIMIT", "0.5")))

    return _pncp_client


def get_minio_client() -> MinIOClient:
    """Get MinIO client singleton."""
    global _minio_client

    if _minio_client is None:
        _minio_client = MinIOClient(
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        )

    return _minio_client
