"""
PNCP Ingestion Service - Framework-agnostic business logic.

This service can be used standalone or integrated with Airflow/other orchestrators.
No Airflow dependencies - pure Python business logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.app.core.pncp_client import PNCPClient
from backend.app.domains.pncp import ModalidadeContratacao

logger = logging.getLogger(__name__)


class PNCPIngestionService:
    """
    Service for ingesting data from PNCP API.

    Pure Python class with no framework dependencies.
    Can be used standalone or wrapped by orchestration frameworks.
    """

    def __init__(
        self,
        pncp_client: Optional[PNCPClient] = None,
        endpoint_url: str = "https://pncp.gov.br/api",
    ):
        """
        Initialize PNCP ingestion service.

        Args:
            pncp_client: Optional pre-configured PNCP client
            endpoint_url: PNCP API endpoint URL
        """
        self.pncp_client = pncp_client or PNCPClient(endpoint_url=endpoint_url)

    def fetch_by_date_range(
        self,
        data_inicial: str,
        data_final: str,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
        num_pages: Optional[int] = None,
    ) -> Dict:
        """
        Fetch procurement data for a date range.

        Args:
            data_inicial: Start date (YYYYMMDD format)
            data_final: End date (YYYYMMDD format)
            modalidades: List of modalidades to fetch (defaults to ALL)
            num_pages: Optional limit on pages per modalidade

        Returns:
            Dict with:
                - data: List of raw records
                - metadata: Ingestion metadata

        Example:
            >>> service = PNCPIngestionService()
            >>> result = service.fetch_by_date_range(
            ...     data_inicial="20241022",
            ...     data_final="20241022",
            ...     modalidades=[ModalidadeContratacao.PREGAO_ELETRONICO],
            ...     num_pages=5
            ... )
            >>> print(f"Fetched {result['metadata']['record_count']} records")
        """
        if modalidades is None:
            modalidades = ModalidadeContratacao.get_all()

        logger.info(
            f"Fetching PNCP data: {data_inicial} to {data_final}, "
            f"{len(modalidades)} modalidades, {num_pages or 'all'} pages"
        )

        all_data = []
        modalidade_stats = {}

        for idx, modalidade in enumerate(modalidades, 1):
            logger.info(
                f"[{idx}/{len(modalidades)}] Fetching {modalidade.descricao}..."
            )

            try:
                data = self.pncp_client.fetch_all_contratacoes_by_date(
                    data_inicial=data_inicial,
                    data_final=data_final,
                    modalidades=[modalidade],
                    num_pages=num_pages,
                )

                all_data.extend(data)
                record_count = len(data)
                modalidade_stats[modalidade.descricao] = record_count

                if record_count == 0:
                    logger.info(f"  → No data available for {modalidade.descricao}")
                else:
                    logger.info(f"  → Fetched {record_count} records")

            except Exception as e:
                # This catches unexpected errors (network issues, API failures, etc.)
                # Empty responses are now handled gracefully in pncp_client
                logger.error(
                    f"Unexpected error fetching {modalidade.descricao}: {e}",
                    exc_info=True,
                )
                modalidade_stats[modalidade.descricao] = 0

        logger.info(f"Total records fetched: {len(all_data)}")

        return {
            "data": all_data,
            "metadata": {
                "data_inicial": data_inicial,
                "data_final": data_final,
                "record_count": len(all_data),
                "modalidades": [m.descricao for m in modalidades],
                "modalidade_stats": modalidade_stats,
                "ingestion_timestamp": datetime.now().isoformat(),
            },
        }

    def fetch_hourly_incremental(
        self,
        execution_date: datetime,
        num_pages: int = 20,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
    ) -> Dict:
        """
        Fetch last N pages for hourly incremental ingestion.

        Args:
            execution_date: Execution datetime (used for date range calculation)
            num_pages: Number of pages to fetch per modalidade (default: 20)
            modalidades: List of modalidades (defaults to ALL)

        Returns:
            Dict with data and metadata

        Example:
            >>> service = PNCPIngestionService()
            >>> result = service.fetch_hourly_incremental(
            ...     execution_date=datetime(2024, 10, 22, 14, 0),
            ...     num_pages=20
            ... )
        """
        # Date range: current hour
        # Convert UTC to Brazil timezone (BRT/BRST - UTC-3)
        # PNCP publishes data in Brazil local time, so we need to query based on BRT date
        import pytz

        brazil_tz = pytz.timezone("America/Sao_Paulo")

        # If execution_date is timezone-aware, convert it; otherwise assume UTC
        if execution_date.tzinfo is None:
            execution_date_utc = pytz.UTC.localize(execution_date)
        else:
            execution_date_utc = execution_date.astimezone(pytz.UTC)

        # Convert to Brazil timezone
        execution_date_br = execution_date_utc.astimezone(brazil_tz)

        data_inicial = execution_date_br.strftime("%Y%m%d")
        data_final = data_inicial

        logger.info(
            f"Hourly incremental ingestion: {data_inicial}, {num_pages} pages/modalidade"
        )

        return self.fetch_by_date_range(
            data_inicial=data_inicial,
            data_final=data_final,
            modalidades=modalidades,
            num_pages=num_pages,
        )

    def fetch_daily_complete(
        self,
        execution_date: datetime,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
    ) -> Dict:
        """
        Fetch complete day data for daily batch ingestion.

        Args:
            execution_date: Execution datetime
            modalidades: List of modalidades (defaults to ALL)

        Returns:
            Dict with data and metadata

        Example:
            >>> service = PNCPIngestionService()
            >>> result = service.fetch_daily_complete(
            ...     execution_date=datetime(2024, 10, 22)
            ... )
        """
        # Fetch previous day's data (run at 2 AM for yesterday)
        # Convert UTC to Brazil timezone (BRT/BRST - UTC-3)
        import pytz

        brazil_tz = pytz.timezone("America/Sao_Paulo")

        # If execution_date is timezone-aware, convert it; otherwise assume UTC
        if execution_date.tzinfo is None:
            execution_date_utc = pytz.UTC.localize(execution_date)
        else:
            execution_date_utc = execution_date.astimezone(pytz.UTC)

        # Convert to Brazil timezone and get previous day
        execution_date_br = execution_date_utc.astimezone(brazil_tz)
        target_date = execution_date_br - timedelta(days=1)

        data_inicial = target_date.strftime("%Y%m%d")
        data_final = data_inicial

        logger.info(f"Daily complete ingestion: {data_inicial}")

        return self.fetch_by_date_range(
            data_inicial=data_inicial,
            data_final=data_final,
            modalidades=modalidades,
            num_pages=None,  # Fetch all pages
        )

    def fetch_backfill(
        self,
        start_date: datetime,
        end_date: datetime,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
    ) -> Dict:
        """
        Fetch historical data for backfilling.

        Args:
            start_date: Start date
            end_date: End date
            modalidades: List of modalidades (defaults to ALL)

        Returns:
            Dict with data and metadata

        Example:
            >>> service = PNCPIngestionService()
            >>> result = service.fetch_backfill(
            ...     start_date=datetime(2024, 10, 1),
            ...     end_date=datetime(2024, 10, 31)
            ... )
        """
        data_inicial = start_date.strftime("%Y%m%d")
        data_final = end_date.strftime("%Y%m%d")

        logger.info(f"Backfill ingestion: {data_inicial} to {data_final}")

        return self.fetch_by_date_range(
            data_inicial=data_inicial,
            data_final=data_final,
            modalidades=modalidades,
            num_pages=None,  # Fetch all pages for backfill
        )


# Standalone execution
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="PNCP Ingestion Service")
    parser.add_argument(
        "--mode",
        choices=["hourly", "daily", "backfill", "custom"],
        default="custom",
        help="Ingestion mode",
    )
    parser.add_argument("--date", help="Date (YYYYMMDD format)")
    parser.add_argument("--start-date", help="Start date for backfill (YYYYMMDD)")
    parser.add_argument("--end-date", help="End date for backfill (YYYYMMDD)")
    parser.add_argument(
        "--pages", type=int, help="Number of pages per modalidade (for testing)"
    )
    parser.add_argument(
        "--modalidades",
        type=int,
        help="Number of modalidades to fetch (1-13, defaults to all)",
    )

    args = parser.parse_args()

    # Initialize service
    service = PNCPIngestionService()

    # Select modalidades
    modalidades = ModalidadeContratacao.get_all()
    if args.modalidades:
        modalidades = ModalidadeContratacao.get_all()[: args.modalidades]
        logger.info(f"Using {len(modalidades)} modalidades for testing")

    # Execute based on mode
    if args.mode == "hourly":
        date = datetime.strptime(args.date, "%Y%m%d") if args.date else datetime.now()
        result = service.fetch_hourly_incremental(
            execution_date=date, num_pages=args.pages or 20, modalidades=modalidades
        )

    elif args.mode == "daily":
        date = datetime.strptime(args.date, "%Y%m%d") if args.date else datetime.now()
        result = service.fetch_daily_complete(
            execution_date=date, modalidades=modalidades
        )

    elif args.mode == "backfill":
        start_date = datetime.strptime(args.start_date, "%Y%m%d")
        end_date = datetime.strptime(args.end_date, "%Y%m%d")
        result = service.fetch_backfill(
            start_date=start_date, end_date=end_date, modalidades=modalidades
        )

    else:  # custom
        if not args.date:
            args.date = datetime.now().strftime("%Y%m%d")

        result = service.fetch_by_date_range(
            data_inicial=args.date,
            data_final=args.date,
            modalidades=modalidades,
            num_pages=args.pages,
        )

    # Print results
    print("\n" + "=" * 60)
    print("INGESTION RESULTS")
    print("=" * 60)
    print(f"Records fetched: {result['metadata']['record_count']}")
    print(
        f"Date range: {result['metadata']['data_inicial']} - {result['metadata']['data_final']}"
    )
    print("\nModalidade breakdown:")
    for modalidade, count in result["metadata"]["modalidade_stats"].items():
        print(f"  {modalidade}: {count}")
    print("=" * 60)
