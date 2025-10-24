"""
DAG: bronze_pncp_cleanup_day

Clean all PNCP data for a specific day (on-demand execution only).

This DAG removes:
1. Contratações from Bronze layer (pncp/year=YYYY/month=MM/day=DD/)
2. Details from Bronze layer (pncp_details/year=YYYY/month=MM/day=DD/)
3. State files (pncp/_state/year=YYYY/month=MM/day=DD/)
4. Details state files (pncp_details/_state/itens/ and arquivos/)

**IMPORTANT:**
- This DAG has NO SCHEDULE (manual trigger only)
- Always provide target date via DAG conf
- Irreversible operation - data will be deleted!
- Use with caution in production

**Usage:**
```bash
# Cleanup data for 2025-10-23
airflow dags trigger bronze_pncp_cleanup_day \\
  --conf '{"target_date": "2025-10-23"}'

# Cleanup with dry-run (just list files, don't delete)
airflow dags trigger bronze_pncp_cleanup_day \\
  --conf '{"target_date": "2025-10-23", "dry_run": true}'
```
"""

from datetime import datetime, timedelta
from typing import Dict

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import MinIO client from utils
from utils.clients import get_minio_client


# DAG default arguments
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,  # No retries for cleanup operations
    "execution_timeout": timedelta(minutes=30),
}


def cleanup_day_data(**context) -> Dict:
    """
    Clean all PNCP data for a specific day.

    This task removes:
    1. Contratações from Bronze (pncp/)
    2. Details from Bronze (pncp_details/)
    3. State files (pncp/_state/)
    4. Details state files (pncp_details/_state/)

    Returns:
        Dict with cleanup statistics
    """
    dag_run = context.get("dag_run")

    # Get target date from DAG conf
    if not dag_run or not dag_run.conf:
        raise ValueError("DAG conf is required. Provide target_date in conf.")

    target_date_str = dag_run.conf.get("target_date")
    if not target_date_str:
        raise ValueError(
            "target_date is required in DAG conf. Example: '2025-10-23'"
        )

    # Parse target date
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid target_date format: {target_date_str}. Use YYYY-MM-DD"
        ) from e

    # Check dry-run flag
    dry_run = dag_run.conf.get("dry_run", False)

    # Initialize MinIO client
    minio_client = get_minio_client()

    print(f"\n{'=' * 70}")
    print("🧹 PNCP DATA CLEANUP")
    print(f"{'=' * 70}")
    print(f"📅 Target date: {target_date.date()}")
    print(f"🔍 Dry run: {dry_run}")
    print(f"{'=' * 70}\n")

    # Construct partition path
    year = target_date.year
    month = target_date.month
    day = target_date.day

    # Prefixes to clean
    prefixes = [
        f"pncp/year={year}/month={month:02d}/day={day:02d}/",
        f"pncp_details/year={year}/month={month:02d}/day={day:02d}/",
        f"pncp/_state/year={year}/month={month:02d}/day={day:02d}/",
        f"pncp_details/_state/itens/year={year}/month={month:02d}/day={day:02d}/",
        f"pncp_details/_state/arquivos/year={year}/month={month:02d}/day={day:02d}/",
    ]

    stats = {
        "target_date": target_date_str,
        "dry_run": dry_run,
        "deleted_files": 0,
        "deleted_size_mb": 0,
        "prefixes_cleaned": 0,
        "errors": [],
    }

    # Clean each prefix
    for prefix in prefixes:
        try:
            print(f"\n📁 Cleaning prefix: {prefix}")

            # List objects
            objects = minio_client.list_objects(bucket=minio_client.BUCKET_BRONZE, prefix=prefix)

            if not objects:
                print(f"   ℹ️  No objects found")
                continue

            # Calculate total size
            total_size = sum(obj["Size"] for obj in objects)
            total_size_mb = total_size / (1024 * 1024)

            print(f"   📊 Found {len(objects)} objects ({total_size_mb:.2f} MB)")

            if dry_run:
                print(f"   🔍 DRY RUN - Would delete:")
                for obj in objects[:5]:  # Show first 5
                    size_kb = obj["Size"] / 1024
                    print(f"      - {obj['Key']} ({size_kb:.1f} KB)")
                if len(objects) > 5:
                    print(f"      ... and {len(objects) - 5} more files")
            else:
                # Delete objects
                print(f"   🗑️  Deleting {len(objects)} objects...")
                deleted = 0
                for obj in objects:
                    try:
                        minio_client.delete_object(
                            bucket_name=minio_client.BUCKET_BRONZE, object_name=obj["Key"]
                        )
                        deleted += 1
                    except Exception as e:
                        error_msg = f"Failed to delete {obj['Key']}: {e}"
                        stats["errors"].append(error_msg)
                        print(f"   ⚠️  {error_msg}")

                print(f"   ✅ Deleted {deleted}/{len(objects)} objects")
                stats["deleted_files"] += deleted
                stats["deleted_size_mb"] += total_size_mb
                stats["prefixes_cleaned"] += 1

        except Exception as e:
            error_msg = f"Error cleaning prefix {prefix}: {e}"
            stats["errors"].append(error_msg)
            print(f"   ❌ {error_msg}")

    # Print summary
    print(f"\n{'=' * 70}")
    print("📊 CLEANUP SUMMARY")
    print(f"{'=' * 70}")
    print(f"📅 Target date: {stats['target_date']}")
    print(f"🔍 Dry run: {stats['dry_run']}")
    print(f"📁 Prefixes cleaned: {stats['prefixes_cleaned']}/{len(prefixes)}")

    if not dry_run:
        print(f"🗑️  Files deleted: {stats['deleted_files']}")
        print(f"💾 Space freed: {stats['deleted_size_mb']:.2f} MB")

    if stats["errors"]:
        print(f"⚠️  Errors: {len(stats['errors'])}")
        for error in stats["errors"][:5]:
            print(f"   - {error}")
        if len(stats["errors"]) > 5:
            print(f"   ... and {len(stats['errors']) - 5} more errors")
    else:
        print("✅ No errors")

    print(f"{'=' * 70}\n")

    return stats


# Define DAG
with DAG(
    dag_id="bronze_pncp_cleanup_day",
    default_args=default_args,
    description="Clean all PNCP data for a specific day (manual trigger only)",
    schedule=None,  # No schedule - manual trigger only
    start_date=datetime(2025, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "cleanup", "maintenance"],
    doc_md=__doc__,
) as dag:

    # Task: Cleanup day data
    task_cleanup = PythonOperator(
        task_id="cleanup_day_data",
        python_callable=cleanup_day_data,
        doc_md="""
        ## Cleanup Day Data

        Removes all PNCP data (contratações, details, state) for a specific day.

        **Required DAG Conf:**
        - `target_date`: Date to clean (format: YYYY-MM-DD)

        **Optional DAG Conf:**
        - `dry_run`: Set to `true` to list files without deleting (default: false)

        **Example:**
        ```bash
        airflow dags trigger bronze_pncp_cleanup_day \\
          --conf '{"target_date": "2025-10-23"}'
        ```
        """,
    )

    # Single task - no dependencies
    task_cleanup
