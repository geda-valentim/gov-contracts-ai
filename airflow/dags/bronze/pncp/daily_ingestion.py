"""
Bronze Layer: PNCP Daily Ingestion DAG (Thin Wrapper with State Management).

This DAG is a thin Airflow wrapper around standalone business logic services.
The actual logic lives in backend/app/services/ and can be executed independently.

Schedule: Daily at 2 AM (after PNCP updates)
Data: Complete day data (all pages)
Partitioning: year=YYYY/month=MM/day=DD

**INCREMENTAL INGESTION:**
- Uses StateManager to track processed record IDs
- Filters out already-processed records (deduplication)
- Only uploads NEW records to Bronze
- Updates state after successful upload
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
    StateManager,
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
    Airflow task wrapper: Transform and validate data with incremental state filtering.

    This is a thin wrapper that:
    1. Pulls data from XCom
    2. Loads state to filter duplicates
    3. Filters only NEW records (not already processed)
    4. Transforms and validates
    5. Updates state with new IDs
    6. Pushes results to XCom
    """
    task_instance = context["task_instance"]
    # Airflow 3.x uses 'logical_date' instead of 'execution_date'
    execution_date = context.get("logical_date") or context.get("data_interval_start")

    # Get data from previous task
    raw_data = task_instance.xcom_pull(task_ids="fetch_pncp_data", key="fetched_data")

    if not raw_data:
        return {"transformed": False, "reason": "no_data"}

    # ===== INCREMENTAL STATE FILTERING =====
    # Initialize state manager
    state_manager = StateManager()

    # Filter only NEW records (not previously processed)
    new_records, filter_stats = state_manager.filter_new_records(
        source="pncp",
        date=execution_date,
        records=raw_data,
        id_field="numeroControlePNCP",
    )

    print(
        f"📊 State Filtering: {filter_stats['total_input']} input → "
        f"{filter_stats['new_records']} new ({filter_stats['already_processed']} duplicates filtered)"
    )

    # If no new records, return early (don't create empty files)
    if not new_records:
        print("⚠️  No new records to process (all duplicates)")
        return {
            "transformed": False,
            "reason": "no_new_records",
            "filter_stats": filter_stats,
        }

    # ===== TRANSFORM AND VALIDATE =====
    # Call standalone service
    service = DataTransformationService()

    # Validate
    validation_report = service.validate_records(new_records)

    # Transform to DataFrame (no deduplication needed - already done by state)
    df = service.to_dataframe(new_records, deduplicate=False)

    # Add metadata
    metadata = task_instance.xcom_pull(task_ids="fetch_pncp_data", key="metadata")
    df = service.add_metadata_columns(df, metadata)

    # ===== UPDATE STATE =====
    # Extract IDs from new records
    new_ids = [r.get("numeroControlePNCP") for r in new_records if r.get("numeroControlePNCP")]

    # Update state with new processed IDs
    state_manager.update_state(
        source="pncp",
        date=execution_date,
        new_ids=new_ids,
        execution_metadata={
            "new_records": len(new_records),
            "duplicates_filtered": filter_stats["already_processed"],
            "validation": validation_report,
        },
    )

    print(f"✅ State updated: {len(new_ids)} new IDs added")

    # Store DataFrame in context for next task
    task_instance.xcom_push(key="dataframe", value=df)
    task_instance.xcom_push(key="validation_report", value=validation_report)
    task_instance.xcom_push(key="filter_stats", value=filter_stats)

    return {
        "transformed": True,
        "record_count": len(df),
        "validation": validation_report,
        "filter_stats": filter_stats,
    }


def upload_to_bronze(**context) -> dict:
    """
    Airflow task wrapper: Upload data to Bronze layer as Parquet.

    This is a thin wrapper that:
    1. Pulls DataFrame from XCom
    2. Uploads directly as Parquet (no JSON conversion needed)
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

    # Upload DataFrame directly to Bronze as Parquet (default format)
    # No need to convert to JSON - Parquet handles pandas types natively
    storage = get_storage_client()
    s3_key = storage.upload_to_bronze(
        data=df,  # Pass DataFrame directly
        source="pncp",
        date=execution_date,
        format="parquet",  # Explicit format (default)
    )

    print(f"📦 Uploaded {len(df)} NEW records as Parquet: {s3_key}")

    return {
        "uploaded": True,
        "s3_key": s3_key,
        "bucket": storage.BUCKET_BRONZE,
        "record_count": len(df),
        "format": "parquet",
    }


def validate_ingestion(**context) -> dict:
    """
    Airflow task wrapper: Validate ingestion.

    This is a thin wrapper that:
    1. Pulls results from XCom
    2. Validates completion
    3. Returns validation status

    Note: Succeeds with no_data=True when API returns no results (expected for future dates)
    or when all records were already processed (duplicates).
    """
    task_instance = context["task_instance"]

    # Get results from previous tasks
    upload_result = task_instance.xcom_pull(task_ids="upload_to_bronze")
    validation_report = task_instance.xcom_pull(task_ids="transform_data", key="validation_report")
    filter_stats = task_instance.xcom_pull(task_ids="transform_data", key="filter_stats")

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

    # Print incremental ingestion stats
    if filter_stats:
        print(
            f"📊 Incremental ingestion stats: {filter_stats['total_input']} fetched → "
            f"{filter_stats['new_records']} new ({filter_stats['already_processed']} duplicates filtered)"
        )

    print(f"✅ Validation passed: {record_count} NEW records ingested")

    return {
        "validated": True,
        "no_data": False,
        "checks": checks,
        "record_count": record_count,
        "filter_stats": filter_stats,
    }


# Define DAG
with DAG(
    dag_id="bronze_pncp_daily_ingestion",
    default_args=default_args,
    description="Daily ingestion of PNCP data to Bronze layer with incremental state management",
    schedule="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2025, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "ingestion", "daily", "incremental"],
) as dag:
    # Task 1: Fetch data (thin wrapper around PNCPIngestionService)
    task_fetch = PythonOperator(
        task_id="fetch_pncp_data",
        python_callable=fetch_pncp_data,
    )

    # Task 2: Transform data with state filtering (thin wrapper around DataTransformationService + StateManager)
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
