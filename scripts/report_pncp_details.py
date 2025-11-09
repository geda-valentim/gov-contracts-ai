#!/usr/bin/env python3
"""
PNCP Details Report Script.

Generates statistical reports from PNCP details data (itens + arquivos) in Bronze layer.

Usage:
    # Report for specific date
    python scripts/report_pncp_details.py --date 20251022

    # Report for date range
    python scripts/report_pncp_details.py --start-date 20251001 --end-date 20251031

    # Detailed breakdown
    python scripts/report_pncp_details.py --date 20251022 --detailed

    # Export to JSON
    python scripts/report_pncp_details.py --date 20251022 --output report.json
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from backend.app.core.storage_client import get_storage_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def read_details_for_date(storage, date: datetime) -> list:
    """
    Read details data from Bronze for a specific date.

    Supports both:
    - Legacy format: details.parquet (single file)
    - Chunked format: chunk_0001.parquet, chunk_0002.parquet, etc.
    """
    import pandas as pd

    year = date.year
    month = date.month
    day = date.day

    partition_prefix = f"pncp_details/year={year}/month={month:02d}/day={day:02d}/"

    try:
        # List all Parquet files in partition
        objects = storage.list_objects(
            bucket=storage.BUCKET_BRONZE,
            prefix=partition_prefix,
        )

        # Filter for Parquet files only
        parquet_files = [
            obj["Key"] for obj in objects
            if obj["Key"].endswith(".parquet")
        ]

        if not parquet_files:
            logger.debug(f"No parquet files found for {date.date()}")
            return []

        logger.debug(f"Found {len(parquet_files)} parquet file(s) for {date.date()}")

        # Read all Parquet files and concatenate
        dfs = []
        for file_key in parquet_files:
            df = storage._client.read_parquet_from_s3(
                bucket_name=storage.BUCKET_BRONZE,
                object_name=file_key
            )
            dfs.append(df)

        # Concatenate all DataFrames
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)

            # Deduplicate by numeroControlePNCP (chunks may overlap in edge cases)
            if "numeroControlePNCP" in combined_df.columns:
                before = len(combined_df)
                combined_df = combined_df.drop_duplicates(
                    subset=["numeroControlePNCP"], keep="first"
                )
                after = len(combined_df)
                if before != after:
                    logger.debug(f"Removed {before - after} duplicates")

            # Convert to list of dicts
            data = combined_df.to_dict(orient="records")

            logger.debug(f"Loaded {len(data)} contratacoes from {date.date()}")
            return data
        else:
            return []

    except Exception as e:
        logger.debug(f"Error reading data for {date.date()}: {e}")
        return []


def generate_report(
    details_data: list, start_date: datetime, end_date: datetime, detailed: bool = False
) -> dict:
    """Generate statistical report from details data."""
    report = {
        "period": {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "days": (end_date - start_date).days + 1,
        },
        "summary": {
            "total_contratacoes": 0,
            "total_itens": 0,
            "total_arquivos": 0,
            "avg_itens_per_contratacao": 0,
            "avg_arquivos_per_contratacao": 0,
        },
        "itens_by_category": defaultdict(int),
        "itens_by_status": defaultdict(int),
        "arquivos_by_type": defaultdict(int),
        "daily_breakdown": [] if detailed else None,
    }

    daily_stats = defaultdict(lambda: {"contratacoes": 0, "itens": 0, "arquivos": 0})

    # Process all data
    for contratacao in details_data:
        report["summary"]["total_contratacoes"] += 1

        # Extract date for daily breakdown
        data_pub = contratacao.get("dataPublicacaoPncp", "")
        if data_pub:
            try:
                date_key = data_pub[:10]  # YYYY-MM-DD
                daily_stats[date_key]["contratacoes"] += 1
            except Exception:
                pass

        # Process itens
        itens = contratacao.get("itens", [])
        report["summary"]["total_itens"] += len(itens)

        if detailed and data_pub:
            daily_stats[date_key]["itens"] += len(itens)

        for item in itens:
            # Category
            cat_nome = item.get("itemCategoriaNome", "Unknown")
            report["itens_by_category"][cat_nome] += 1

            # Status
            status_nome = item.get("situacaoCompraItemNome", "Unknown")
            report["itens_by_status"][status_nome] += 1

        # Process arquivos
        arquivos = contratacao.get("arquivos", [])
        report["summary"]["total_arquivos"] += len(arquivos)

        if detailed and data_pub:
            daily_stats[date_key]["arquivos"] += len(arquivos)

        for arquivo in arquivos:
            # Document type
            tipo_nome = arquivo.get("tipoDocumentoNome") or arquivo.get(
                "tipoDocumentoDescricao", "Unknown"
            )
            report["arquivos_by_type"][tipo_nome] += 1

    # Calculate averages
    if report["summary"]["total_contratacoes"] > 0:
        report["summary"]["avg_itens_per_contratacao"] = round(
            report["summary"]["total_itens"] / report["summary"]["total_contratacoes"],
            2,
        )
        report["summary"]["avg_arquivos_per_contratacao"] = round(
            report["summary"]["total_arquivos"]
            / report["summary"]["total_contratacoes"],
            2,
        )

    # Convert defaultdicts to regular dicts
    report["itens_by_category"] = dict(report["itens_by_category"])
    report["itens_by_status"] = dict(report["itens_by_status"])
    report["arquivos_by_type"] = dict(report["arquivos_by_type"])

    # Sort by count (descending)
    report["itens_by_category"] = dict(
        sorted(report["itens_by_category"].items(), key=lambda x: x[1], reverse=True)
    )
    report["itens_by_status"] = dict(
        sorted(report["itens_by_status"].items(), key=lambda x: x[1], reverse=True)
    )
    report["arquivos_by_type"] = dict(
        sorted(report["arquivos_by_type"].items(), key=lambda x: x[1], reverse=True)
    )

    # Daily breakdown
    if detailed:
        report["daily_breakdown"] = [
            {"date": date_key, **stats}
            for date_key, stats in sorted(daily_stats.items())
        ]

    return report


def print_report(report: dict):
    """Print report to console in human-readable format."""
    print("\n" + "=" * 80)
    print("PNCP DETAILS REPORT")
    print("=" * 80)

    # Period
    print(f"\n📅 Period: {report['period']['start_date']} to {report['period']['end_date']}")
    print(f"   Duration: {report['period']['days']} days")

    # Summary
    summary = report["summary"]
    print("\n📊 Summary:")
    print(f"   Total contratacoes: {summary['total_contratacoes']:,}")
    print(f"   Total itens: {summary['total_itens']:,}")
    print(f"   Total arquivos: {summary['total_arquivos']:,}")
    print(f"   Avg itens/contratacao: {summary['avg_itens_per_contratacao']}")
    print(f"   Avg arquivos/contratacao: {summary['avg_arquivos_per_contratacao']}")

    # Itens by category
    if report["itens_by_category"]:
        print("\n📦 Itens by Category:")
        for category, count in list(report["itens_by_category"].items())[:10]:
            percentage = (count / summary["total_itens"] * 100) if summary["total_itens"] > 0 else 0
            print(f"   {category:<40} {count:>8,} ({percentage:>5.1f}%)")

    # Itens by status
    if report["itens_by_status"]:
        print("\n📋 Itens by Status:")
        for status, count in report["itens_by_status"].items():
            percentage = (count / summary["total_itens"] * 100) if summary["total_itens"] > 0 else 0
            print(f"   {status:<40} {count:>8,} ({percentage:>5.1f}%)")

    # Arquivos by type
    if report["arquivos_by_type"]:
        print("\n📄 Arquivos by Type:")
        for tipo, count in list(report["arquivos_by_type"].items())[:10]:
            percentage = (count / summary["total_arquivos"] * 100) if summary["total_arquivos"] > 0 else 0
            print(f"   {tipo:<40} {count:>8,} ({percentage:>5.1f}%)")

    # Daily breakdown
    if report["daily_breakdown"]:
        print("\n📆 Daily Breakdown:")
        print(f"   {'Date':<12} {'Contratacoes':>15} {'Itens':>10} {'Arquivos':>10}")
        print(f"   {'-' * 12} {'-' * 15} {'-' * 10} {'-' * 10}")
        for day in report["daily_breakdown"]:
            print(
                f"   {day['date']:<12} {day['contratacoes']:>15,} "
                f"{day['itens']:>10,} {day['arquivos']:>10,}"
            )

    print("\n" + "=" * 80)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="PNCP Details Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--date", help="Specific date (YYYYMMDD format)")
    parser.add_argument("--start-date", help="Start date (YYYYMMDD format)")
    parser.add_argument("--end-date", help="End date (YYYYMMDD format)")
    parser.add_argument(
        "--detailed", action="store_true", help="Include daily breakdown"
    )
    parser.add_argument("--output", help="Output file path (JSON format)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if required services are available before starting
    from backend.app.core.health_checks import check_services_or_exit
    check_services_or_exit(["MinIO"], script_name="PNCP Details Report")

    # Parse dates
    try:
        if args.date:
            start_date = datetime.strptime(args.date, "%Y%m%d")
            end_date = start_date
        elif args.start_date and args.end_date:
            start_date = datetime.strptime(args.start_date, "%Y%m%d")
            end_date = datetime.strptime(args.end_date, "%Y%m%d")
        else:
            # Default: last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=6)
            logger.info(f"No dates specified, using last 7 days: {start_date.date()} to {end_date.date()}")

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return 1

    # Validate date range
    if start_date > end_date:
        logger.error("Start date must be before or equal to end date")
        return 1

    # Initialize storage
    storage = get_storage_client()

    # Read data for date range
    logger.info(f"Reading data from {start_date.date()} to {end_date.date()}...")
    all_details = []

    current_date = start_date
    while current_date <= end_date:
        details = read_details_for_date(storage, current_date)
        all_details.extend(details)
        current_date += timedelta(days=1)

    logger.info(f"Loaded {len(all_details)} contratacoes total")

    if not all_details:
        logger.warning("⚠️  No data found for the specified period")
        return 0

    # Generate report
    logger.info("Generating report...")
    report = generate_report(all_details, start_date, end_date, detailed=args.detailed)

    # Print to console
    print_report(report)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Report saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
