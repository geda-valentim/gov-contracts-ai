"""
Notification utilities for DAG failures and success.

Supports Slack, email, and logging.
"""

import logging
from datetime import UTC
from typing import Any

logger = logging.getLogger(__name__)


def notify_success(context: dict[str, Any]) -> None:
    """
    Callback for successful DAG runs.

    Args:
        context: Airflow context dict
    """
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    # Airflow 3.x: use logical_date instead of execution_date
    from datetime import datetime

    execution_date = (
        context.get("logical_date") or context.get("data_interval_start") or datetime.now(UTC)
    )

    logger.info(f"✅ DAG Success: {dag_id} | Task: {task_id} | Date: {execution_date}")

    # TODO: Add Slack notification
    # TODO: Add email notification


def notify_failure(context: dict[str, Any]) -> None:
    """
    Callback for failed DAG runs.

    Args:
        context: Airflow context dict
    """
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    # Airflow 3.x: use logical_date instead of execution_date
    from datetime import datetime

    execution_date = (
        context.get("logical_date") or context.get("data_interval_start") or datetime.now(UTC)
    )
    exception = context.get("exception")

    logger.error(
        f"❌ DAG Failure: {dag_id} | Task: {task_id} | Date: {execution_date} | Error: {exception}"
    )

    # TODO: Add Slack notification
    # TODO: Add email notification
    # TODO: Add PagerDuty/Opsgenie integration
