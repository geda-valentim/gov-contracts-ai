#!/usr/bin/env python3
"""
Consolidate Bronze Layer - Merge multiple Parquet files and remove duplicates.

This script:
1. Reads all Parquet files for a specific day
2. Combines them into a single DataFrame
3. Removes duplicates by numeroControlePNCP
4. Saves back as a single Parquet file
5. Deletes the old files

Usage:
    python scripts/consolidate_bronze_day.py --date 2025-10-23
    python scripts/consolidate_bronze_day.py --date 2025-10-23 --dry-run
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.minio_client import MinIOClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def consolidate_bronze_day(target_date: datetime, dry_run: bool = False):
    """
    Consolidate all Parquet files for a specific day into one deduplicated file.

    Args:
        target_date: Target date to consolidate
        dry_run: If True, only show what would be done without making changes
    """
    minio_client = MinIOClient()
    bucket = minio_client.BUCKET_BRONZE

    # Build partition prefix
    year = target_date.year
    month = target_date.month
    day = target_date.day
    prefix = f"pncp/year={year}/month={month:02d}/day={day:02d}/"

    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Consolidating {target_date.date()}")
    logger.info(f"Prefix: {prefix}")

    # List all Parquet files
    objects = minio_client.list_objects(bucket, prefix=prefix)
    parquet_files = [obj for obj in objects if obj["Key"].endswith(".parquet")]

    if not parquet_files:
        logger.warning(f"No Parquet files found for {target_date.date()}")
        return

    logger.info(f"Found {len(parquet_files)} Parquet file(s)")
    for obj in parquet_files:
        size_mb = obj["Size"] / (1024 * 1024)
        logger.info(f"  - {obj['Key']} ({size_mb:.2f} MB)")

    # If only one file, check if it has duplicates
    if len(parquet_files) == 1:
        logger.info("Only 1 file found, checking for duplicates...")
        df = minio_client.read_parquet_from_s3(bucket, parquet_files[0]["Key"])

        total_before = len(df)
        if "numeroControlePNCP" in df.columns:
            df_dedup = df.drop_duplicates(subset=["numeroControlePNCP"], keep="first")
            total_after = len(df_dedup)
            duplicates = total_before - total_after

            if duplicates == 0:
                logger.info("✅ No duplicates found, file is already clean!")
                return

            logger.info(f"📊 Found {duplicates} duplicates ({total_before} → {total_after} records)")

            if not dry_run:
                # Save deduplicated version
                logger.info("Saving deduplicated version...")
                new_filename = f"pncp_{year}{month:02d}{day:02d}_consolidated.parquet"
                new_key = f"{prefix}{new_filename}"

                # Upload deduplicated file
                minio_client.upload_to_bronze(
                    data=df_dedup,
                    source="pncp",
                    date=target_date,
                    filename=new_filename,
                    format="parquet"
                )
                logger.info(f"✅ Uploaded: {new_key} ({len(df_dedup)} records)")

                # Delete old file
                minio_client.delete_object(bucket, parquet_files[0]["Key"])
                logger.info(f"🗑️  Deleted: {parquet_files[0]['Key']}")

                logger.info(f"✅ Consolidation complete: {duplicates} duplicates removed")
        else:
            logger.warning("Column 'numeroControlePNCP' not found, cannot deduplicate")
        return

    # Multiple files - merge them
    logger.info(f"Reading {len(parquet_files)} files...")
    dataframes = []

    for i, obj in enumerate(parquet_files, 1):
        logger.info(f"Reading file {i}/{len(parquet_files)}: {obj['Key']}")
        df = minio_client.read_parquet_from_s3(bucket, obj["Key"])
        dataframes.append(df)

    # Combine all DataFrames
    logger.info("Combining DataFrames...")
    combined_df = pd.concat(dataframes, ignore_index=True)
    total_before = len(combined_df)

    logger.info(f"Total records before deduplication: {total_before:,}")

    # Deduplicate
    if "numeroControlePNCP" in combined_df.columns:
        combined_df = combined_df.drop_duplicates(
            subset=["numeroControlePNCP"], keep="first"
        )
        total_after = len(combined_df)
        duplicates_removed = total_before - total_after

        logger.info(f"Total records after deduplication: {total_after:,}")
        logger.info(f"Duplicates removed: {duplicates_removed:,}")
    else:
        logger.warning("Column 'numeroControlePNCP' not found, skipping deduplication")
        total_after = total_before
        duplicates_removed = 0

    if dry_run:
        logger.info("[DRY-RUN] Would save consolidated file and delete old files")
        return

    # Save consolidated file
    new_filename = f"pncp_{year}{month:02d}{day:02d}_consolidated.parquet"
    new_key = f"{prefix}{new_filename}"

    logger.info(f"Saving consolidated file: {new_key}")
    minio_client.upload_to_bronze(
        data=combined_df,
        source="pncp",
        date=target_date,
        filename=new_filename,
        format="parquet"
    )
    logger.info(f"✅ Uploaded: {new_key} ({total_after:,} records)")

    # Delete old files
    logger.info(f"Deleting {len(parquet_files)} old files...")
    for obj in parquet_files:
        minio_client.delete_object(bucket, obj["Key"])
        logger.info(f"🗑️  Deleted: {obj['Key']}")

    logger.info("=" * 70)
    logger.info("✅ CONSOLIDATION COMPLETE")
    logger.info(f"Files merged: {len(parquet_files)} → 1")
    logger.info(f"Records: {total_before:,} → {total_after:,}")
    logger.info(f"Duplicates removed: {duplicates_removed:,}")
    logger.info(f"Final file: {new_key}")
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate Bronze layer Parquet files and remove duplicates"
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Parse date
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
        sys.exit(1)

    # Run consolidation
    consolidate_bronze_day(target_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
