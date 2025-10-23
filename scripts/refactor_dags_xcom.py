#!/usr/bin/env python3
"""
Script to refactor PNCP DAGs to use S3 temp storage instead of XCom.

This prevents Airflow database bloat by storing large datasets in S3
and only passing lightweight references through XCom.
"""

import re
from pathlib import Path


def refactor_dag_file(file_path: Path) -> None:
    """Refactor a single DAG file to use S3 temp storage."""
    print(f"\n📝 Refactoring {file_path.name}...")

    content = file_path.read_text()

    # Check if already refactored
    if "upload_temp" in content:
        print(f"✅ {file_path.name} already refactored, skipping")
        return

    # 1. Update fetch_pncp_data function to save to temp storage
    content = re.sub(
        r'def fetch_pncp_data\(\*\*context\) -> dict:\n    """\n    (.*?)\n\n    This is a thin wrapper that:\n    1\. Extracts Airflow context\n    2\. Calls standalone service\n    3\. Pushes results to XCom\n    """',
        r'''def fetch_pncp_data(**context) -> dict:
    """
    \1

    This is a thin wrapper that:
    1. Extracts Airflow context
    2. Calls standalone service
    3. Saves data to temp storage (NOT XCom to avoid DB bloat)
    4. Pushes only S3 reference to XCom (<1KB)
    """''',
        content,
        flags=re.DOTALL,
    )

    # 2. Add execution_id extraction in fetch function
    content = re.sub(
        r'(execution_date = .*?\n)',
        r'''\1    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")

''',
        content,
        count=1,
    )

    # 3. Replace XCom push with temp storage upload in fetch function
    content = re.sub(
        r'    # Push to XCom for next task\n    context\["task_instance"\]\.xcom_push\(key="fetched_data", value=result\["data"\]\)\n    context\["task_instance"\]\.xcom_push\(key="metadata", value=result\["metadata"\]\)\n\n    return result\["metadata"\]',
        r'''    # ✅ SOLUTION: Save data to temp storage instead of XCom
    # XCom only stores the S3 reference (~100 bytes) instead of all data (megabytes)
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],  # Large data goes to S3
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
        "temp_key": temp_key,  # S3 reference only (~100 bytes)
        "metadata": result["metadata"],
        "record_count": len(result["data"]),
    }''',
        content,
    )

    # 4. Update transform_data docstring
    content = re.sub(
        r'(def transform_data\(\*\*context\) -> dict:\n    """\n    .*?)\n    1\. Pulls data from XCom\n    2\. Loads state to filter duplicates',
        r'''\1
    1. Reads S3 reference from XCom (not data itself)
    2. Loads data from temp storage
    3. Loads state to filter duplicates''',
        content,
        flags=re.DOTALL,
    )

    # 5. Update transform_data to read from temp storage
    content = re.sub(
        r'(def transform_data\(\*\*context\) -> dict:.*?execution_date = .*?\n)',
        r'''\1    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else execution_date.strftime("%Y%m%d_%H%M%S")

''',
        content,
        flags=re.DOTALL,
        count=1,
    )

    content = re.sub(
        r'    # Get data from previous task\n    raw_data = task_instance\.xcom_pull\(task_ids="fetch_pncp_data", key="fetched_data"\)\n\n    if not raw_data:\n        return \{"transformed": False, "reason": "no_data"\}',
        r'''    # ✅ Get S3 reference from XCom (lightweight)
    fetch_result = task_instance.xcom_pull(task_ids="fetch_pncp_data")

    if not fetch_result or not fetch_result.get("temp_key"):
        return {"transformed": False, "reason": "no_data"}

    # ✅ Read actual data from temp storage (not from XCom)
    storage = get_storage_client()
    raw_df = storage.read_temp(bucket=storage.BUCKET_BRONZE, key=fetch_result["temp_key"])

    # Convert DataFrame back to list of dicts for processing
    raw_data = raw_df.to_dict(orient="records")

    if not raw_data:
        return {"transformed": False, "reason": "no_data"}''',
        content,
    )

    # 6. Update metadata extraction
    content = re.sub(
        r'    # Add metadata\n    metadata = task_instance\.xcom_pull\(task_ids="fetch_pncp_data", key="metadata"\)',
        r'''    # Add metadata
    metadata = fetch_result.get("metadata", {})''',
        content,
    )

    # 7. Replace XCom push with temp storage in transform_data
    content = re.sub(
        r'    # Store DataFrame in context for next task\n    task_instance\.xcom_push\(key="dataframe", value=df\).*?\n    task_instance\.xcom_push\(key="validation_report", value=validation_report\)\n    task_instance\.xcom_push\(key="filter_stats", value=filter_stats\)\n\n    return \{\n        "transformed": True,\n        "record_count": len\(df\),\n        "validation": validation_report,\n        "filter_stats": filter_stats,\n    \}',
        r'''    # ✅ Store DataFrame in temp storage (not XCom)
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
    }''',
        content,
    )

    # 8. Update upload_to_bronze to read from temp storage
    content = re.sub(
        r'(def upload_to_bronze\(\*\*context\) -> dict:\n    """\n    .*?)\n    1\. Pulls DataFrame from XCom\n    2\. Uploads directly as Parquet.*?\n    3\. Returns upload result',
        r'''\1
    1. Reads S3 reference from XCom
    2. Loads DataFrame from temp storage
    3. Uploads to final Bronze location
    4. Returns upload result''',
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r'    # Get DataFrame from previous task\n    df = task_instance\.xcom_pull\(task_ids="transform_data", key="dataframe"\)',
        r'''    # ✅ Get S3 reference from XCom (lightweight)
    transform_result = task_instance.xcom_pull(task_ids="transform_data")

    if not transform_result or not transform_result.get("temp_key"):
        return {"uploaded": False, "reason": "no_data"}

    # ✅ Read DataFrame from temp storage
    storage = get_storage_client()
    df = storage.read_temp(
        bucket=storage.BUCKET_BRONZE, key=transform_result["temp_key"]
    )''',
        content,
    )

    # 9. Fix upload_to_bronze storage initialization (remove duplicate)
    content = re.sub(
        r'    # Upload DataFrame directly to Bronze as Parquet \(default format\)\n    # No need to convert to JSON - Parquet handles pandas types natively\n    storage = get_storage_client\(\)',
        r'''    # Upload DataFrame to final Bronze location''',
        content,
    )

    # 10. Add cleanup function before validate_ingestion
    cleanup_function = '''def cleanup_temp_files(**context) -> dict:
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


'''

    content = re.sub(
        r'(def validate_ingestion\(\*\*context\) -> dict:)',
        cleanup_function + r'\1',
        content,
    )

    # 11. Update validate_ingestion to extract from transform result
    content = re.sub(
        r'    # Get results from previous tasks\n    transform_result = task_instance\.xcom_pull\(task_ids="transform_data"\)\n    upload_result = task_instance\.xcom_pull\(task_ids="upload_to_bronze"\)\n    validation_report = task_instance\.xcom_pull\(task_ids="transform_data", key="validation_report"\)\n    filter_stats = task_instance\.xcom_pull\(task_ids="transform_data", key="filter_stats"\)',
        r'''    # Get results from previous tasks (only lightweight metadata, not data)
    transform_result = task_instance.xcom_pull(task_ids="transform_data")
    upload_result = task_instance.xcom_pull(task_ids="upload_to_bronze")

    # Extract validation info and filter stats from transform result
    validation_report = transform_result.get("validation") if transform_result else None
    filter_stats = transform_result.get("filter_stats") if transform_result else None''',
        content,
    )

    # 12. Add cleanup task in DAG definition
    content = re.sub(
        r'(    # Task 4: Validate ingestion\n    task_validate = PythonOperator\(\n        task_id="validate_ingestion",\n        python_callable=validate_ingestion,\n    \)\n\n    # Define task dependencies\n    task_fetch >> task_transform >> task_upload >> task_validate)',
        r'''    # Task 4: Validate ingestion
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
    task_fetch >> task_transform >> task_upload >> task_validate >> task_cleanup''',
        content,
    )

    # Write back
    file_path.write_text(content)
    print(f"✅ Successfully refactored {file_path.name}")


def main():
    """Refactor all PNCP DAGs."""
    dag_files = [
        Path("/home/gov-contracts-ai/airflow/dags/bronze/pncp/daily_ingestion.py"),
        Path("/home/gov-contracts-ai/airflow/dags/bronze/pncp/backfill.py"),
    ]

    print("🔧 Refactoring PNCP DAGs to use S3 temp storage instead of XCom...")

    for dag_file in dag_files:
        if not dag_file.exists():
            print(f"⚠️  File not found: {dag_file}")
            continue

        # Create backup
        backup_file = dag_file.with_suffix(dag_file.suffix + ".bak2")
        backup_file.write_text(dag_file.read_text())
        print(f"💾 Created backup: {backup_file.name}")

        # Refactor
        refactor_dag_file(dag_file)

    print("\n✅ All DAGs refactored successfully!")
    print("\n📋 Summary:")
    print("  - XCom now stores only S3 references (~100 bytes per task)")
    print("  - Large datasets stored in MinIO/S3 temp storage")
    print("  - Cleanup task removes temp files after DAG completion")
    print("  - Airflow database will stay lightweight")


if __name__ == "__main__":
    main()
