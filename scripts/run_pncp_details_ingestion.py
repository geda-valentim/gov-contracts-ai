#!/usr/bin/env python3
"""
Standalone PNCP Details Ingestion Script.

Fetches items (itens) and documents (arquivos) for contratacoes from Bronze layer
and saves enriched data with nested structure.

This script can run independently without Airflow.

Usage:
    # Fetch details for specific date
    python scripts/run_pncp_details_ingestion.py --date 20251022

    # Fetch details with limit (testing)
    python scripts/run_pncp_details_ingestion.py --date 20251022 --max-contratacoes 10

    # Specify output format
    python scripts/run_pncp_details_ingestion.py --date 20251022 --format json

Requirements:
    - .env file in project root
    - MinIO/S3 configured with Bronze bucket
    - Contratacoes already ingested for the date
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env
try:
    from dotenv import load_dotenv

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env loading")

# Now import backend modules
from backend.app.core.storage_client import get_storage_client
from backend.app.services import StateManager
from backend.app.services.ingestion.pncp_details import PNCPDetailsIngestionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="PNCP Details Ingestion - Standalone Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch details for specific date
  python scripts/run_pncp_details_ingestion.py --date 20251022

  # Fetch with limit for testing
  python scripts/run_pncp_details_ingestion.py --date 20251022 --max-contratacoes 10

  # Skip state filtering (fetch all)
  python scripts/run_pncp_details_ingestion.py --date 20251022 --no-state-filter
        """,
    )

    parser.add_argument(
        "--date", required=True, help="Date to fetch details for (YYYYMMDD format)"
    )
    parser.add_argument(
        "--max-contratacoes",
        type=int,
        help="Maximum contratacoes to process (for testing, legacy)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Batch size for auto-resume mode (e.g., 100)",
    )
    parser.add_argument(
        "--auto-resume",
        action="store_true",
        help="Enable auto-resume mode (continues from last checkpoint)",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=50,
        help="Save checkpoint every N contratacoes (default: 50)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "parquet"],
        default="parquet",
        help="Output format (default: parquet)",
    )
    parser.add_argument(
        "--no-state-filter",
        action="store_true",
        help="Skip state filtering (fetch all, ignore previous runs)",
    )
    parser.add_argument(
        "--output-file", help="Optional output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("backend").setLevel(logging.DEBUG)

    # Check if required services are available before starting
    from backend.app.core.health_checks import check_services_or_exit
    check_services_or_exit(["PostgreSQL", "Redis", "MinIO"], script_name="PNCP Details Ingestion")

    # Parse date
    try:
        execution_date = datetime.strptime(args.date, "%Y%m%d")
    except ValueError:
        logger.error(f"Invalid date format: {args.date}. Expected YYYYMMDD.")
        return 1

    logger.info("=" * 70)
    logger.info("PNCP DETAILS INGESTION - STANDALONE EXECUTION")
    logger.info("=" * 70)
    logger.info(f"Date: {execution_date.date()}")
    logger.info(f"Mode: {'auto-resume' if args.auto_resume else 'full'}")
    if args.batch_size:
        logger.info(f"Batch size: {args.batch_size}")
    if args.max_contratacoes:
        logger.info(f"Max contratacoes: {args.max_contratacoes} (test limit)")
    logger.info(f"State filtering: {'disabled' if args.no_state_filter else 'enabled'}")
    logger.info(f"Output format: {args.format}")
    logger.info("=" * 70)

    try:
        # Initialize services
        logger.info("Initializing services...")
        service = PNCPDetailsIngestionService()
        storage = get_storage_client()
        state_manager = StateManager()

        # Step 1: Fetch details from API
        logger.info("\n📥 STEP 1: Fetching details from PNCP API...")
        result = service.fetch_details_for_date(
            execution_date=execution_date,
            max_contratacoes=args.max_contratacoes,
            batch_size=args.batch_size,
            auto_resume=args.auto_resume,
            checkpoint_every=args.checkpoint_every,
        )

        enriched_contratacoes = result["data"]
        metadata = result["metadata"]

        logger.info(
            f"✅ Fetched details for {metadata['contratacoes_processed']} contratacoes"
        )
        logger.info(f"   Total itens: {metadata['total_itens']}")
        logger.info(f"   Total arquivos: {metadata['total_arquivos']}")
        logger.info(f"   API calls: {metadata['api_calls']}")
        logger.info(f"   Errors: {metadata['errors']}")

        if not enriched_contratacoes:
            logger.warning("⚠️  No contratacoes found for this date")
            return 0

        # Step 2: State filtering (optional, skipped if auto_resume)
        if not args.no_state_filter and not args.auto_resume:
            logger.info("\n🔍 STEP 2: Filtering with state management...")

            # Filter for itens
            contratacoes_itens, itens_stats = state_manager.filter_new_details(
                source="pncp_details",
                date=execution_date,
                contratacoes=enriched_contratacoes,
                detail_type="itens",
                key_extractor_fn=PNCPDetailsIngestionService.extract_key_from_contratacao,
            )

            # Filter for arquivos
            contratacoes_arquivos, arquivos_stats = state_manager.filter_new_details(
                source="pncp_details",
                date=execution_date,
                contratacoes=enriched_contratacoes,
                detail_type="arquivos",
                key_extractor_fn=PNCPDetailsIngestionService.extract_key_from_contratacao,
            )

            logger.info(
                f"   Itens: {itens_stats['new_records']} new / {itens_stats['total_input']} total "
                f"({itens_stats['filter_rate']:.1f}% filtered)"
            )
            logger.info(
                f"   Arquivos: {arquivos_stats['new_records']} new / {arquivos_stats['total_input']} total "
                f"({arquivos_stats['filter_rate']:.1f}% filtered)"
            )

            if not contratacoes_itens and not contratacoes_arquivos:
                logger.info("✅ All contratacoes already processed (no new data)")
                return 0

            # Update state
            logger.info("\n💾 Updating state files...")

            itens_keys = [
                PNCPDetailsIngestionService.extract_key_from_contratacao(c)
                for c in contratacoes_itens
                if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
            ]
            arquivos_keys = [
                PNCPDetailsIngestionService.extract_key_from_contratacao(c)
                for c in contratacoes_arquivos
                if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
            ]

            if itens_keys:
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="itens",
                    new_keys=itens_keys,
                    execution_metadata={"new_records": len(itens_keys)},
                )
                logger.info(f"   ✅ Itens state updated ({len(itens_keys)} keys)")

            if arquivos_keys:
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="arquivos",
                    new_keys=arquivos_keys,
                    execution_metadata={"new_records": len(arquivos_keys)},
                )
                logger.info(f"   ✅ Arquivos state updated ({len(arquivos_keys)} keys)")

        elif args.auto_resume:
            logger.info("\n⏭️  STEP 2: Updating state after auto-resume processing...")

            # Extract keys for state update
            itens_keys = [
                PNCPDetailsIngestionService.extract_key_from_contratacao(c)
                for c in enriched_contratacoes
                if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
            ]

            arquivos_keys = [
                PNCPDetailsIngestionService.extract_key_from_contratacao(c)
                for c in enriched_contratacoes
                if PNCPDetailsIngestionService.extract_key_from_contratacao(c)
            ]

            if itens_keys:
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="itens",
                    new_keys=itens_keys,
                    execution_metadata={"new_records": len(itens_keys)},
                )
                logger.info(f"   ✅ Itens state updated ({len(itens_keys)} keys)")

            if arquivos_keys:
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="arquivos",
                    new_keys=arquivos_keys,
                    execution_metadata={"new_records": len(arquivos_keys)},
                )
                logger.info(f"   ✅ Arquivos state updated ({len(arquivos_keys)} keys)")
        else:
            logger.info("\n⏭️  STEP 2: Skipping state filtering (--no-state-filter)")

        # Step 3: Save to Bronze
        logger.info("\n💾 STEP 3: Saving to Bronze layer...")

        # Construct key
        year = execution_date.year
        month = execution_date.month
        day = execution_date.day

        # Save to S3/MinIO
        if args.format == "json":
            details_key = (
                f"pncp_details/year={year}/month={month:02d}/day={day:02d}/details.json"
            )
            storage.write_json_to_s3(
                bucket=storage.BUCKET_BRONZE,
                key=details_key,
                data=enriched_contratacoes,
            )
        else:
            # Parquet format (preserves nested structure)
            from backend.app.services.ingestion.pncp_details import (
                convert_nested_to_dataframe,
                save_to_parquet_bronze,
            )

            df = convert_nested_to_dataframe(enriched_contratacoes)
            # Use append mode for auto-resume, overwrite otherwise
            save_mode = "append" if args.auto_resume else "overwrite"
            details_key = save_to_parquet_bronze(
                df=df,
                storage_client=storage,
                execution_date=execution_date,
                mode=save_mode,
            )

        logger.info(f"✅ Saved to: s3://{storage.BUCKET_BRONZE}/{details_key}")

        # Step 4: Save local copy (optional)
        if args.output_file:
            logger.info(f"\n📝 Saving local copy to {args.output_file}...")
            output_path = Path(args.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(enriched_contratacoes, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Saved local copy: {output_path}")

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ INGESTION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Contratacoes processed: {len(enriched_contratacoes)}")
        logger.info(
            f"Total itens: {sum(len(c.get('itens', [])) for c in enriched_contratacoes)}"
        )
        logger.info(
            f"Total arquivos: {sum(len(c.get('arquivos', [])) for c in enriched_contratacoes)}"
        )
        logger.info(f"Storage location: s3://{storage.BUCKET_BRONZE}/{details_key}")

        if metadata.get("remaining_contratacoes") is not None:
            remaining = metadata["remaining_contratacoes"]
            if remaining > 0:
                logger.info(f"📋 Remaining: {remaining} contratacoes to process (run again to continue)")
            else:
                logger.info("✅ All contratacoes processed!")

        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"\n❌ Error during ingestion: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
