"""
PNCP Details Ingestion Service - Framework-agnostic business logic.

Fetches items (itens) and documents (arquivos) from PNCP API for contratacoes.
No Airflow dependencies - pure Python business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.app.core.pncp_client import PNCPClient

logger = logging.getLogger(__name__)


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize data structure for JSON serialization.

    Converts numpy types, pandas NA values, and other non-serializable types
    to native Python types.

    Args:
        obj: Object to sanitize

    Returns:
        Sanitized object that is JSON serializable
    """
    # Handle None
    if obj is None:
        return None

    # Handle numpy types (check before pandas to avoid ambiguity)
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)

    # Handle pandas NA/NaT (scalar values only)
    try:
        import pandas as pd
        # Only check scalars, not arrays
        if not isinstance(obj, (dict, list, tuple)):
            try:
                if pd.isna(obj):
                    return None
            except (ValueError, TypeError):
                # Can't check this type with pd.isna, continue
                pass
    except ImportError:
        pass

    # Handle datetime
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Handle dictionaries
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}

    # Handle lists/tuples
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]

    # Return as-is for native types
    return obj


def convert_nested_to_dataframe(contratacoes: List[Dict]) -> pd.DataFrame:
    """
    Convert nested contratacoes structure to flat DataFrame for Parquet storage.

    Each row represents one contratacao with itens and arquivos stored as nested lists.
    Parquet supports nested types (lists, structs) natively.

    Args:
        contratacoes: List of contratacoes with nested itens/arquivos

    Returns:
        DataFrame with nested columns preserved
    """
    if not contratacoes:
        # Return empty DataFrame with expected schema
        return pd.DataFrame(columns=[
            'cnpj', 'anoCompra', 'sequencialCompra', 'numeroControlePNCP',
            'itens', 'arquivos', '_metadata'
        ])

    # Sanitize data first to handle numpy types
    sanitized = [sanitize_for_json(c) for c in contratacoes]

    # Create DataFrame - pandas will handle nested lists naturally
    df = pd.DataFrame(sanitized)

    logger.info(f"Converted {len(df)} contratacoes to DataFrame ({df.memory_usage(deep=True).sum() / 1024:.1f} KB)")

    return df


def save_to_parquet_bronze(
    df: pd.DataFrame,
    storage_client,
    execution_date: datetime,
    mode: str = "overwrite"
) -> str:
    """
    Save details DataFrame to Bronze in Parquet format.

    Args:
        df: DataFrame with details
        storage_client: Storage client (MinIO/S3)
        execution_date: Date for partitioning
        mode: 'overwrite' or 'append'

    Returns:
        S3 key where data was saved
    """
    import io

    year = execution_date.year
    month = execution_date.month
    day = execution_date.day

    s3_key = f"pncp_details/year={year}/month={month:02d}/day={day:02d}/details.parquet"

    if mode == "append":
        # Read existing file if it exists
        try:
            # Access underlying client
            client = getattr(storage_client, '_client', storage_client)
            existing_df = client.read_parquet_from_s3(
                bucket_name=storage_client.BUCKET_BRONZE,
                object_name=s3_key
            )
            logger.info(f"Read existing Parquet: {len(existing_df)} rows")

            # Append new data
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.info(f"Appended {len(df) - len(existing_df)} rows, total: {len(df)}")

        except Exception as e:
            logger.info(f"No existing file or error reading: {e}. Creating new file.")

    # Save to Parquet using same pattern as upload_temp
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
    buffer.seek(0)

    # Access underlying client (MinIOClient or S3Client)
    client = getattr(storage_client, '_client', storage_client)

    client.upload_fileobj(
        file_obj=buffer,
        bucket_name=storage_client.BUCKET_BRONZE,
        object_name=s3_key
    )

    logger.info(
        f"Saved {len(df)} contratacoes to {s3_key} "
        f"(Parquet format, size: {buffer.getbuffer().nbytes / 1024:.1f} KB)"
    )

    return s3_key


