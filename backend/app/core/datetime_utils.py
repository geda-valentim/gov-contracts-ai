"""
Datetime utilities with timezone awareness for consistent date handling.

This module provides utilities to ensure all dates are timezone-aware
and consistently use America/Sao_Paulo timezone throughout the application.

WHY: Airflow uses Pendulum with UTC internally, but we need to save data
partitioned by Brazil's timezone (America/Sao_Paulo) to match business logic.

USAGE:
    from backend.app.core.datetime_utils import get_now_sao_paulo, to_sao_paulo

    # Get current time in São Paulo
    now = get_now_sao_paulo()

    # Convert any datetime to São Paulo timezone
    local_dt = to_sao_paulo(some_datetime)

    # Format for partitioning
    date_str = format_date(now)  # "20251023"
"""

from datetime import datetime, timezone
from typing import Optional

try:
    import pendulum

    HAS_PENDULUM = True
except ImportError:
    HAS_PENDULUM = False

# Brazil's timezone (used for data partitioning and business logic)
SAO_PAULO_TZ = "America/Sao_Paulo"


def get_now_sao_paulo() -> datetime:
    """
    Get current datetime in São Paulo timezone.

    Returns:
        datetime: Current time in America/Sao_Paulo timezone

    Example:
        >>> now = get_now_sao_paulo()
        >>> now.tzinfo
        <DstTzInfo 'America/Sao_Paulo' -03-1 day, 21:00:00 STD>
    """
    if HAS_PENDULUM:
        return pendulum.now(SAO_PAULO_TZ)

    # Fallback if pendulum not available
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(SAO_PAULO_TZ))


def to_sao_paulo(dt: Optional[datetime]) -> datetime:
    """
    Convert any datetime to São Paulo timezone.

    If datetime is naive (no timezone), assumes it's UTC.
    If datetime is already timezone-aware, converts to São Paulo.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        datetime: Datetime in America/Sao_Paulo timezone

    Example:
        >>> utc_dt = datetime(2025, 10, 23, 12, 0, tzinfo=timezone.utc)
        >>> sp_dt = to_sao_paulo(utc_dt)
        >>> sp_dt.hour
        9  # UTC 12:00 = São Paulo 09:00 (UTC-3)
    """
    if dt is None:
        return get_now_sao_paulo()

    if HAS_PENDULUM:
        # Pendulum handles conversion elegantly
        if not hasattr(dt, "tzinfo") or dt.tzinfo is None:
            # Naive datetime - assume UTC
            dt = pendulum.instance(dt, tz="UTC")
        elif not isinstance(dt, pendulum.DateTime):
            # Convert regular datetime to pendulum
            dt = pendulum.instance(dt)

        return dt.in_timezone(SAO_PAULO_TZ)

    # Fallback without pendulum
    from zoneinfo import ZoneInfo

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(ZoneInfo(SAO_PAULO_TZ))


def format_date(dt: Optional[datetime] = None) -> str:
    """
    Format datetime for file partitioning (YYYYMMDD).

    Always uses São Paulo timezone to ensure consistent partitioning.

    Args:
        dt: Datetime to format (defaults to now)

    Returns:
        str: Date in YYYYMMDD format

    Example:
        >>> dt = datetime(2025, 10, 23, 3, 0, tzinfo=timezone.utc)
        >>> format_date(dt)
        '20251023'  # Still Oct 23 in São Paulo (UTC 03:00 = SP 00:00)
        >>> dt = datetime(2025, 10, 23, 2, 0, tzinfo=timezone.utc)
        >>> format_date(dt)
        '20251022'  # Oct 22 in São Paulo (UTC 02:00 = SP Oct 22 23:00)
    """
    if dt is None:
        dt = get_now_sao_paulo()
    else:
        dt = to_sao_paulo(dt)

    return dt.strftime("%Y%m%d")


def format_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format datetime for timestamps (YYYYMMDD_HHMMSS).

    Always uses São Paulo timezone.

    Args:
        dt: Datetime to format (defaults to now)

    Returns:
        str: Datetime in YYYYMMDD_HHMMSS format

    Example:
        >>> dt = datetime(2025, 10, 23, 15, 30, 45, tzinfo=timezone.utc)
        >>> format_datetime(dt)
        '20251023_123045'  # São Paulo time (UTC-3)
    """
    if dt is None:
        dt = get_now_sao_paulo()
    else:
        dt = to_sao_paulo(dt)

    return dt.strftime("%Y%m%d_%H%M%S")


def get_partition_path(dt: Optional[datetime] = None) -> dict[str, str]:
    """
    Get partition components for data lake structure.

    Always uses São Paulo timezone to ensure data is partitioned
    by local business date, not UTC date.

    Args:
        dt: Datetime to partition (defaults to now)

    Returns:
        dict: Partition components (year, month, day)

    Example:
        >>> dt = datetime(2025, 10, 23, 3, 0, tzinfo=timezone.utc)
        >>> get_partition_path(dt)
        {'year': '2025', 'month': '10', 'day': '23'}
    """
    if dt is None:
        dt = get_now_sao_paulo()
    else:
        dt = to_sao_paulo(dt)

    return {
        "year": dt.strftime("%Y"),
        "month": dt.strftime("%m"),
        "day": dt.strftime("%d"),
    }


def parse_date_str(date_str: str, tz: str = SAO_PAULO_TZ) -> datetime:
    """
    Parse date string (YYYYMMDD) to timezone-aware datetime.

    Args:
        date_str: Date string in YYYYMMDD format
        tz: Timezone to use (defaults to São Paulo)

    Returns:
        datetime: Timezone-aware datetime at midnight

    Example:
        >>> dt = parse_date_str("20251023")
        >>> dt
        DateTime(2025, 10, 23, 0, 0, 0, tzinfo=Timezone('America/Sao_Paulo'))
    """
    if HAS_PENDULUM:
        # Parse as São Paulo timezone
        return pendulum.from_format(date_str, "YYYYMMDD", tz=tz)

    # Fallback without pendulum
    from zoneinfo import ZoneInfo

    naive_dt = datetime.strptime(date_str, "%Y%m%d")
    return naive_dt.replace(tzinfo=ZoneInfo(tz))
