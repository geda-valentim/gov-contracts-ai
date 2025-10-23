#!/usr/bin/env python3
"""
Test DAG functions directly without Airflow.

Usage:
    python scripts/test_dag_directly.py
    python scripts/test_dag_directly.py --modalidades 3
    python scripts/test_dag_directly.py --pages 5
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "airflow"))

from backend.app.core.minio_client import MinIOClient


# Mock Airflow context
class MockContext:
    """Mock Airflow context for testing."""

    def __init__(self):
        self.execution_date = datetime.now()
        self.task_instance = MockTaskInstance()
        self.ti = self.task_instance

    def __getitem__(self, key):
        return getattr(self, key)


class MockTaskInstance:
    """Mock Airflow TaskInstance."""

    def __init__(self):
        self._xcom_data = {}

    def xcom_push(self, key, value):
        print(
            f"📤 XCom Push: {key} = {type(value).__name__} ({len(value) if isinstance(value, list) else 'N/A'} items)"
        )
        self._xcom_data[key] = value

    def xcom_pull(self, task_ids=None, key=None):
        print(f"📥 XCom Pull: task_ids={task_ids}, key={key}")
        return self._xcom_data.get(key)


def test_hourly_dag(num_pages=5, num_modalidades=3):
    """
    Test hourly ingestion DAG functions directly.

    Args:
        num_pages: Number of pages to fetch per modalidade
        num_modalidades: Number of modalidades to test (3 for fast, 13 for complete)
    """
    print("=" * 80)
    print("🧪 TESTING HOURLY INGESTION DAG")
    print("=" * 80)
    print(f"Settings: {num_pages} pages × {num_modalidades} modalidades")
    print()

    # Import DAG functions
    sys.path.insert(0, str(project_root / "airflow" / "dags"))

    # Import the actual functions from the DAG
    from bronze.pncp_hourly_ingestion import (
        fetch_last_n_pages_task,
        transform_to_dataframe_task,
        upload_to_bronze_task,
        validate_bronze_data_task,
    )

    # Create mock context
    context = MockContext()

    print("=" * 80)
    print("TASK 1: fetch_last_n_pages_task")
    print("=" * 80)

    try:
        # Temporarily override NUM_PAGES for testing
        import bronze.pncp_hourly_ingestion as dag_module

        # Patch the function to use fewer pages/modalidades
        result1 = fetch_last_n_pages_task(**context)
        print(f"✅ Task 1 Result: {result1}")
        print()

    except Exception as e:
        print(f"❌ Task 1 Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("=" * 80)
    print("TASK 2: transform_to_dataframe_task")
    print("=" * 80)

    try:
        result2 = transform_to_dataframe_task(**context)
        print(f"✅ Task 2 Result: {result2}")
        print()
    except Exception as e:
        print(f"❌ Task 2 Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("=" * 80)
    print("TASK 3: upload_to_bronze_task")
    print("=" * 80)

    try:
        result3 = upload_to_bronze_task(**context)
        print(f"✅ Task 3 Result: {result3}")
        print()
    except Exception as e:
        print(f"❌ Task 3 Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("=" * 80)
    print("TASK 4: validate_bronze_data_task")
    print("=" * 80)

    try:
        result4 = validate_bronze_data_task(**context)
        print(f"✅ Task 4 Result: {result4}")
        print()
    except Exception as e:
        print(f"❌ Task 4 Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("=" * 80)
    print("🎉 ALL TASKS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print()
    print("📊 Summary:")
    print(f"  - Records Fetched: {result1.get('record_count', 'N/A')}")
    print(f"  - Records After Transform: {result2}")
    print(f"  - S3 Key: {result3.get('s3_key', 'N/A')}")
    print(f"  - Validation: {result4.get('validated', False)}")
    print()

    return True


def test_single_task(task_name="fetch"):
    """
    Test a single task function.

    Args:
        task_name: Name of task to test (fetch, transform, upload, validate)
    """
    print(f"🧪 Testing single task: {task_name}")

    sys.path.insert(0, str(project_root / "airflow" / "dags"))

    context = MockContext()

    if task_name == "fetch":
        from bronze.pncp_hourly_ingestion import fetch_last_n_pages_task

        result = fetch_last_n_pages_task(**context)
        print(f"✅ Result: {result}")

    elif task_name == "transform":
        # Need to run fetch first to populate XCom
        from bronze.pncp_hourly_ingestion import (
            fetch_last_n_pages_task,
            transform_to_dataframe_task,
        )

        print("Running fetch first...")
        fetch_last_n_pages_task(**context)
        print("Now running transform...")
        result = transform_to_dataframe_task(**context)
        print(f"✅ Result: {result}")

    elif task_name == "validate":
        print("This requires data to be uploaded to MinIO first.")
        print("Run full DAG test instead: python scripts/test_dag_directly.py")

    else:
        print(f"❌ Unknown task: {task_name}")
        print("Available: fetch, transform, upload, validate")


def test_pncp_client():
    """Test PNCP client directly."""
    print("🧪 Testing PNCP Client")
    print("=" * 80)

    from backend.app.core.pncp_client import PNCPClient
    from backend.app.domains.pncp import ModalidadeContratacao

    client = PNCPClient()

    # Test with today's date
    today = datetime.now()
    yesterday = today.replace(day=today.day - 1)

    date_str = today.strftime("%Y%m%d")
    yesterday_str = yesterday.strftime("%Y%m%d")

    print(f"📅 Fetching data for: {yesterday_str} to {date_str}")
    print("📋 Modalidade: Pregão Eletrônico")
    print("📄 Pages: 1-3 (test mode)")
    print()

    try:
        # Fetch just 3 pages for testing
        result = client.fetch_contratacoes_by_date(
            data_inicial=yesterday_str,
            data_final=date_str,
            modalidades=[ModalidadeContratacao.PREGAO_ELETRONICO],
            pagina=1,
            tamanho_pagina=50,
        )

        data = result.get("data", [])

        print("✅ Success!")
        print(f"  - Records: {len(data)}")
        print(f"  - Total Pages: {result.get('totalPaginas', 'N/A')}")
        print(f"  - Total Records: {result.get('totalRegistros', 'N/A')}")

        if data:
            print("\n📄 Sample Record:")
            sample = data[0]
            print(f"  - numeroControlePNCP: {sample.get('numeroControlePNCP', 'N/A')}")
            print(f"  - objetoCompra: {sample.get('objetoCompra', 'N/A')[:80]}...")
            print(f"  - valorTotalEstimado: {sample.get('valorTotalEstimado', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_minio_client():
    """Test MinIO client directly."""
    print("🧪 Testing MinIO Client")
    print("=" * 80)

    try:
        client = MinIOClient(
            endpoint_url="http://minio:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
        )

        print("✅ MinIO client created")

        # List buckets
        buckets = client.list_buckets()
        print(f"📦 Buckets: {buckets}")

        # Check bronze bucket exists
        if client.bucket_exists(client.BUCKET_BRONZE):
            print(f"✅ Bronze bucket exists: {client.BUCKET_BRONZE}")

            # List recent files
            objects = client.list_objects(
                client.BUCKET_BRONZE, prefix="pncp/", max_keys=5
            )
            print(f"📄 Recent files: {len(objects)}")

            for obj in objects[:3]:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print(f"⚠️  Bronze bucket does not exist: {client.BUCKET_BRONZE}")
            print("Creating bucket...")
            client.create_bucket(client.BUCKET_BRONZE)
            print("✅ Bucket created!")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test DAG functions directly")
    parser.add_argument(
        "--task",
        choices=["full", "fetch", "transform", "pncp", "minio"],
        default="full",
        help="Which task to test (default: full DAG)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Number of pages to fetch per modalidade (default: 5)",
    )
    parser.add_argument(
        "--modalidades",
        type=int,
        default=3,
        help="Number of modalidades to fetch (3=fast, 13=complete, default: 3)",
    )

    args = parser.parse_args()

    print()
    print("🚀 DAG Direct Test Runner")
    print("=" * 80)
    print()

    success = False

    if args.task == "full":
        success = test_hourly_dag(
            num_pages=args.pages, num_modalidades=args.modalidades
        )
    elif args.task == "fetch":
        success = test_single_task("fetch")
    elif args.task == "transform":
        success = test_single_task("transform")
    elif args.task == "pncp":
        success = test_pncp_client()
    elif args.task == "minio":
        success = test_minio_client()

    print()
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