class PNCPDetailsIngestionService:
    """
    Service for ingesting procurement details (items + documents) from PNCP API.

    Reads contratacoes from Bronze layer and fetches associated details.
    Pure Python class with no framework dependencies.
    """

    def __init__(
        self,
        pncp_client: Optional[PNCPClient] = None,
        storage_client=None,
        endpoint_url: str = "https://pncp.gov.br/api",
    ):
        """
        Initialize PNCP details ingestion service.

        Args:
            pncp_client: Optional pre-configured PNCP client
            storage_client: Optional storage client (lazy-loaded if None)
            endpoint_url: PNCP API endpoint URL
        """
        self.pncp_client = pncp_client or PNCPClient(endpoint_url=endpoint_url)
        self._storage_client = storage_client

    @property
    def storage_client(self):
        """Lazy-load storage client."""
        if self._storage_client is None:
            from backend.app.core.storage_client import get_storage_client

            self._storage_client = get_storage_client()
        return self._storage_client

    def fetch_details_for_date(
        self,
        execution_date: datetime,
        max_contratacoes: Optional[int] = None,
        batch_size: Optional[int] = None,
        auto_resume: bool = False,
    ) -> Dict:
        """
        Fetch details (items + arquivos) for all contratacoes from a specific date.

        Args:
            execution_date: Date to fetch details for
            max_contratacoes: Optional limit for testing (default: all)
            batch_size: Number of contratacoes to process per execution (auto-resume mode)
            auto_resume: If True, automatically resume from last checkpoint

        Returns:
            Dict with:
                - data: List of enriched contratacoes with nested items/arquivos
                - metadata: Ingestion statistics

        Example:
            >>> service = PNCPDetailsIngestionService()
            >>> # Process all
            >>> result = service.fetch_details_for_date(
            ...     execution_date=datetime(2025, 10, 22)
            ... )
            >>> # Auto-resume mode (process 100 at a time)
            >>> result = service.fetch_details_for_date(
            ...     execution_date=datetime(2025, 10, 22),
            ...     batch_size=100,
            ...     auto_resume=True
            ... )
        """
        # 1. Read contratacoes from Bronze layer
        logger.info(f"Reading contratacoes from Bronze for {execution_date.date()}")
        contratacoes = self._read_contratacoes_from_bronze(execution_date)

        if not contratacoes:
            logger.info(f"No contratacoes found for {execution_date.date()}")
            return {
                "data": [],
                "metadata": {
                    "execution_date": execution_date.isoformat(),
                    "contratacoes_processed": 0,
                    "total_itens": 0,
                    "total_arquivos": 0,
                    "api_calls": 0,
                    "errors": 0,
                    "remaining_contratacoes": 0,
                },
            }

        # 2. Auto-resume: Filter out already processed contratacoes
        if auto_resume:
            from backend.app.services import StateManager

            state_manager = StateManager()

            # Use itens state as checkpoint reference
            unprocessed_contratacoes, resume_stats = state_manager.filter_new_details(
                source="pncp_details",
                date=execution_date,
                contratacoes=contratacoes,
                detail_type="itens",
                key_extractor_fn=self.extract_key_from_contratacao,
            )

            logger.info(
                f"🔄 Auto-resume: {resume_stats['total_input']} total, "
                f"{len(unprocessed_contratacoes)} remaining to process "
                f"({resume_stats['already_processed']} already done)"
            )

            contratacoes = unprocessed_contratacoes

            if not contratacoes:
                logger.info("✅ All contratacoes already processed (auto-resume complete)")
                return {
                    "data": [],
                    "metadata": {
                        "execution_date": execution_date.isoformat(),
                        "contratacoes_processed": 0,
                        "total_itens": 0,
                        "total_arquivos": 0,
                        "api_calls": 0,
                        "errors": 0,
                        "remaining_contratacoes": 0,
                        "resume_stats": resume_stats,
                    },
                }

        # 3. Apply batch size (process only first N unprocessed)
        total_available = len(contratacoes)
        if batch_size and batch_size < len(contratacoes):
            logger.info(
                f"📦 Batch mode: processing {batch_size} of {len(contratacoes)} available"
            )
            contratacoes = contratacoes[:batch_size]
        elif max_contratacoes:
            # Legacy test limit
            logger.info(f"Limiting to {max_contratacoes} contratacoes for testing")
            contratacoes = contratacoes[:max_contratacoes]

        logger.info(f"Processing {len(contratacoes)} contratacoes...")

        # 2. Fetch details for each contratacao
        enriched_contratacoes = []
        total_itens = 0
        total_arquivos = 0
        api_calls = 0
        errors = 0

        for idx, contratacao in enumerate(contratacoes, 1):
            try:
                # Fetch details
                enriched, stats = self._fetch_single_contratacao_details(contratacao)

                # Accumulate stats
                total_itens += stats["itens_count"]
                total_arquivos += stats["arquivos_count"]
                api_calls += stats["api_calls"]

                enriched_contratacoes.append(enriched)

                # Log progress every 100 contratacoes
                if idx % 100 == 0:
                    logger.info(
                        f"Progress: {idx}/{len(contratacoes)} contratacoes, "
                        f"{total_itens} itens, {total_arquivos} arquivos"
                    )

            except Exception as e:
                logger.error(
                    f"Error fetching details for contratacao #{idx}: {e}", exc_info=True
                )
                errors += 1
                # Still add contratacao without details
                enriched_contratacoes.append(
                    {
                        **contratacao,
                        "itens": [],
                        "arquivos": [],
                        "metadata": {
                            "total_itens": 0,
                            "total_arquivos": 0,
                            "fetch_timestamp": datetime.now().isoformat(),
                            "fetch_error": str(e),
                        },
                    }
                )

        logger.info(
            f"✅ Processed {len(contratacoes)} contratacoes: "
            f"{total_itens} itens, {total_arquivos} arquivos "
            f"({api_calls} API calls, {errors} errors)"
        )

        # Sanitize data for JSON serialization
        logger.debug("Sanitizing data for JSON serialization...")
        enriched_contratacoes_sanitized = sanitize_for_json(enriched_contratacoes)

        # Calculate remaining contratacoes for auto-resume
        remaining_contratacoes = 0
        if auto_resume:
            remaining_contratacoes = total_available - len(contratacoes)
            if remaining_contratacoes > 0:
                logger.info(f"📋 Remaining: {remaining_contratacoes} contratacoes to process in future runs")

        return {
            "data": enriched_contratacoes_sanitized,
            "metadata": {
                "execution_date": execution_date.isoformat(),
                "contratacoes_processed": len(contratacoes),
                "total_itens": total_itens,
                "total_arquivos": total_arquivos,
                "api_calls": api_calls,
                "errors": errors,
                "ingestion_timestamp": datetime.now().isoformat(),
                "remaining_contratacoes": remaining_contratacoes if auto_resume else None,
            },
        }

    def _read_contratacoes_from_bronze(self, execution_date: datetime) -> List[Dict]:
        """
        Read contratacoes from Bronze layer for a specific date.

        Args:
            execution_date: Date to read

        Returns:
            List of contratacao dicts
        """
        # Construct partition path
        year = execution_date.year
        month = execution_date.month
        day = execution_date.day

        prefix = f"pncp/year={year}/month={month:02d}/day={day:02d}/"

        logger.info(f"Reading from Bronze: {prefix}")

        try:
            # List all parquet files in the partition
            objects = self.storage_client.list_objects(
                bucket=self.storage_client.BUCKET_BRONZE,
                prefix=prefix,
            )

            # Filter for parquet files only
            parquet_files = [
                obj["Key"] for obj in objects if obj["Key"].endswith(".parquet")
            ]

            if not parquet_files:
                logger.warning(f"No parquet files found in {prefix}")
                return []

            logger.info(f"Found {len(parquet_files)} parquet files")

            # Read all parquet files and concatenate
            import pandas as pd

            dfs = []
            for file_key in parquet_files:
                df = self.storage_client.read_parquet_from_s3(
                    bucket=self.storage_client.BUCKET_BRONZE, key=file_key
                )
                dfs.append(df)

            # Concatenate all DataFrames
            if dfs:
                combined_df = pd.concat(dfs, ignore_index=True)
                logger.info(f"Loaded {len(combined_df)} contratacoes from Bronze")
                return combined_df.to_dict(orient="records")
            else:
                return []

        except Exception as e:
            logger.warning(
                f"No contratacoes found in Bronze for {execution_date.date()}: {e}"
            )
            return []

    def _fetch_single_contratacao_details(
        self, contratacao: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Fetch details (itens + arquivos) for a single contratacao.

        Args:
            contratacao: Contratacao dict from Bronze

        Returns:
            Tuple of (enriched_contratacao, stats)
        """
        # Extract identifiers
        cnpj = contratacao.get("cnpj") or contratacao.get("orgaoEntidade", {}).get(
            "cnpj"
        )
        ano = contratacao.get("anoCompra")
        sequencial = contratacao.get("sequencialCompra")
        numero_controle = contratacao.get("numeroControlePNCP")

        # Validate required fields
        if not cnpj or not ano or not sequencial:
            logger.warning(
                f"Missing required fields in contratacao {numero_controle}: "
                f"cnpj={cnpj}, ano={ano}, sequencial={sequencial}"
            )
            return (
                {
                    **contratacao,
                    "itens": [],
                    "arquivos": [],
                    "metadata": {
                        "total_itens": 0,
                        "total_arquivos": 0,
                        "fetch_timestamp": datetime.now().isoformat(),
                        "fetch_error": "Missing cnpj/ano/sequencial",
                    },
                },
                {"itens_count": 0, "arquivos_count": 0, "api_calls": 0},
            )

        # Fetch itens
        itens = []
        try:
            itens = self.pncp_client.fetch_all_itens_contratacao(
                cnpj=cnpj, ano=ano, sequencial=sequencial
            )
        except Exception as e:
            logger.error(f"Error fetching itens for {cnpj}/{ano}/{sequencial}: {e}")

        # Fetch arquivos
        arquivos = []
        try:
            arquivos = self.pncp_client.fetch_all_arquivos_contratacao(
                cnpj=cnpj, ano=ano, sequencial=sequencial
            )
        except Exception as e:
            logger.error(f"Error fetching arquivos for {cnpj}/{ano}/{sequencial}: {e}")

        # Build enriched contratacao with nested structure
        enriched = {
            **contratacao,
            "itens": itens,
            "arquivos": arquivos,
            "metadata": {
                "total_itens": len(itens),
                "total_arquivos": len(arquivos),
                "fetch_timestamp": datetime.now().isoformat(),
                "api_calls": 2,  # 1 for itens, 1 for arquivos
            },
        }

        stats = {
            "itens_count": len(itens),
            "arquivos_count": len(arquivos),
            "api_calls": 2,
        }

        return enriched, stats

    @staticmethod
    def build_composite_key(cnpj: str, ano: int, sequencial: int) -> str:
        """
        Build composite key for state management.

        Args:
            cnpj: CNPJ do órgão
            ano: Ano da compra
            sequencial: Número sequencial

        Returns:
            Composite key string

        Example:
            >>> PNCPDetailsIngestionService.build_composite_key(
            ...     "83102277000152", 2025, 423
            ... )
            '83102277000152|2025|423'
        """
        return f"{cnpj}|{ano}|{sequencial}"

    @staticmethod
    def extract_key_from_contratacao(contratacao: Dict) -> Optional[str]:
        """
        Extract composite key from contratacao dict.

        Args:
            contratacao: Contratacao dict

        Returns:
            Composite key or None if missing fields
        """
        cnpj = contratacao.get("cnpj") or contratacao.get("orgaoEntidade", {}).get(
            "cnpj"
        )
        ano = contratacao.get("anoCompra")
        sequencial = contratacao.get("sequencialCompra")

        if cnpj and ano and sequencial:
            return PNCPDetailsIngestionService.build_composite_key(
                cnpj, ano, sequencial
            )
        return None


# Standalone execution
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="PNCP Details Ingestion Service")
    parser.add_argument("--date", required=True, help="Date (YYYYMMDD format)")
    parser.add_argument(
        "--max-contratacoes",
        type=int,
        help="Max contratacoes to process (for testing)",
    )

    args = parser.parse_args()

    # Parse date
    execution_date = datetime.strptime(args.date, "%Y%m%d")

    # Initialize service
    service = PNCPDetailsIngestionService()

    # Execute
    result = service.fetch_details_for_date(
        execution_date=execution_date,
        max_contratacoes=args.max_contratacoes,
    )

    # Print results
    print("\n" + "=" * 60)
    print("PNCP DETAILS INGESTION RESULTS")
    print("=" * 60)
    print(f"Date: {result['metadata']['execution_date']}")
    print(f"Contratacoes processed: {result['metadata']['contratacoes_processed']}")
    print(f"Total itens: {result['metadata']['total_itens']}")
    print(f"Total arquivos: {result['metadata']['total_arquivos']}")
    print(f"API calls: {result['metadata']['api_calls']}")
    print(f"Errors: {result['metadata']['errors']}")
    print("=" * 60)

    if result["data"]:
        print("\nFirst contratacao with details:")
        first = result["data"][0]
        print(f"  CNPJ: {first.get('cnpj')}")
        print(f"  Ano/Seq: {first.get('anoCompra')}/{first.get('sequencialCompra')}")
        print(f"  Itens: {len(first.get('itens', []))}")
        print(f"  Arquivos: {len(first.get('arquivos', []))}")
