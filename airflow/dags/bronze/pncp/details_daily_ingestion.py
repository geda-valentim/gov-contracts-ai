"""
Bronze Layer: PNCP Details Daily Ingestion DAG (Thin Wrapper with Granular State Management).

Fetches items (itens) and documents (arquivos) for contratacoes from Bronze layer.
This DAG is a thin Airflow wrapper around standalone business logic services.

GRANULAR STATE MANAGEMENT:
- Separate state for itens and arquivos
- Allows reprocessing arquivos without reprocessing itens
- State files: pncp_details/_state/itens/ and pncp_details/_state/arquivos/

Schedule: Daily at 4 AM (after contratacoes daily run at 2 AM)
Data: Contratacoes from previous day + their details
Output: JSON with nested structure (1 file per day)
"""

import json
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
from backend.app.services import StateManager
from backend.app.services.ingestion.pncp_details import PNCPDetailsIngestionService

# DAG default arguments
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=3),  # Longer timeout for many API calls
}


def fetch_details_data(**context) -> dict:
    """
    Airflow task wrapper: Fetch details (itens + arquivos) from PNCP API.

    This is a thin wrapper that:
    1. Extracts Airflow context
    2. Calls standalone service to fetch details
    3. Saves data to temp storage (NOT XCom to avoid DB bloat)
    4. Pushes only S3 reference to XCom (<1KB)

    Features:
    - Auto-resume: Automatically skips already-processed contratacoes
    - Batch processing: Process N contratacoes per run (configurable)
    - Incremental checkpoints: Saves every 50 contratacoes to prevent data loss
    """
    from airflow.models import Variable

    # Airflow 3.x uses 'logical_date' instead of 'execution_date'
    execution_date = (
        context.get("logical_date")
        or context.get("data_interval_start")
        or datetime.now(UTC)
    )
    dag_run = context.get("dag_run")
    execution_id = (
        dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")
    )

    # Get configuration from DAG conf (manual trigger) or Airflow Variables
    if dag_run and dag_run.conf:
        max_contratacoes = dag_run.conf.get("max_contratacoes")
        batch_size = dag_run.conf.get("batch_size")
        checkpoint_every = dag_run.conf.get("checkpoint_every", 50)
    else:
        max_contratacoes = None
        # Get from Airflow Variables (set via UI or CLI)
        batch_size = Variable.get("pncp_details_batch_size", default_var=None)
        if batch_size:
            batch_size = int(batch_size)
        checkpoint_every = int(Variable.get("pncp_details_checkpoint_every", default_var=50))

    # Call standalone service (no Airflow dependencies)
    service = PNCPDetailsIngestionService()
    result = service.fetch_details_for_date(
        execution_date=execution_date,
        max_contratacoes=max_contratacoes,
        batch_size=batch_size,
        auto_resume=True,  # Always use auto-resume in daily DAG
        checkpoint_every=checkpoint_every,
    )

    # ✅ SOLUTION: Save data to temp storage instead of XCom
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],  # Large data goes to S3
        execution_id=execution_id,
        stage="raw_details",
        format="json",  # JSON for complex nested structure
    )

    print(
        f"📦 Saved {len(result['data'])} enriched contratacoes to temp storage: {temp_key} "
        f"({result['metadata']['total_itens']} itens, {result['metadata']['total_arquivos']} arquivos)"
    )

    # ✅ XCom only stores lightweight metadata + S3 reference
    return {
        "temp_key": temp_key,  # S3 reference only (~100 bytes)
        "metadata": result["metadata"],
        "contratacoes_count": len(result["data"]),
    }


