"""
Bronze Layer: PNCP Details Hourly Ingestion DAG with Auto-Resume.

Fetches items (itens) and documents (arquivos) for contratacoes in batches.
Uses auto-resume to continue from last checkpoint.

INCREMENTAL PROCESSING:
- Processes contratacoes in batches (e.g., 100 per run)
- Auto-resumes from last checkpoint
- Saves chunks directly to Bronze (chunk_0001.parquet, chunk_0002.parquet, etc.)
- State tracking for itens and arquivos separately
- Safe re-runs with idempotent operations

Schedule: Every 15 minutes
Data: Batch of unprocessed contratacoes from current day
Output: Parquet chunks with nested structure (itens, arquivos per contratacao)

Tasks:
1. fetch_details_batch: Process batch and save directly to Bronze as chunks
2. validate_ingestion: Validate processing completed successfully
3. cleanup_temp_files: Clean up any temporary files
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
from backend.app.core.storage_client import get_storage_client  # Used in cleanup
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
    4. Saves data directly to Bronze as chunks (no temp storage needed)
    """
    # Get execution date using centralized utility (handles timezone conversion)
    execution_date = get_execution_date(context)

    dag_run = context.get("dag_run")

    # Get batch size from DAG conf if provided
    batch_size = BATCH_SIZE
    if dag_run and dag_run.conf:
        batch_size = dag_run.conf.get("batch_size", BATCH_SIZE)

    print(f"🔄 Auto-resume mode: processing batch of {batch_size} contratacoes")

    # Call standalone service with auto-resume
    # Service saves chunks directly to Bronze - no temp storage needed
    service = PNCPDetailsIngestionService()
    result = service.fetch_details_for_date(
        execution_date=execution_date,
        batch_size=batch_size,
        auto_resume=True,  # ✅ Auto-resume enabled
    )

    metadata = result["metadata"]
    contratacoes_processed = metadata.get("contratacoes_processed", 0)

    # Check if data was processed (service saves directly to Bronze)
    if contratacoes_processed == 0:
        reason = "no_data"
        if metadata.get("resume_stats"):
            reason = "all_processed"

        print(f"⚠️  No data to process: {reason}")
        return {
            "has_data": False,
            "reason": reason,
            "metadata": metadata,
        }

    # Data was processed and saved directly to Bronze by the service
    print(
        f"📦 Processed batch: {contratacoes_processed} contratacoes "
        f"({metadata['total_itens']} itens, {metadata['total_arquivos']} arquivos)"
    )
    print(f"💾 Chunks saved: {metadata.get('chunks_saved', 0)}")

    remaining = metadata.get("remaining_contratacoes", 0)
    if remaining > 0:
        print(f"📋 Remaining: {remaining} contratacoes for future runs")
    else:
        print("✅ All contratacoes processed!")

    return {
        "has_data": True,
        "metadata": metadata,
        "contratacoes_processed": contratacoes_processed,
        "chunks_saved": metadata.get("chunks_saved", 0),
    }


def validate_ingestion(**context) -> dict:
    """
    Airflow task wrapper: Validate batch processing.

    Validates that the fetch task completed successfully.
    Data is saved directly to Bronze by the service (no append step needed).
    """
    task_instance = context["task_instance"]

    fetch_result = task_instance.xcom_pull(task_ids="fetch_details_batch")

    if not fetch_result:
        print("❌ Validation failed: no result from fetch task")
        raise ValueError("No result from fetch_details_batch task")

    # Check if data was processed
    if not fetch_result.get("has_data"):
        reason = fetch_result.get("reason", "unknown")

        # Acceptable reasons - no data to process
        if reason in ["no_data", "all_processed"]:
            print(f"✅ Validation passed: {reason} (acceptable)")
            return {"validation": "passed", "reason": reason}
        else:
            print(f"❌ Validation failed: {reason}")
            raise ValueError(f"Fetch failed: {reason}")

    # Data was processed successfully
    contratacoes_processed = fetch_result.get("contratacoes_processed", 0)
    chunks_saved = fetch_result.get("chunks_saved", 0)
    metadata = fetch_result.get("metadata", {})

    print(
        f"✅ Validation passed: {contratacoes_processed} contratacoes processed, "
        f"{chunks_saved} chunks saved"
    )

    return {
        "validation": "passed",
        "contratacoes_processed": contratacoes_processed,
        "chunks_saved": chunks_saved,
        "total_itens": metadata.get("total_itens", 0),
        "total_arquivos": metadata.get("total_arquivos", 0),
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

    # Task 1: Fetch batch with auto-resume (saves directly to Bronze)
    task_fetch_batch = PythonOperator(
        task_id="fetch_details_batch",
        python_callable=fetch_details_batch,
    )

    # Task 2: Validate processing
    task_validate = PythonOperator(
        task_id="validate_ingestion",
        python_callable=validate_ingestion,
    )

    # Task 3: Cleanup temp files
    task_cleanup = PythonOperator(
        task_id="cleanup_temp_files",
        python_callable=cleanup_temp_files,
        trigger_rule="all_done",
    )

    # Define task dependencies
    # Note: append_to_bronze was removed - service saves chunks directly
    task_fetch_batch >> task_validate >> task_cleanup
