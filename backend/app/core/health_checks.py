"""
Health check utilities for external service dependencies.

This module provides functions to verify that required external services
(PostgreSQL, Redis, MinIO, OpenSearch) are available before attempting
to connect to them.

Prevents:
- Connection errors from services not running
- Unnecessary Docker restarts
- Confusing error messages

Usage:
    from app.core.health_checks import check_required_services, ensure_services_available

    # Check all services
    if not ensure_services_available():
        sys.exit(1)

    # Check specific services
    status = check_required_services(services=["PostgreSQL", "Redis"])
"""

import logging
import socket
import sys
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def check_service_available(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a service is available by attempting a TCP connection.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if service is reachable, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.gaierror:
        # DNS resolution failed
        return False
    except Exception as e:
        logger.debug(f"Connection check failed for {host}:{port}: {e}")
        return False


def get_service_endpoints() -> Dict[str, Tuple[str, int]]:
    """
    Get endpoints for all required services from configuration.

    Returns:
        Dictionary mapping service names to (host, port) tuples

    Note:
        This function tries to load from environment variables first,
        then falls back to common local development values.
    """
    import os

    try:
        # Always use environment variables directly (not settings object)
        # This ensures we get the latest values after .env is loaded in scripts
        postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
        postgres_port = int(os.getenv("POSTGRES_PORT", "5433"))
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6380"))
        minio_endpoint = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
        opensearch_host = os.getenv("OPENSEARCH_HOST", "localhost")
        opensearch_port = int(os.getenv("OPENSEARCH_PORT", "9201"))

        # Determine MinIO host from endpoint URL
        minio_host = "localhost"
        if minio_endpoint:
            if "localhost" in minio_endpoint or "127.0.0.1" in minio_endpoint:
                minio_host = "localhost"
            elif "minio:" in minio_endpoint or minio_endpoint.startswith(
                "http://minio"
            ):
                minio_host = "minio"
            else:
                # Extract host from URL
                import re

                match = re.search(r"https?://([^:]+)", minio_endpoint)
                if match:
                    minio_host = match.group(1)

        return {
            "PostgreSQL": (postgres_server, postgres_port),
            "Redis": (redis_host, redis_port),
            "MinIO": (minio_host, 9000),
            "OpenSearch": (opensearch_host, opensearch_port),
        }
    except Exception as e:
        logger.debug(f"Using fallback service endpoints: {e}")
        # Fallback to common local development values
        return {
            "PostgreSQL": ("localhost", 5433),
            "Redis": ("localhost", 6380),
            "MinIO": ("localhost", 9000),
            "OpenSearch": ("localhost", 9201),
        }


def check_required_services(
    services: Optional[List[str]] = None, timeout: float = 2.0, verbose: bool = True
) -> Dict[str, bool]:
    """
    Check availability of required services.

    Args:
        services: List of service names to check (None = check all)
        timeout: Connection timeout in seconds
        verbose: Whether to log results

    Returns:
        Dictionary mapping service names to availability status (True/False)
    """
    all_endpoints = get_service_endpoints()

    # Filter to requested services if specified
    if services:
        endpoints = {
            name: endpoint
            for name, endpoint in all_endpoints.items()
            if name in services
        }
    else:
        endpoints = all_endpoints

    status = {}
    for name, (host, port) in endpoints.items():
        is_available = check_service_available(host, port, timeout)
        status[name] = is_available

        if verbose:
            status_icon = "✓" if is_available else "✗"
            status_text = "Available" if is_available else "Not available"
            logger.info(f"{status_icon} {name:12s} ({host}:{port}): {status_text}")

    return status


def ensure_services_available(
    services: Optional[List[str]] = None,
    timeout: float = 2.0,
    exit_on_failure: bool = False,
) -> bool:
    """
    Check required services and optionally exit if any are unavailable.

    Args:
        services: List of service names to check (None = check all)
        timeout: Connection timeout in seconds
        exit_on_failure: Whether to exit the program if services are unavailable

    Returns:
        True if all services are available, False otherwise

    Example:
        >>> if not ensure_services_available(services=["PostgreSQL", "Redis"]):
        ...     sys.exit(1)
    """
    logger.info("🔍 Checking service availability...")
    status = check_required_services(services=services, timeout=timeout, verbose=True)

    all_available = all(status.values())

    if not all_available:
        missing = [name for name, available in status.items() if not available]
        logger.error(f"❌ Missing services: {', '.join(missing)}")
        logger.info("💡 Start services with: docker compose up -d")
        logger.info("💡 Or check specific services with: docker compose ps")

        if exit_on_failure:
            logger.error("Exiting due to missing services")
            sys.exit(1)

        return False
    else:
        logger.info("✅ All required services are running")
        return True


def check_service_healthy(service_name: str, timeout: float = 2.0) -> bool:
    """
    Check if a specific service is healthy and available.

    Args:
        service_name: Name of the service (PostgreSQL, Redis, MinIO, OpenSearch)
        timeout: Connection timeout in seconds

    Returns:
        True if service is available, False otherwise

    Example:
        >>> if not check_service_healthy("PostgreSQL"):
        ...     print("Database not available")
    """
    endpoints = get_service_endpoints()

    if service_name not in endpoints:
        logger.error(f"Unknown service: {service_name}")
        logger.info(f"Available services: {', '.join(endpoints.keys())}")
        return False

    host, port = endpoints[service_name]
    return check_service_available(host, port, timeout)


def check_services_or_exit(services: List[str], script_name: str = "Script") -> None:
    """
    Check required services and exit if any are unavailable.

    This is a convenience function for scripts that should fail fast
    if required services are not available.

    Args:
        services: List of service names to check (e.g., ["PostgreSQL", "Redis", "MinIO"])
        script_name: Name of the calling script (for error messages)

    Example:
        >>> # In any script - single line import and check
        >>> from backend.app.core.health_checks import check_services_or_exit
        >>> check_services_or_exit(["PostgreSQL", "Redis", "MinIO"])
        >>> # Script continues only if all services are available
    """
    if not ensure_services_available(services=services, exit_on_failure=False):
        logger.error(f"{script_name} cannot proceed without required services")
        sys.exit(1)