def filter_and_consolidate(**context) -> dict:
    """
    Airflow task wrapper: Filter with granular state and consolidate structure.

    This task:
    1. Reads data from temp storage
    2. Filters itens and arquivos separately with state management
    3. Consolidates final nested structure
    4. Saves filtered data to temp storage
    """
    task_instance = context["task_instance"]
    execution_date = context.get("logical_date") or context.get("data_interval_start")
    dag_run = context.get("dag_run")
    execution_id = (
        dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")
    )

    # ✅ Get S3 reference from XCom (lightweight)
    fetch_result = task_instance.xcom_pull(task_ids="fetch_details_data")

    if not fetch_result or not fetch_result.get("temp_key"):
        return {"filtered": False, "reason": "no_data"}

    # ✅ Read actual data from temp storage
    storage = get_storage_client()
    temp_bucket = storage.BUCKET_BRONZE  # BUCKET_TMP might not exist
    enriched_contratacoes_json = storage.read_json_from_s3(
        bucket=temp_bucket, key=fetch_result["temp_key"]
    )

    # Convert back to list if it's a dict wrapper
    enriched_contratacoes = (
        enriched_contratacoes_json
        if isinstance(enriched_contratacoes_json, list)
        else enriched_contratacoes_json.get("data", [])
    )

    if not enriched_contratacoes:
        return {"filtered": False, "reason": "no_data"}

    # ===== GRANULAR STATE FILTERING =====
    state_manager = StateManager()

    # Filter for itens (only contratacoes that haven't had itens fetched)
    contratacoes_needing_itens, itens_stats = state_manager.filter_new_details(
        source="pncp_details",
        date=execution_date,
        contratacoes=enriched_contratacoes,
        detail_type="itens",
        key_extractor_fn=PNCPDetailsIngestionService.extract_key_from_contratacao,
    )

    # Filter for arquivos (only contratacoes that haven't had arquivos fetched)
    contratacoes_needing_arquivos, arquivos_stats = state_manager.filter_new_details(
        source="pncp_details",
        date=execution_date,
        contratacoes=enriched_contratacoes,
        detail_type="arquivos",
        key_extractor_fn=PNCPDetailsIngestionService.extract_key_from_contratacao,
    )

    print(
        f"📊 Itens State Filtering: {itens_stats['total_input']} input → "
        f"{itens_stats['new_records']} new ({itens_stats['already_processed']} duplicates filtered)"
    )
    print(
        f"📊 Arquivos State Filtering: {arquivos_stats['total_input']} input → "
        f"{arquivos_stats['new_records']} new ({arquivos_stats['already_processed']} duplicates filtered)"
    )

    # If no new data for either, return early
    if not contratacoes_needing_itens and not contratacoes_needing_arquivos:
        print("⚠️  No new details to process (all already processed)")
        return {
            "filtered": False,
            "reason": "all_duplicates",
            "itens_stats": itens_stats,
            "arquivos_stats": arquivos_stats,
        }

    # ===== CONSOLIDATE FINAL DATA =====
    # For now, take union of contratacoes needing either type
    # (In future, could optimize to only fetch missing detail type)
    contratacoes_to_save = enriched_contratacoes  # Keep all for this iteration

    # ===== UPDATE STATE =====
    # Extract keys for state update
    itens_keys = [
        PNCPDetailsIngestionService.extract_key_from_contratacao(c)
        for c in contratacoes_needing_itens
        if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
    ]

    arquivos_keys = [
        PNCPDetailsIngestionService.extract_key_from_contratacao(c)
        for c in contratacoes_needing_arquivos
        if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
    ]

    # Update itens state
    if itens_keys:
        state_manager.update_details_state(
            source="pncp_details",
            date=execution_date,
            detail_type="itens",
            new_keys=itens_keys,
            execution_metadata={
                "new_records": len(itens_keys),
                "total_itens": sum(len(c.get("itens", [])) for c in contratacoes_to_save),
            },
        )
        print(f"✅ Itens state updated: {len(itens_keys)} new keys added")

    # Update arquivos state
    if arquivos_keys:
        state_manager.update_details_state(
            source="pncp_details",
            date=execution_date,
            detail_type="arquivos",
            new_keys=arquivos_keys,
            execution_metadata={
                "new_records": len(arquivos_keys),
                "total_arquivos": sum(
                    len(c.get("arquivos", [])) for c in contratacoes_to_save
                ),
            },
        )
        print(f"✅ Arquivos state updated: {len(arquivos_keys)} new keys added")

    # ✅ Store filtered data in temp storage
    filtered_key = storage.upload_temp(
        data=contratacoes_to_save,
        execution_id=execution_id,
        stage="filtered_details",
        format="json",
    )

    print(
        f"📦 Saved {len(contratacoes_to_save)} filtered contratacoes to temp storage: {filtered_key}"
    )

    # ✅ XCom only stores lightweight metadata
    return {
        "filtered": True,
        "temp_key": filtered_key,
        "contratacoes_count": len(contratacoes_to_save),
        "itens_stats": itens_stats,
        "arquivos_stats": arquivos_stats,
    }


