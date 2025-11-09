"""
Bronze Layer: PNCP Details Hourly Ingestion DAG with Auto-Resume.

Fetches items (itens) and documents (arquivos) for contratacoes in batches.
Uses auto-resume to continue from last checkpoint.

INCREMENTAL PROCESSING:
- Processes contratacoes in batches (e.g., 100 per hour)
- Auto-resumes from last checkpoint
- Separate state for itens and arquivos
- Safe re-runs with idempotent operations

Schedule: Every hour (or custom interval)
Data: Batch of unprocessed contratacoes from current day
Output: JSON with nested structure (appended to daily file)
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
from backend.app.services.ingestion.pncp_details import PNCPDetailsIngestionService

# Import centralized date utilities
from dags.utils.dates import get_execution_date, DEFAULT_TZ

# DAG default arguments
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}

# Configuration
BATCH_SIZE = 100  # Process 100 contratacoes per hour


def fetch_details_batch(**context) -> dict:
    """
    Airflow task wrapper: Fetch batch of details with auto-resume.

    This task:
    1. Reads contratacoes from Bronze
    2. Filters out already processed (auto-resume)
    3. Processes next batch (e.g., 100 contratacoes)
    4. Saves data to temp storage
    """
    # Get execution date using centralized utility (handles timezone conversion)
    execution_date = get_execution_date(context)

    dag_run = context.get("dag_run")
    execution_id = (
        dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")
    )

    # Get batch size from DAG conf if provided
    batch_size = BATCH_SIZE
    if dag_run and dag_run.conf:
        batch_size = dag_run.conf.get("batch_size", BATCH_SIZE)

    print(f"🔄 Auto-resume mode: processing batch of {batch_size} contratacoes")

    # Call standalone service with auto-resume
    service = PNCPDetailsIngestionService()
    result = service.fetch_details_for_date(
        execution_date=execution_date,
        batch_size=batch_size,
        auto_resume=True,  # ✅ Auto-resume enabled
    )

    # Check if there's data to process
    if not result["data"]:
        reason = "no_data"
        if result["metadata"].get("resume_stats"):
            reason = "all_processed"

        print(f"⚠️  No data to process: {reason}")
        return {
            "has_data": False,
            "reason": reason,
            "metadata": result["metadata"],
        }

    # ✅ Save data to temp storage
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],
        execution_id=execution_id,
        stage="batch_details",
        format="json",
    )

    print(
        f"📦 Processed batch: {len(result['data'])} contratacoes "
        f"({result['metadata']['total_itens']} itens, {result['metadata']['total_arquivos']} arquivos)"
    )

    remaining = result["metadata"].get("remaining_contratacoes", 0)
    if remaining > 0:
        print(f"📋 Remaining: {remaining} contratacoes for future runs")
    else:
        print("✅ All contratacoes processed!")

    return {
        "has_data": True,
        "temp_key": temp_key,
        "metadata": result["metadata"],
        "contratacoes_count": len(result["data"]),
    }


def append_to_bronze(**context) -> dict:
    """
    Airflow task wrapper: Append batch to daily Bronze Parquet file.

    Reads existing daily file (if any) and appends new batch.
    """
    from backend.app.services.ingestion.pncp_details import (
        convert_nested_to_dataframe,
        save_to_parquet_bronze,
    )

    task_instance = context["task_instance"]
    # Get execution date using centralized utility (handles timezone conversion)
    execution_date = get_execution_date(context)

    # Get batch result
    batch_result = task_instance.xcom_pull(task_ids="fetch_details_batch")

    if not batch_result or not batch_result.get("has_data"):
        reason = batch_result.get("reason", "unknown") if batch_result else "no_result"
        print(f"⚠️  No data to append: {reason}")
        return {"appended": False, "reason": reason}

    # Read batch data from temp
    storage = get_storage_client()
    batch_data = storage.read_json_from_s3(
        bucket=storage.BUCKET_BRONZE, key=batch_result["temp_key"]
    )

    # Convert to DataFrame
    batch_df = convert_nested_to_dataframe(batch_data)

    # Save with append mode (handles existing file automatically)
    details_key = save_to_parquet_bronze(
        df=batch_df,
        storage_client=storage,
        execution_date=execution_date,
        mode="append",
    )

    # Get total count from parquet file
    try:
        client = getattr(storage, '_client', storage)
        final_df = client.read_parquet_from_s3(
            bucket_name=storage.BUCKET_BRONZE, object_name=details_key
        )
        total_count = len(final_df)
    except Exception:
        total_count = len(batch_df)

    print(
        f"✅ Appended to Bronze: {details_key} "
        f"(+{len(batch_df)} contratacoes, total: {total_count})"
    )

    return {
        "appended": True,
        "s3_key": details_key,
        "batch_size": len(batch_df),
        "total_contratacoes": total_count,
    }


def validate_ingestion(**context) -> dict:
    """
    Airflow task wrapper: Validate batch append.
    """
    task_instance = context["task_instance"]

    append_result = task_instance.xcom_pull(task_ids="append_to_bronze")

    if not append_result or not append_result.get("appended"):
        reason = append_result.get("reason", "unknown") if append_result else "no_result"

        # Acceptable reasons
        if reason in ["no_data", "all_processed"]:
            print(f"✅ Validation passed: {reason} (acceptable)")
            return {"validation": "passed", "reason": reason}
        else:
            print(f"❌ Validation failed: {reason}")
            raise ValueError(f"Append failed: {reason}")

    # Check batch size
    batch_size = append_result.get("batch_size", 0)
    total = append_result.get("total_contratacoes", 0)

    print(f"✅ Validation passed: +{batch_size} contratacoes (total: {total})")

    return {
        "validation": "passed",
        "batch_size": batch_size,
        "total_contratacoes": total,
    }


def cleanup_temp_files(**context) -> dict:
    """
    Airflow task wrapper: Cleanup temporary files from S3.
    """
    dag_run = context.get("dag_run")
    execution_date = get_execution_date(context)
    execution_id = (
        dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")
    )

    storage = get_storage_client()

    try:
        deleted_count = storage.cleanup_temp(
            execution_id=execution_id, bucket=storage.BUCKET_BRONZE
        )

        print(f"🧹 Cleaned up {deleted_count} temporary files")

        return {"cleaned_up": True, "files_deleted": deleted_count}

    except Exception as e:
        print(f"⚠️  Error during cleanup (non-fatal): {e}")
        return {"cleaned_up": False, "error": str(e)}


# Define DAG
with DAG(
    dag_id="bronze_pncp_details_hourly_ingestion",
    default_args=default_args,
    description="Batch processing of PNCP details with auto-resume (every 15 minutes)",
    schedule="*/15 * * * *",  # Every 15 minutes
    start_date=pendulum.datetime(2025, 10, 23, tz=DEFAULT_TZ),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "details", "hourly", "auto-resume"],
) as dag:

    # Task 1: Fetch batch with auto-resume
    task_fetch_batch = PythonOperator(
        task_id="fetch_details_batch",
        python_callable=fetch_details_batch,
    )

    # Task 2: Append to Bronze daily file
    task_append = PythonOperator(
        task_id="append_to_bronze",
        python_callable=append_to_bronze,
    )

    # Task 3: Validate append
    task_validate = PythonOperator(
        task_id="validate_ingestion",
        python_callable=validate_ingestion,
    )

    # Task 4: Cleanup temp files
    task_cleanup = PythonOperator(
        task_id="cleanup_temp_files",
        python_callable=cleanup_temp_files,
        trigger_rule="all_done",
    )

    # Define task dependencies
    task_fetch_batch >> task_append >> task_validate >> task_cleanup
