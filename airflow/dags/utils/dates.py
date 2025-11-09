"""
Date utilities for DAGs with timezone awareness.

IMPORTANT: All dates use the timezone configured in .env (TZ variable) to ensure:
1. Data is partitioned by local business date (not UTC)
2. Consistent date handling across DAGs and backend
3. Airflow logical_date (UTC) is properly converted to local time

WHY PENDULUM:
- Airflow internally uses Pendulum for logical_date
- Better timezone handling than stdlib datetime
- Consistent API across the codebase

CONFIGURATION:
- Timezone is read from environment variable TZ (default: America/Sao_Paulo)
- Set in .env file: TZ=America/Sao_Paulo
"""

import os
import pendulum
from datetime import datetime

# Application timezone (read from .env TZ variable)
DEFAULT_TZ = os.getenv("TZ", "America/Sao_Paulo")

# Legacy alias (for backward compatibility)
SAO_PAULO_TZ = DEFAULT_TZ


def to_local_tz(dt: datetime) -> pendulum.DateTime:
    """
    Convert any datetime to configured local timezone (from TZ env var).

    Args:
        dt: Datetime to convert (Airflow logical_date, execution_date, etc.)

    Returns:
        pendulum.DateTime in configured timezone (default: America/Sao_Paulo)

    Example:
        >>> # Airflow passes logical_date in UTC
        >>> logical_date = pendulum.datetime(2025, 10, 23, 3, 0, tz="UTC")
        >>> local_date = to_local_tz(logical_date)
        >>> local_date.format("YYYYMMDD")
        '20251023'  # Converted to local timezone
    """
    if isinstance(dt, pendulum.DateTime):
        return dt.in_timezone(DEFAULT_TZ)

    # Convert stdlib datetime to pendulum
    return pendulum.instance(dt).in_timezone(DEFAULT_TZ)


# Legacy alias (for backward compatibility)
def to_sao_paulo(dt: datetime) -> pendulum.DateTime:
    """DEPRECATED: Use to_local_tz() instead."""
    return to_local_tz(dt)


def get_date_range_for_execution(execution_date: datetime) -> tuple[str, str]:
    """
    Get date range (YYYYMMDD format) for a given execution date.

    For daily DAGs, returns the execution date in São Paulo timezone.

    Args:
        execution_date: Airflow execution date (usually UTC)

    Returns:
        Tuple of (start_date, end_date) in YYYYMMDD format

    Example:
        >>> # UTC midnight = São Paulo 21:00 previous day
        >>> execution_date = pendulum.datetime(2025, 10, 23, 0, 0, tz="UTC")
        >>> get_date_range_for_execution(execution_date)
        ('20251022', '20251022')  # Returns São Paulo date
    """
    sp_date = to_sao_paulo(execution_date)
    date_str = sp_date.format("YYYYMMDD")
    return date_str, date_str


def get_yesterday() -> str:
    """
    Get yesterday's date in YYYYMMDD format (local timezone from TZ env var).

    Returns:
        str: Yesterday's date in YYYYMMDD format

    Example:
        >>> # If today is Oct 23 in local timezone
        >>> get_yesterday()
        '20251022'
    """
    yesterday = pendulum.now(DEFAULT_TZ).subtract(days=1)
    return yesterday.format("YYYYMMDD")


def get_last_n_days(n: int) -> tuple[str, str]:
    """
    Get date range for last N days (local timezone from TZ env var).

    Args:
        n: Number of days to go back

    Returns:
        Tuple of (start_date, end_date) in YYYYMMDD format

    Example:
        >>> # If today is Oct 23 in local timezone
        >>> get_last_n_days(7)
        ('20251016', '20251023')  # Last 7 days
    """
    end_date = pendulum.now(DEFAULT_TZ)
    start_date = end_date.subtract(days=n)

    return start_date.format("YYYYMMDD"), end_date.format("YYYYMMDD")


def get_now_local() -> pendulum.DateTime:
    """
    Get current datetime in configured local timezone (from TZ env var).

    Returns:
        pendulum.DateTime: Current time in configured timezone

    Example:
        >>> now = get_now_local()
        >>> now.timezone_name
        'America/Sao_Paulo'  # Or whatever is configured in TZ
    """
    return pendulum.now(DEFAULT_TZ)


# Legacy alias (for backward compatibility)
def get_now_sao_paulo() -> pendulum.DateTime:
    """DEPRECATED: Use get_now_local() instead."""
    return get_now_local()


def format_date(dt: datetime) -> str:
    """
    Format datetime for file partitioning (YYYYMMDD).

    Args:
        dt: Datetime to format

    Returns:
        str: Date in YYYYMMDD format

    Example:
        >>> dt = pendulum.datetime(2025, 10, 23, 15, 30, tz="UTC")
        >>> format_date(dt)
        '20251023'  # Converted to local timezone first
    """
    local_date = to_local_tz(dt)
    return local_date.format("YYYYMMDD")


def get_execution_date(context: dict) -> pendulum.DateTime:
    """
    Get execution date from Airflow context and convert to local timezone.

    This is the SINGLE SOURCE OF TRUTH for getting execution dates in all DAGs.

    WHY THIS FUNCTION EXISTS:
    - Centralizes the logic of extracting execution_date from Airflow context
    - Handles both logical_date (Airflow 2.2+) and data_interval_start (Airflow 2.0+)
    - Provides safe fallback to current time if running outside Airflow
    - Ensures all DAGs use the same timezone conversion logic
    - Uses TZ environment variable for timezone configuration

    MIGRATION PLAN:
    - All DAGs should use this function instead of manual context extraction
    - If we need to change how we get execution dates, we only modify this function

    Args:
        context: Airflow task context dict (passed automatically to task functions)

    Returns:
        pendulum.DateTime: Execution date in configured local timezone (from TZ env var)

    Example:
        >>> # Inside a DAG task
        >>> def my_task(**context):
        ...     execution_date = get_execution_date(context)
        ...     date_str = execution_date.format("YYYYMMDD")
        ...     print(f"Processing data for {date_str}")

        >>> # Airflow passes logical_date as UTC 2025-10-23 00:00:00+00:00
        >>> # Function converts to local TZ: 2025-10-22 21:00:00-03:00
        >>> # format("YYYYMMDD") returns: "20251022"
    """
    # Try to get logical_date (Airflow 2.2+)
    execution_date = context.get("logical_date")

    # Fallback to data_interval_start (Airflow 2.0+)
    if execution_date is None:
        execution_date = context.get("data_interval_start")

    # Fallback to current time if running outside Airflow (manual execution)
    if execution_date is None:
        execution_date = get_now_local()

    # Convert to local timezone
    return to_local_tz(execution_date)