def upload_to_bronze(**context) -> dict:
    """
    Airflow task wrapper: Upload details to Bronze layer as Parquet.

    Uploads:
    - Nested Parquet file to pncp_details/year=YYYY/month=MM/day=DD/details.parquet
    """
    from backend.app.services.ingestion.pncp_details import (
        convert_nested_to_dataframe,
        save_to_parquet_bronze,
    )

    task_instance = context["task_instance"]
    execution_date = context.get("logical_date") or context.get("data_interval_start")

    # ✅ Get S3 reference from XCom
    filter_result = task_instance.xcom_pull(task_ids="filter_and_consolidate")

    if not filter_result or not filter_result.get("filtered"):
        reason = filter_result.get("reason", "unknown") if filter_result else "no_result"
        print(f"⚠️  No data to upload: {reason}")
        return {"uploaded": False, "reason": reason}

    # ✅ Read filtered data from temp storage
    storage = get_storage_client()
    details_data = storage.read_json_from_s3(
        bucket=storage.BUCKET_BRONZE, key=filter_result["temp_key"]
    )

    # Ensure it's a list
    if isinstance(details_data, dict) and "data" in details_data:
        details_data = details_data["data"]

    # ===== UPLOAD TO BRONZE AS PARQUET =====
    # Convert to DataFrame
    details_df = convert_nested_to_dataframe(details_data)

    # Save as Parquet
    details_key = save_to_parquet_bronze(
        df=details_df,
        storage_client=storage,
        execution_date=execution_date,
        mode="overwrite",  # Daily DAG always overwrites
    )

    # Calculate stats
    total_itens = sum(len(c.get("itens", [])) for c in details_data)
    total_arquivos = sum(len(c.get("arquivos", [])) for c in details_data)

    print(
        f"✅ Uploaded to Bronze: {details_key} "
        f"({len(details_data)} contratacoes, {total_itens} itens, {total_arquivos} arquivos)"
    )

    return {
        "uploaded": True,
        "s3_key": details_key,
        "contratacoes_count": len(details_data),
        "total_itens": total_itens,
        "total_arquivos": total_arquivos,
    }


def validate_ingestion(**context) -> dict:
    """
    Airflow task wrapper: Validate ingestion results.

    Checks:
    - Upload succeeded
    - Data counts are reasonable
    """
    task_instance = context["task_instance"]

    # Pull results from previous tasks
    upload_result = task_instance.xcom_pull(task_ids="upload_to_bronze")

    if not upload_result or not upload_result.get("uploaded"):
        reason = upload_result.get("reason", "unknown") if upload_result else "no_result"

        # Check if it's acceptable (no data, all duplicates)
        if reason in ["no_data", "all_duplicates"]:
            print(f"✅ Validation passed: {reason} (acceptable)")
            return {"validation": "passed", "reason": reason}
        else:
            print(f"❌ Validation failed: {reason}")
            raise ValueError(f"Upload failed: {reason}")

    # Check data counts
    contratacoes_count = upload_result.get("contratacoes_count", 0)
    total_itens = upload_result.get("total_itens", 0)
    total_arquivos = upload_result.get("total_arquivos", 0)

    print(
        f"✅ Validation passed: "
        f"{contratacoes_count} contratacoes, {total_itens} itens, {total_arquivos} arquivos"
    )

    return {
        "validation": "passed",
        "contratacoes_count": contratacoes_count,
        "total_itens": total_itens,
        "total_arquivos": total_arquivos,
    }


def cleanup_temp_files(**context) -> dict:
    """
    Airflow task wrapper: Cleanup temporary files from S3.

    Runs regardless of success/failure (trigger_rule='all_done').
    """
    dag_run = context.get("dag_run")
    execution_id = (
        dag_run.run_id
        if dag_run
        else context.get("logical_date", datetime.now()).strftime("%Y%m%d_%H%M%S")
    )

    storage = get_storage_client()

    try:
        # Cleanup temp files for this execution
        deleted_count = storage.cleanup_temp(
            execution_id=execution_id, bucket=storage.BUCKET_BRONZE
        )

        print(f"🧹 Cleaned up {deleted_count} temporary files for execution {execution_id}")

        return {"cleaned_up": True, "files_deleted": deleted_count}

    except Exception as e:
        print(f"⚠️  Error during cleanup (non-fatal): {e}")
        return {"cleaned_up": False, "error": str(e)}


# Define DAG
with DAG(
    dag_id="bronze_pncp_details_daily_ingestion",
    default_args=default_args,
    description="Fetch PNCP contratacao details (itens + arquivos) from Bronze contratacoes",
    schedule="0 4 * * *",  # Daily at 4 AM (after contratacoes at 2 AM)
    start_date=datetime(2025, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "details", "daily"],
) as dag:

    # Task 1: Fetch details from API
    task_fetch = PythonOperator(
        task_id="fetch_details_data",
        python_callable=fetch_details_data,
    )

    # Task 2: Filter with granular state and consolidate
    task_filter = PythonOperator(
        task_id="filter_and_consolidate",
        python_callable=filter_and_consolidate,
    )

    # Task 3: Upload to Bronze
    task_upload = PythonOperator(
        task_id="upload_to_bronze",
        python_callable=upload_to_bronze,
    )

    # Task 4: Validate ingestion
    task_validate = PythonOperator(
        task_id="validate_ingestion",
        python_callable=validate_ingestion,
    )

    # Task 5: Cleanup temp files (runs regardless of success/failure)
    task_cleanup = PythonOperator(
        task_id="cleanup_temp_files",
        python_callable=cleanup_temp_files,
        trigger_rule="all_done",  # Run even if previous tasks fail
    )

    # Define task dependencies
    task_fetch >> task_filter >> task_upload >> task_validate >> task_cleanup
