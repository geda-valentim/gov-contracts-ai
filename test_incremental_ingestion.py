"""
Test script for incremental ingestion with state management.

This script simulates multiple executions of the hourly DAG to verify:
1. First execution: All records are new
2. Second execution: Some duplicates, some new
3. Third execution: All duplicates (no new records)
"""

import logging
from datetime import datetime

from backend.app.services.state_management import StateManager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_incremental_ingestion():
    """Test incremental ingestion workflow."""

    # Sample data (simulating PNCP API responses)
    # First execution data
    execution_1_data = [
        {"numeroControlePNCP": "07954480000179-1-022746/2025", "valor": 11998.00},
        {"numeroControlePNCP": "07954480000179-1-022747/2025", "valor": 1534.00},
        {"numeroControlePNCP": "45276128000110-1-003529/2025", "valor": 580.00},
    ]

    # Second execution data (2 duplicates + 2 new)
    execution_2_data = [
        {
            "numeroControlePNCP": "07954480000179-1-022746/2025",
            "valor": 11998.00,
        },  # DUP
        {"numeroControlePNCP": "07954480000179-1-022747/2025", "valor": 1534.00},  # DUP
        {"numeroControlePNCP": "45276128000110-1-003529/2025", "valor": 580.00},  # DUP
        {"numeroControlePNCP": "63025530000104-1-004689/2025", "valor": 6140.00},  # NEW
        {
            "numeroControlePNCP": "07954480000179-1-022748/2025",
            "valor": 20000.00,
        },  # NEW
    ]

    # Third execution data (all duplicates)
    execution_3_data = [
        {
            "numeroControlePNCP": "07954480000179-1-022746/2025",
            "valor": 11998.00,
        },  # DUP
        {"numeroControlePNCP": "07954480000179-1-022747/2025", "valor": 1534.00},  # DUP
        {"numeroControlePNCP": "45276128000110-1-003529/2025", "valor": 580.00},  # DUP
        {"numeroControlePNCP": "63025530000104-1-004689/2025", "valor": 6140.00},  # DUP
        {
            "numeroControlePNCP": "07954480000179-1-022748/2025",
            "valor": 20000.00,
        },  # DUP
    ]

    # Test date
    test_date = datetime(2025, 10, 22)

    # Initialize state manager (with mock storage - won't actually save)
    print("\n" + "=" * 80)
    print("TEST: INCREMENTAL INGESTION WITH STATE MANAGEMENT")
    print("=" * 80)

    # ===== EXECUTION 1: First run (all new) =====
    print("\n" + "-" * 80)
    print("EXECUTION 1 - 08:00 (First time)")
    print("-" * 80)

    state_manager = StateManager()

    # Simulate having no prior state (first execution)
    new_records_1, stats_1 = state_manager.filter_new_records(
        source="pncp",
        date=test_date,
        records=execution_1_data,
        id_field="numeroControlePNCP",
    )

    print("\n📊 Results:")
    print(f"  Input records:       {stats_1['total_input']}")
    print(f"  New records:         {stats_1['new_records']}")
    print(f"  Already processed:   {stats_1['already_processed']}")
    print(f"  Filter rate:         {stats_1['filter_rate']}%")

    assert stats_1["new_records"] == 3, "Expected all 3 records to be new"
    assert stats_1["already_processed"] == 0, "Expected no duplicates"

    # Update state
    new_ids_1 = [
        r["numeroControlePNCP"] for r in new_records_1 if r.get("numeroControlePNCP")
    ]
    state_manager.update_state(
        source="pncp",
        date=test_date,
        new_ids=new_ids_1,
        execution_metadata={"execution_time": "08:00", **stats_1},
    )

    print(f"\n✅ State updated: {len(new_ids_1)} IDs added")
    print(
        f"   Total processed so far: {len(state_manager.get_processed_ids('pncp', test_date))}"
    )

    # ===== EXECUTION 2: Second run (mixed) =====
    print("\n" + "-" * 80)
    print("EXECUTION 2 - 12:00 (4 hours later)")
    print("-" * 80)

    new_records_2, stats_2 = state_manager.filter_new_records(
        source="pncp",
        date=test_date,
        records=execution_2_data,
        id_field="numeroControlePNCP",
    )

    print("\n📊 Results:")
    print(f"  Input records:       {stats_2['total_input']}")
    print(f"  New records:         {stats_2['new_records']}")
    print(f"  Already processed:   {stats_2['already_processed']}")
    print(f"  Filter rate:         {stats_2['filter_rate']}%")

    assert stats_2["new_records"] == 2, "Expected 2 new records"
    assert stats_2["already_processed"] == 3, "Expected 3 duplicates"

    # Update state
    new_ids_2 = [
        r["numeroControlePNCP"] for r in new_records_2 if r.get("numeroControlePNCP")
    ]
    state_manager.update_state(
        source="pncp",
        date=test_date,
        new_ids=new_ids_2,
        execution_metadata={"execution_time": "12:00", **stats_2},
    )

    print(f"\n✅ State updated: {len(new_ids_2)} IDs added")
    print(
        f"   Total processed so far: {len(state_manager.get_processed_ids('pncp', test_date))}"
    )

    # ===== EXECUTION 3: Third run (all duplicates) =====
    print("\n" + "-" * 80)
    print("EXECUTION 3 - 16:00 (4 hours later)")
    print("-" * 80)

    new_records_3, stats_3 = state_manager.filter_new_records(
        source="pncp",
        date=test_date,
        records=execution_3_data,
        id_field="numeroControlePNCP",
    )

    print("\n📊 Results:")
    print(f"  Input records:       {stats_3['total_input']}")
    print(f"  New records:         {stats_3['new_records']}")
    print(f"  Already processed:   {stats_3['already_processed']}")
    print(f"  Filter rate:         {stats_3['filter_rate']}%")

    assert stats_3["new_records"] == 0, "Expected no new records"
    assert stats_3["already_processed"] == 5, "Expected all 5 to be duplicates"

    print("\n⚠️  No new records - all were duplicates (no Bronze file created)")
    print(
        f"   Total processed so far: {len(state_manager.get_processed_ids('pncp', test_date))}"
    )

    # ===== SUMMARY =====
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    summary = state_manager.get_state_summary("pncp", test_date)

    print(f"\nDate:                    {summary['date']}")
    print(f"Total processed IDs:     {summary['total_processed']}")
    print(f"Total executions:        {summary['total_executions']}")
    print(f"Total new across execs:  {summary['total_new_across_executions']}")
    print(f"First execution:         {summary['first_execution']}")
    print(f"Last execution:          {summary['last_execution']}")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)

    # Show what Bronze files would have been created
    print("\n📁 Bronze Files Created:")
    print("   Execution 1 (08:00): data_080000.json (3 records)")
    print("   Execution 2 (12:00): data_120000.json (2 records)")
    print("   Execution 3 (16:00): [NO FILE] (0 new records)")

    print("\n📄 State File:")
    print("   pncp/_state/year=2025/month=10/day=22/state_20251022.json")
    print(f"   Contains: {summary['total_processed']} processed IDs")


if __name__ == "__main__":
    try:
        test_incremental_ingestion()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise
