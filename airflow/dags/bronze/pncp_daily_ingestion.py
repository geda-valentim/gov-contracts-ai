"""
Bronze Layer: PNCP Daily Ingestion DAG (Thin Wrapper).

This DAG is a thin Airflow wrapper around standalone business logic services.
The actual logic lives in backend/app/services/ and can be executed independently.

Schedule: Daily at 2 AM (after PNCP updates)
Data: Complete day data (all pages)
Partitioning: year=YYYY/month=MM/day=DD
"""

import sys

sys.path.insert(0, "/opt/airflow")

from datetime import UTC, datetime, timedelta

from airflow import DAG

# Airflow 3.x imports
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator

# Import standalone services (no Airflow dependencies)
from backend.app.core.storage_client import get_storage_client
from backend.app.domains.pncp import ModalidadeContratacao
from backend.app.services import (
    DataTransformationService,
    PNCPIngestionService,
)

# DAG default arguments
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


def fetch_pncp_data(**context) -> dict:
    """
    Airflow task wrapper: Fetch complete day data from PNCP API.

    This is a thin wrapper that:
    1. Extracts Airflow context
    2. Calls standalone service
    3. Pushes results to XCom
    """
    # Airflow 3.x: use logical_date instead of execution_date
    # Fallback chain: logical_date -> data_interval_start -> current time
    execution_date = (
        context.get("logical_date") or context.get("data_interval_start") or datetime.now(UTC)
    )

    # Call standalone service (no Airflow dependencies)
    service = PNCPIngestionService()
    result = service.fetch_daily_complete(
        execution_date=execution_date,
        modalidades=ModalidadeContratacao.get_all(),
    )

    # Push to XCom for next task
    context["task_instance"].xcom_push(key="fetched_data", value=result["data"])
    context["task_instance"].xcom_push(key="metadata", value=result["metadata"])

    return result["metadata"]


def transform_data(**context) -> dict:
    """
    Airflow task wrapper: Transform and validate data.

    This is a thin wrapper that:
    1. Pulls data from XCom
    2. Calls standalone service
    3. Pushes results to XCom
    """
    task_instance = context["task_instance"]

    # Get data from previous task
    raw_data = task_instance.xcom_pull(task_ids="fetch_pncp_data", key="fetched_data")

    if not raw_data:
        return {"transformed": False, "reason": "no_data"}

    # Call standalone service
    service = DataTransformationService()

    # Validate
    validation_report = service.validate_records(raw_data)

    # Transform to DataFrame
    df = service.to_dataframe(raw_data, deduplicate=True)

    # Add metadata
    metadata = task_instance.xcom_pull(task_ids="fetch_pncp_data", key="metadata")
    df = service.add_metadata_columns(df, metadata)

    # Store DataFrame in context for next task (instead of XCom which has size limits)
    # XCom is limited to ~1MB, but daily ingestion can have many thousands of records
    task_instance.xcom_push(key="dataframe", value=df)  # Pandas DataFrame
    task_instance.xcom_push(key="validation_report", value=validation_report)

    return {
        "transformed": True,
        "record_count": len(df),
        "validation": validation_report,
    }


def upload_to_bronze(**context) -> dict:
    """
    Airflow task wrapper: Upload data to Bronze layer.

    This is a thin wrapper that:
    1. Pulls data from XCom
    2. Calls standalone service
    3. Returns upload result
    """
    task_instance = context["task_instance"]
    # Airflow 3.x: use logical_date instead of execution_date
    # Fallback chain: logical_date -> data_interval_start -> current time
    from datetime import datetime

    execution_date = (
        context.get("logical_date") or context.get("data_interval_start") or datetime.now(UTC)
    )

    # Get DataFrame from previous task
    df = task_instance.xcom_pull(task_ids="transform_data", key="dataframe")

    if df is None or len(df) == 0:
        return {"uploaded": False, "reason": "no_data"}

    # Convert DataFrame to JSON-safe list of dicts
    # Use df.to_json() + json.loads() to handle numpy types properly
    import json

    data = json.loads(df.to_json(orient="records", date_format="iso"))

    # Upload to Bronze using MinIO client
    storage = get_storage_client()
    s3_key = storage.upload_to_bronze(
        data=data,
        source="pncp",
        date=execution_date,
    )

    return {
        "uploaded": True,
        "s3_key": s3_key,
        "bucket": storage.BUCKET_BRONZE,
        "record_count": len(data),
    }


def validate_ingestion(**context) -> dict:
    """
    Airflow task wrapper: Validate ingestion.

    This is a thin wrapper that:
    1. Pulls results from XCom
    2. Validates completion
    3. Returns validation status

    Note: Succeeds with no_data=True when API returns no results (expected for future dates)
    """
    task_instance = context["task_instance"]

    # Get results from previous tasks
    upload_result = task_instance.xcom_pull(task_ids="upload_to_bronze")
    validation_report = task_instance.xcom_pull(task_ids="transform_data", key="validation_report")

    # Handle case where no data was available from API (expected for future dates)
    if upload_result and upload_result.get("reason") == "no_data":
        print(
            "⚠️  No data available from PNCP API - this is expected for future dates or when API has no records"
        )
        return {
            "validated": True,
            "no_data": True,
            "reason": "no_data_from_api",
            "record_count": 0,
        }

    # Validate that upload actually succeeded
    if not upload_result or not upload_result.get("uploaded"):
        raise ValueError(f"Upload task failed: {upload_result}")

    record_count = upload_result.get("record_count", 0)

    # Validation checks
    checks = {
        "has_data": record_count > 0,
        "upload_succeeded": upload_result.get("uploaded", False),
        "s3_key_exists": bool(upload_result.get("s3_key")),
        "validation_passed": validation_report.get("invalid_records", 0) == 0
        if validation_report
        else True,
    }

    all_passed = all(checks.values())

    if not all_passed:
        raise ValueError(f"Validation failed: {checks}")

    print(f"✅ Validation passed: {record_count} records ingested")

    return {
        "validated": True,
        "no_data": False,
        "checks": checks,
        "record_count": record_count,
    }


# Define DAG
with DAG(
    dag_id="bronze_pncp_daily_ingestion",
    default_args=default_args,
    description="Daily ingestion of PNCP data to Bronze layer (thin wrapper)",
    schedule="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2025, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "ingestion", "daily"],
) as dag:
    # Task 1: Fetch data (thin wrapper around PNCPIngestionService)
    task_fetch = PythonOperator(
        task_id="fetch_pncp_data",
        python_callable=fetch_pncp_data,
    )

    # Task 2: Transform data (thin wrapper around DataTransformationService)
    task_transform = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data,
    )

    # Task 3: Upload to Bronze (thin wrapper around MinIOClient)
    task_upload = PythonOperator(
        task_id="upload_to_bronze",
        python_callable=upload_to_bronze,
    )

    # Task 4: Validate ingestion
    task_validate = PythonOperator(
        task_id="validate_ingestion",
        python_callable=validate_ingestion,
    )

    # Define task dependencies
    task_fetch >> task_transform >> task_upload >> task_validate
