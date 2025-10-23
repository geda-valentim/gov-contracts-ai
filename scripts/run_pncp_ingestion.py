#!/usr/bin/env python3
"""
Standalone PNCP Ingestion Script - No Airflow Required.

This script runs the complete ingestion pipeline using standalone services.
Can be executed directly without any Airflow dependencies.

Usage:
    # Hourly ingestion (last 20 pages)
    python scripts/run_pncp_ingestion.py --mode hourly

    # Daily ingestion (complete day)
    python scripts/run_pncp_ingestion.py --mode daily

    # Custom date range
    python scripts/run_pncp_ingestion.py --mode custom --date 20241022 --pages 5

    # Test with fewer modalidades
    python scripts/run_pncp_ingestion.py --mode hourly --modalidades 3

Examples:
    # Quick test with 3 modalidades and 5 pages
    python scripts/run_pncp_ingestion.py --mode custom --date 20241022 --pages 5 --modalidades 3

    # Full hourly ingestion
    python scripts/run_pncp_ingestion.py --mode hourly

    # Backfill historical data
    python scripts/run_pncp_ingestion.py --mode backfill --start-date 20241001 --end-date 20241031
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services import (
    PNCPIngestionService,
    DataTransformationService,
)
from backend.app.core.storage_client import get_storage_client
from backend.app.domains.pncp import ModalidadeContratacao

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    mode: str,
    date: str = None,
    start_date: str = None,
    end_date: str = None,
    num_pages: int = None,
    num_modalidades: int = None,
) -> dict:
    """
    Run complete ingestion pipeline.

    Args:
        mode: Ingestion mode (hourly, daily, backfill, custom)
        date: Date for custom mode (YYYYMMDD)
        start_date: Start date for backfill (YYYYMMDD)
        end_date: End date for backfill (YYYYMMDD)
        num_pages: Number of pages per modalidade (optional)
        num_modalidades: Number of modalidades to use (1-13)

    Returns:
        Dict with pipeline results
    """
    logger.info("=" * 80)
    logger.info("PNCP INGESTION PIPELINE - STANDALONE MODE")
    logger.info("=" * 80)
    logger.info(f"Mode: {mode}")
    logger.info(f"Date: {date or 'today'}")
    logger.info(f"Pages: {num_pages or 'all'}")
    logger.info(f"Modalidades: {num_modalidades or 'all (13)'}")
    logger.info("=" * 80)

    # Select modalidades
    all_modalidades = ModalidadeContratacao.get_all()
    if num_modalidades and num_modalidades < len(all_modalidades):
        modalidades = all_modalidades[:num_modalidades]
        logger.info(f"Using {len(modalidades)} modalidades for testing")
    else:
        modalidades = all_modalidades
        logger.info(f"Using all {len(modalidades)} modalidades")

    # STEP 1: FETCH DATA
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: FETCHING DATA FROM PNCP API")
    logger.info("=" * 80)

    ingestion_service = PNCPIngestionService()

    if mode == "hourly":
        execution_date = datetime.strptime(date, "%Y%m%d") if date else datetime.now()
        result = ingestion_service.fetch_hourly_incremental(
            execution_date=execution_date,
            num_pages=num_pages or 20,
            modalidades=modalidades,
        )

    elif mode == "daily":
        execution_date = datetime.strptime(date, "%Y%m%d") if date else datetime.now()
        result = ingestion_service.fetch_daily_complete(
            execution_date=execution_date,
            modalidades=modalidades,
        )

    elif mode == "backfill":
        if not start_date or not end_date:
            raise ValueError("Backfill mode requires --start-date and --end-date")
        result = ingestion_service.fetch_backfill(
            start_date=datetime.strptime(start_date, "%Y%m%d"),
            end_date=datetime.strptime(end_date, "%Y%m%d"),
            modalidades=modalidades,
        )

    else:  # custom
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        result = ingestion_service.fetch_by_date_range(
            data_inicial=date,
            data_final=date,
            modalidades=modalidades,
            num_pages=num_pages,
        )

    raw_data = result["data"]
    metadata = result["metadata"]

    logger.info(f"✅ Fetched {len(raw_data)} records")
    logger.info("Modalidade breakdown:")
    for modalidade, count in metadata["modalidade_stats"].items():
        logger.info(f"  {modalidade}: {count}")

    if not raw_data:
        logger.warning("No data fetched, stopping pipeline")
        return {"success": False, "reason": "no_data"}

    # STEP 2: TRANSFORM AND VALIDATE
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: TRANSFORMING AND VALIDATING DATA")
    logger.info("=" * 80)

    transformation_service = DataTransformationService()

    # Validate
    validation_report = transformation_service.validate_records(raw_data)
    logger.info(
        f"Validation: {validation_report['valid_records']}/{validation_report['total_records']} valid"
    )
    if validation_report["validation_errors"]:
        logger.warning(
            f"Found {len(validation_report['validation_errors'])} validation errors"
        )

    # Transform to DataFrame
    df = transformation_service.to_dataframe(raw_data, deduplicate=True)
    logger.info(f"DataFrame created: {df.shape}")

    # Add metadata
    df = transformation_service.add_metadata_columns(df, metadata)

    logger.info(f"✅ Transformed {len(df)} records")

    # STEP 3: UPLOAD TO BRONZE
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: UPLOADING TO BRONZE LAYER")
    logger.info("=" * 80)

    storage = get_storage_client()

    # Convert DataFrame back to dict for upload
    data_to_upload = df.to_dict(orient="records")

    # Use current time for unique filenames, but preserve the logical date for partitioning
    # Parse the logical date but use now() for timestamp to avoid overwrites
    if date:
        logical_date = datetime.strptime(date, "%Y%m%d")
        # Replace time component with current time for uniqueness
        upload_date = logical_date.replace(
            hour=datetime.now().hour,
            minute=datetime.now().minute,
            second=datetime.now().second,
            microsecond=datetime.now().microsecond,
        )
    else:
        upload_date = datetime.now()

    s3_key = storage.upload_to_bronze(
        data=data_to_upload,
        source="pncp",
        date=upload_date,
    )

    upload_result = {
        "uploaded": True,
        "s3_key": s3_key,
        "bucket": storage.BUCKET_BRONZE,
        "record_count": len(data_to_upload),
    }

    logger.info(
        f"✅ Uploaded to: s3://{upload_result['bucket']}/{upload_result['s3_key']}"
    )
    logger.info(f"Records uploaded: {upload_result['record_count']}")

    # STEP 4: VALIDATE INGESTION
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4: VALIDATING INGESTION")
    logger.info("=" * 80)

    is_valid = (
        upload_result.get("uploaded") and upload_result.get("record_count", 0) > 0
    )

    if is_valid:
        logger.info("✅ Ingestion validation passed")
    else:
        logger.error("❌ Ingestion validation failed")

    # FINAL SUMMARY
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"Total records fetched: {metadata['record_count']}")
    logger.info(f"Total records uploaded: {upload_result['record_count']}")
    logger.info(
        f"S3 location: s3://{upload_result['bucket']}/{upload_result['s3_key']}"
    )
    logger.info(f"Date range: {metadata['data_inicial']} - {metadata['data_final']}")
    logger.info("=" * 80)

    return {
        "success": True,
        "metadata": metadata,
        "validation": validation_report,
        "upload": upload_result,
        "is_valid": is_valid,
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Standalone PNCP Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--mode",
        choices=["hourly", "daily", "backfill", "custom"],
        default="custom",
        help="Ingestion mode",
    )

    parser.add_argument(
        "--date",
        help="Date in YYYYMMDD format (defaults to today)",
    )

    parser.add_argument(
        "--start-date",
        help="Start date for backfill (YYYYMMDD)",
    )

    parser.add_argument(
        "--end-date",
        help="End date for backfill (YYYYMMDD)",
    )

    parser.add_argument(
        "--pages",
        type=int,
        help="Number of pages per modalidade (for testing)",
    )

    parser.add_argument(
        "--modalidades",
        type=int,
        choices=range(1, 14),
        metavar="[1-13]",
        help="Number of modalidades to use (1-13, defaults to all)",
    )

    args = parser.parse_args()

    try:
        result = run_ingestion_pipeline(
            mode=args.mode,
            date=args.date,
            start_date=args.start_date,
            end_date=args.end_date,
            num_pages=args.pages,
            num_modalidades=args.modalidades,
        )

        if result["success"]:
            logger.info("Pipeline completed successfully! ✅")
            sys.exit(0)
        else:
            logger.error(f"Pipeline failed: {result.get('reason')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
