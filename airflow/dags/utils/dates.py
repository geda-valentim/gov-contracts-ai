"""Date utilities for DAGs."""

from datetime import datetime, timedelta


def get_date_range_for_execution(execution_date: datetime) -> tuple[str, str]:
    """
    Get date range (YYYYMMDD format) for a given execution date.

    For daily DAGs, returns the execution date.

    Args:
        execution_date: Airflow execution date

    Returns:
        Tuple of (start_date, end_date) in YYYYMMDD format
    """
    date_str = execution_date.strftime("%Y%m%d")
    return date_str, date_str


def get_yesterday() -> str:
    """Get yesterday's date in YYYYMMDD format."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y%m%d")


def get_last_n_days(n: int) -> tuple[str, str]:
    """
    Get date range for last N days.

    Args:
        n: Number of days to go back

    Returns:
        Tuple of (start_date, end_date) in YYYYMMDD format
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=n)

    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
