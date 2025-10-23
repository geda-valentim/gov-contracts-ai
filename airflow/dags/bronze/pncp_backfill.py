"""
Bronze Layer: PNCP Backfill DAG.

One-time backfill for historical PNCP data.

Schedule: Manual trigger only
Data: Raw JSON for last 90 days
Use case: Initial data load or recovery
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
from utils.clients import get_minio_client, get_pncp_client

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,  # Disabled for development
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=6),
    # Disabled callbacks for development to avoid DB issues
    # "on_failure_callback": notify_failure,
    # "on_success_callback": notify_success,
}


def backfill_pncp_data(days_back: int = 90, **context) -> dict:
    """
    Backfill PNCP data for the last N days.

    Args:
        days_back: Number of days to backfill

    Returns:
        Dict with backfill metadata
    """
    pncp_client = get_pncp_client()
    minio_client = get_minio_client()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    print(f"Backfilling from {start_date.date()} to {end_date.date()}")

    # Fetch ALL modalidades (13 total)
    modalidades = [
        ModalidadeContratacao.LEILAO_ELETRONICO,
        ModalidadeContratacao.DIALOGO_COMPETITIVO,
        ModalidadeContratacao.CONCURSO,
        ModalidadeContratacao.CONCORRENCIA_ELETRONICA,
        ModalidadeContratacao.CONCORRENCIA_PRESENCIAL,
        ModalidadeContratacao.PREGAO_ELETRONICO,
        ModalidadeContratacao.PREGAO_PRESENCIAL,
        ModalidadeContratacao.DISPENSA_LICITACAO,
        ModalidadeContratacao.INEXIGIBILIDADE,
        ModalidadeContratacao.MANIFESTACAO_INTERESSE,
        ModalidadeContratacao.PRE_QUALIFICACAO,
        ModalidadeContratacao.CREDENCIAMENTO,
        ModalidadeContratacao.LEILAO_PRESENCIAL,
    ]

    total_records = 0
    uploaded_files = []

    print(f"Backfilling {len(modalidades)} modalidades...")

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

        if day_data:
            # Upload to bronze
            s3_key = storage.upload_to_bronze(
                data=day_data,
                source="pncp",
                date=current_date,
            )

            uploaded_files.append(s3_key)
            total_records += len(day_data)

            print(f"  ✅ Uploaded {len(day_data)} records → {s3_key}")
        else:
            print(f"  ⚠️  No data for {current_date.date()}")

        # Move to next day
        current_date += timedelta(days=1)

    print(
        f"\n🎉 Backfill complete: {total_records} total records across {len(uploaded_files)} files"
    )

    return {
        "days_backfilled": days_back,
        "total_records": total_records,
        "files_uploaded": len(uploaded_files),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


with DAG(
    dag_id="bronze_pncp_backfill",
    default_args=default_args,
    description="One-time backfill of historical PNCP data (90 days)",
    schedule=None,  # Manual trigger only
    start_date=datetime(2025, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "backfill", "manual"],
) as dag:
    task_backfill = PythonOperator(
        task_id="backfill_pncp_data",
        python_callable=backfill_pncp_data,
        op_kwargs={"days_back": 90},
    )
