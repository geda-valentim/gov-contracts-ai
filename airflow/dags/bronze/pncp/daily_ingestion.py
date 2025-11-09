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

from datetime import timedelta

import pendulum
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

# Import centralized date utilities
from dags.utils.dates import get_execution_date, DEFAULT_TZ

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
    3. Saves data to temp storage (NOT XCom to avoid DB bloat)
    4. Pushes only S3 reference to XCom (<1KB)
    """
    # Get execution date using centralized utility (handles timezone conversion)
    execution_date = get_execution_date(context)

    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")

    # Call standalone service (no Airflow dependencies)
    service = PNCPIngestionService()
    result = service.fetch_daily_complete(
        execution_date=execution_date,
        modalidades=ModalidadeContratacao.get_all(),
    )

    # ✅ SOLUTION: Save data to temp storage instead of XCom
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],
        execution_id=execution_id,
        stage="raw",
        format="parquet",
    )

    print(
        f"📦 Saved {len(result['data'])} records to temp storage: {temp_key} "
        f"(XCom stores only reference, not data)"
    )

    # ✅ XCom only stores lightweight metadata + S3 reference
    return {
        "temp_key": temp_key,
        "metadata": result["metadata"],
        "record_count": len(result["data"]),
    }


def transform_data(**context) -> dict:
    """
    Airflow task wrapper: Transform and validate data with incremental state filtering.

    This is a thin wrapper that:
    1. Reads S3 reference from XCom (not data itself)
    2. Loads data from temp storage
    3. Loads state to filter duplicates
    4. Filters only NEW records (not already processed)
    5. Transforms and validates
    6. Updates state with new IDs
    7. Saves to temp storage (not XCom)
    """
    task_instance = context["task_instance"]
    # Airflow 3.x uses 'logical_date' instead of 'execution_date'
    execution_date = context.get("logical_date") or context.get("data_interval_start")
    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")

    # ✅ Get S3 reference from XCom (lightweight)
    fetch_result = task_instance.xcom_pull(task_ids="fetch_pncp_data")

    if not fetch_result or not fetch_result.get("temp_key"):
        return {"transformed": False, "reason": "no_data"}

    # ✅ Read actual data from temp storage (not from XCom)
    storage = get_storage_client()
    raw_df = storage.read_temp(bucket=storage.BUCKET_BRONZE, key=fetch_result["temp_key"])

    # Convert DataFrame back to list of dicts for processing
    raw_data = raw_df.to_dict(orient="records")

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
    metadata = fetch_result.get("metadata", {})
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

    # ✅ Store DataFrame in temp storage (not XCom)
    transformed_key = storage.upload_temp(
        data=df, execution_id=execution_id, stage="transformed", format="parquet"
    )

    print(
        f"📦 Saved {len(df)} transformed records to temp storage: {transformed_key} "
        f"(XCom stores only reference)"
    )

    # ✅ XCom only stores lightweight metadata + references
    return {
        "transformed": True,
        "temp_key": transformed_key,  # S3 reference only
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

    # ✅ Get S3 reference from XCom (lightweight)
    transform_result = task_instance.xcom_pull(task_ids="transform_data")

    if not transform_result or not transform_result.get("temp_key"):
        return {"uploaded": False, "reason": "no_data"}

    # ✅ Read DataFrame from temp storage
    storage = get_storage_client()
    df = storage.read_temp(
        bucket=storage.BUCKET_BRONZE, key=transform_result["temp_key"]
    )

    if df is None or len(df) == 0:
        return {"uploaded": False, "reason": "no_data"}

    # Upload DataFrame to final Bronze location
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


def cleanup_temp_files(**context) -> dict:
    """
    Airflow task wrapper: Clean up temporary files.

    This task runs at the end (success or failure) to clean up
    temporary files created during the DAG execution.
    """
    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else context.get("logical_date").strftime(
        "%Y%m%d_%H%M%S"
    )

    storage = get_storage_client()
    deleted = storage.cleanup_temp(execution_id=execution_id)

    print(f"🧹 Cleaned up {deleted} temporary files for execution {execution_id}")

    return {"deleted_files": deleted, "execution_id": execution_id}


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
    start_date=pendulum.datetime(2025, 10, 1, tz=DEFAULT_TZ),
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

    # Task 5: Cleanup temporary files
    # This runs ALWAYS (even if previous tasks fail) to clean up temp storage
    task_cleanup = PythonOperator(
        task_id="cleanup_temp_files",
        python_callable=cleanup_temp_files,
        trigger_rule="all_done",  # Run regardless of upstream success/failure
    )

    # Define task dependencies
    # Cleanup runs after validate (regardless of success/failure)
    task_fetch >> task_transform >> task_upload >> task_validate >> task_cleanup
