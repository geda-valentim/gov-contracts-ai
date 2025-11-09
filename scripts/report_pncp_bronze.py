#!/usr/bin/env python3
"""
PNCP Bronze Layer Report Generator

Generates statistics about collected procurement records (licitações) in the Bronze layer.
Shows unique records collected by year, month, and day.

Features:
- Reads Parquet files from MinIO Bronze layer
- Counts unique licitações (by sequencialCompra)
- Groups by year, month, day
- Displays summary statistics

Usage:
    python scripts/report_pncp_bronze.py
    python scripts/report_pncp_bronze.py --start-date 2025-10-01
    python scripts/report_pncp_bronze.py --start-date 2025-10-01 --end-date 2025-10-31
    python scripts/report_pncp_bronze.py --detailed  # Show daily breakdown
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file BEFORE importing backend modules
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.warning(f".env file not found at {dotenv_path}")

from backend.app.core.storage_client import get_storage_client


def get_parquet_files_in_period(
    storage,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[str]:
    """
    List all Parquet files in the Bronze PNCP layer within date range.

    Args:
        storage: Storage client instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of S3 keys for Parquet files
    """
    # If no dates provided, get last 30 days
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    logger.info(
        f"Scanning for Parquet files from {start_date.date()} to {end_date.date()}"
    )

    parquet_files = []
    bucket = storage.BUCKET_BRONZE

    # Iterate through date range
    current_date = start_date
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day

        # Build prefix for this date
        prefix = f"pncp/year={year}/month={month:02d}/day={day:02d}/"

        # List objects with this prefix
        try:
            objects = storage.list_objects(bucket, prefix=prefix)
            parquet_objects = [
                obj["Key"] for obj in objects if obj["Key"].endswith(".parquet")
            ]
            parquet_files.extend(parquet_objects)
            if parquet_objects:
                logger.info(
                    f"  {current_date.date()}: Found {len(parquet_objects)} file(s)"
                )
        except Exception as e:
            logger.debug(f"  {current_date.date()}: No files (error: {e})")

        current_date += timedelta(days=1)

    logger.info(f"Total Parquet files found: {len(parquet_files)}")
    return parquet_files


def read_parquet_from_s3(storage, bucket: str, key: str) -> pd.DataFrame:
    """
    Read a Parquet file from S3/MinIO into a DataFrame.

    Args:
        storage: Storage client instance
        bucket: Bucket name
        key: Object key

    Returns:
        DataFrame with the data
    """
    try:
        # Use the storage client's read_parquet_from_s3 method
        return storage.read_parquet_from_s3(bucket, key)
    except Exception as e:
        logger.error(f"Error reading {key}: {e}")
        return pd.DataFrame()


def generate_report(
    storage,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    detailed: bool = False,
) -> Dict:
    """
    Generate statistics report for PNCP Bronze layer.

    Args:
        storage: Storage client instance
        start_date: Start date for analysis
        end_date: End date for analysis
        detailed: If True, show daily breakdown

    Returns:
        Dictionary with report data
    """
    # Get list of Parquet files
    parquet_files = get_parquet_files_in_period(storage, start_date, end_date)

    if not parquet_files:
        logger.warning("No Parquet files found in the specified period")
        return {
            "total_files": 0,
            "total_records": 0,
            "unique_licitacoes": 0,
            "by_year": {},
            "by_month": {},
            "by_day": {},
            "id_column": None,
        }

    # Read all files and combine
    logger.info(f"Reading {len(parquet_files)} Parquet file(s)...")
    all_data = []
    bucket = storage.BUCKET_BRONZE

    for i, key in enumerate(parquet_files, 1):
        logger.info(f"  Reading file {i}/{len(parquet_files)}: {key}")
        df = read_parquet_from_s3(storage, bucket, key)
        if not df.empty:
            all_data.append(df)

    if not all_data:
        logger.warning("No data found in Parquet files")
        return {
            "total_files": len(parquet_files),
            "total_records": 0,
            "unique_licitacoes": 0,
            "by_year": {},
            "by_month": {},
            "by_day": {},
            "id_column": None,
        }

    # Combine all DataFrames
    logger.info("Combining data and calculating statistics...")
    combined_df = pd.concat(all_data, ignore_index=True)

    # Extract date components from dataInicioVigencia or dataPublicacaoPncp
    date_column = None
    for col in ["dataInicioVigencia", "dataPublicacaoPncp", "ingestion_timestamp"]:
        if col in combined_df.columns:
            date_column = col
            break

    if date_column:
        # Convert to datetime
        combined_df["date"] = pd.to_datetime(combined_df[date_column], errors="coerce")
        combined_df["year"] = combined_df["date"].dt.year
        combined_df["month"] = combined_df["date"].dt.month
        combined_df["day"] = combined_df["date"].dt.day
        combined_df["year_month"] = combined_df["date"].dt.to_period("M").astype(str)
        combined_df["date_only"] = combined_df["date"].dt.date
    else:
        logger.warning("No date column found, using ingestion timestamp if available")
        combined_df["year"] = None
        combined_df["month"] = None
        combined_df["day"] = None
        combined_df["year_month"] = None
        combined_df["date_only"] = None

    # Calculate statistics
    total_records = len(combined_df)

    # Unique licitações by numeroControlePNCP (globally unique ID)
    # NOTE: numeroControlePNCP = {CNPJ}-{unidade}-{sequencial}/{ano}
    # This is the ONLY globally unique identifier in PNCP API
    # sequencialCompra is NOT unique (each orgao has its own sequence)
    if "numeroControlePNCP" in combined_df.columns:
        unique_licitacoes = combined_df["numeroControlePNCP"].nunique()
        id_column = "numeroControlePNCP"
    elif "sequencialCompra" in combined_df.columns:
        # Fallback: combine CNPJ + sequencialCompra for uniqueness
        logger.warning(
            "Using sequencialCompra (not globally unique). "
            "Combining with CNPJ for accurate count."
        )
        combined_df["cnpj"] = combined_df["orgaoEntidade"].apply(
            lambda x: x.get("cnpj") if isinstance(x, dict) else None
        )
        combined_df["licitacao_id"] = (
            combined_df["cnpj"].astype(str)
            + "-"
            + combined_df["sequencialCompra"].astype(str)
        )
        unique_licitacoes = combined_df["licitacao_id"].nunique()
        id_column = "licitacao_id"
    else:
        unique_licitacoes = total_records
        id_column = None
        logger.warning("No ID column found, using total records as unique count")

    # Group by year
    by_year = {}
    if "year" in combined_df.columns and combined_df["year"].notna().any():
        for year, group in combined_df.groupby("year"):
            if pd.notna(year):
                unique_count = group[id_column].nunique() if id_column else len(group)
                by_year[int(year)] = {
                    "total_records": len(group),
                    "unique_licitacoes": unique_count,
                }

    # Group by month
    by_month = {}
    if "year_month" in combined_df.columns and combined_df["year_month"].notna().any():
        for year_month, group in combined_df.groupby("year_month"):
            if pd.notna(year_month):
                unique_count = group[id_column].nunique() if id_column else len(group)
                by_month[year_month] = {
                    "total_records": len(group),
                    "unique_licitacoes": unique_count,
                }

    # Group by day (only if detailed requested)
    by_day = {}
    if detailed and "date_only" in combined_df.columns:
        for date, group in combined_df.groupby("date_only"):
            if pd.notna(date):
                unique_count = group[id_column].nunique() if id_column else len(group)
                by_day[str(date)] = {
                    "total_records": len(group),
                    "unique_licitacoes": unique_count,
                }

    return {
        "total_files": len(parquet_files),
        "total_records": total_records,
        "unique_licitacoes": unique_licitacoes,
        "by_year": by_year,
        "by_month": by_month,
        "by_day": by_day,
        "id_column": id_column,
    }


def print_report(report: Dict):
    """
    Print formatted report to console.

    Args:
        report: Report dictionary from generate_report()
    """
    print("\n" + "=" * 80)
    print("📊 PNCP Bronze Layer - Relatório de Licitações Coletadas")
    print("=" * 80)
    print()

    # Overall statistics
    print("📈 Estatísticas Gerais:")
    print(f"   Total de arquivos Parquet: {report['total_files']:,}")
    print(f"   Total de registros: {report['total_records']:,}")

    if report.get("id_column"):
        print(
            f"   Licitações únicas ({report['id_column']}): {report['unique_licitacoes']:,}"
        )
    else:
        print(f"   Licitações únicas: {report['unique_licitacoes']:,}")

    # Add note about records vs licitações
    if report['total_records'] > report['unique_licitacoes']:
        ratio = report['total_records'] / report['unique_licitacoes']
        print(f"   ℹ️  Média de {ratio:.1f} registros por licitação (itens/modalidades)")
    print()

    # By year
    if report["by_year"]:
        print("📅 Por Ano:")
        for year in sorted(report["by_year"].keys()):
            data = report["by_year"][year]
            print(
                f"   {year}: {data['unique_licitacoes']:,} licitações únicas "
                f"({data['total_records']:,} registros)"
            )
        print()

    # By month
    if report["by_month"]:
        print("📆 Por Mês:")
        for month in sorted(report["by_month"].keys()):
            data = report["by_month"][month]
            print(
                f"   {month}: {data['unique_licitacoes']:,} licitações únicas "
                f"({data['total_records']:,} registros)"
            )
        print()

    # By day (only if detailed)
    if report["by_day"]:
        print("📋 Por Dia:")
        for day in sorted(report["by_day"].keys()):
            data = report["by_day"][day]
            print(
                f"   {day}: {data['unique_licitacoes']:,} licitações únicas "
                f"({data['total_records']:,} registros)"
            )
        print()

    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate PNCP Bronze layer statistics report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Last 30 days (default)
  python scripts/report_pncp_bronze.py

  # Specific date range
  python scripts/report_pncp_bronze.py --start-date 2025-10-01 --end-date 2025-10-31

  # Show daily breakdown
  python scripts/report_pncp_bronze.py --detailed

  # All data from specific date
  python scripts/report_pncp_bronze.py --start-date 2025-01-01
        """,
    )

    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD), default: 30 days ago",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD), default: today",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed daily breakdown",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    # Check if required services are available before starting
    from backend.app.core.health_checks import check_services_or_exit
    check_services_or_exit(["MinIO"], script_name="PNCP Bronze Report")

    # Parse dates
    start_date = None
    end_date = None

    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid start date format: {args.start_date}")
            sys.exit(1)

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid end date format: {args.end_date}")
            sys.exit(1)

    # Get storage client
    logger.info("Initializing storage client...")
    storage = get_storage_client()

    # Generate report
    report = generate_report(
        storage,
        start_date=start_date,
        end_date=end_date,
        detailed=args.detailed,
    )

    # Print report
    print_report(report)


if __name__ == "__main__":
    main()
