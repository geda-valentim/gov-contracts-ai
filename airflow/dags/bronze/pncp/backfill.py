"""
Bronze Layer: PNCP Backfill DAG with State Management.

One-time backfill for historical PNCP data with incremental deduplication.

Schedule: Manual trigger only
Data: Parquet format for last N days (default 90)
Use case: Initial data load or recovery

**INCREMENTAL BACKFILL:**
- Uses StateManager to track processed record IDs
- Skips already-processed records (safe re-runs)
- Only uploads NEW records to Bronze
- Updates state after successful upload
"""

import sys

sys.path.insert(0, "/opt/airflow")
sys.path.insert(0, "/opt/airflow/dags")

from datetime import UTC, datetime, timedelta

from airflow import DAG

# Airflow 3.x imports
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator

from backend.app.domains.pncp import ModalidadeContratacao
from backend.app.services import DataTransformationService, StateManager
from utils.clients import get_minio_client, get_pncp_client

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,  # Disabled for development
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=6),
}


def backfill_pncp_data(days_back: int = 90, **context) -> dict:
    """
    Backfill PNCP data for the last N days with incremental state management.

    Args:
        days_back: Number of days to backfill

    Returns:
        Dict with backfill metadata
    """
    pncp_client = get_pncp_client()
    storage = get_minio_client()
    state_manager = StateManager()
    transformation_service = DataTransformationService()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    print(f"🔄 Backfilling from {start_date.date()} to {end_date.date()}")

    # Fetch ALL modalidades (13 total)
    modalidades = ModalidadeContratacao.get_all()

    total_fetched = 0
    total_new_records = 0
    total_duplicates_filtered = 0
    uploaded_files = []

    print(f"📋 Backfilling {len(modalidades)} modalidades with incremental state...")

    # Backfill day by day
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")

        print(f"\n📅 Processing {current_date.date()}...")

        day_data = []

        for idx, modalidade in enumerate(modalidades, 1):
            print(f"  [{idx}/{len(modalidades)}] {modalidade.descricao}...")
            data = pncp_client.fetch_all_contratacoes_by_date(
                data_inicial=date_str,
                data_final=date_str,
                modalidades=[modalidade],
            )
            day_data.extend(data)

        total_fetched += len(day_data)

        if not day_data:
            print(f"  ⚠️  No data from API for {current_date.date()}")
            current_date += timedelta(days=1)
            continue

        # ===== INCREMENTAL STATE FILTERING =====
        # Filter only NEW records (not previously processed)
        new_records, filter_stats = state_manager.filter_new_records(
            source="pncp",
            date=current_date,
            records=day_data,
            id_field="numeroControlePNCP",
        )

        print(
            f"  📊 State Filtering: {filter_stats['total_input']} fetched → "
            f"{filter_stats['new_records']} new ({filter_stats['already_processed']} duplicates)"
        )

        total_duplicates_filtered += filter_stats["already_processed"]

        # If no new records, skip this day
        if not new_records:
            print(f"  ⏭️  All records already processed for {current_date.date()}")
            current_date += timedelta(days=1)
            continue

        # ===== TRANSFORM AND VALIDATE =====
        # Validate new records
        validation_report = transformation_service.validate_records(new_records)

        # Transform to DataFrame (no deduplication needed - already done by state)
        df = transformation_service.to_dataframe(new_records, deduplicate=False)

        # Add metadata
        metadata = {
            "data_inicial": date_str,
            "data_final": date_str,
            "modalidades": [m.descricao for m in modalidades],
            "ingestion_timestamp": datetime.now().isoformat(),
            "record_count": len(new_records),
        }
        df = transformation_service.add_metadata_columns(df, metadata)

        # ===== UPLOAD TO BRONZE =====
        # Upload as Parquet
        s3_key = storage.upload_to_bronze(
            data=df,
            source="pncp",
            date=current_date,
            format="parquet",
        )

        uploaded_files.append(s3_key)
        total_new_records += len(new_records)

        # ===== UPDATE STATE =====
        # Extract IDs from new records
        new_ids = [r.get("numeroControlePNCP") for r in new_records if r.get("numeroControlePNCP")]

        # Update state with new processed IDs
        state_manager.update_state(
            source="pncp",
            date=current_date,
            new_ids=new_ids,
            execution_metadata={
                "backfill": True,
                "new_records": len(new_records),
                "duplicates_filtered": filter_stats["already_processed"],
                "validation": validation_report,
            },
        )

        print(f"  ✅ Uploaded {len(new_records)} NEW records as Parquet → {s3_key}")
        print(f"  💾 State updated: {len(new_ids)} IDs added")

        # Move to next day
        current_date += timedelta(days=1)

    print("\n" + "=" * 80)
    print("🎉 Backfill Complete!")
    print(f"📊 Total fetched from API: {total_fetched:,} records")
    print(f"✨ New records uploaded: {total_new_records:,} records")
    print(f"🔄 Duplicates filtered: {total_duplicates_filtered:,} records")
    print(f"📁 Files uploaded: {len(uploaded_files)} Parquet files")
    print(
        f"💡 Efficiency: {(total_duplicates_filtered/total_fetched*100) if total_fetched > 0 else 0:.1f}% duplicates filtered"
    )
    print("=" * 80)

    return {
        "days_backfilled": days_back,
        "total_fetched": total_fetched,
        "total_new_records": total_new_records,
        "total_duplicates_filtered": total_duplicates_filtered,
        "files_uploaded": len(uploaded_files),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "efficiency_rate": (total_duplicates_filtered / total_fetched * 100)
        if total_fetched > 0
        else 0,
    }


with DAG(
    dag_id="bronze_pncp_backfill",
    default_args=default_args,
    description="Backfill of historical PNCP data with incremental state management",
    schedule=None,  # Manual trigger only
    start_date=datetime(2025, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "backfill", "manual", "incremental"],
) as dag:
    task_backfill = PythonOperator(
        task_id="backfill_pncp_data",
        python_callable=backfill_pncp_data,
        op_kwargs={"days_back": 90},
    )
