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
        return pd.DataFrame(
            columns=[
                "cnpj",
                "anoCompra",
                "sequencialCompra",
                "numeroControlePNCP",
                "itens",
                "arquivos",
                "_metadata",
            ]
        )

    # Sanitize data first to handle numpy types
    sanitized = [sanitize_for_json(c) for c in contratacoes]

    # Create DataFrame - pandas will handle nested lists naturally
    df = pd.DataFrame(sanitized)

    logger.info(
        f"Converted {len(df)} contratacoes to DataFrame ({df.memory_usage(deep=True).sum() / 1024:.1f} KB)"
    )

    return df


def save_to_parquet_bronze(
    df: pd.DataFrame,
    storage_client,
    execution_date: datetime,
    mode: str = "overwrite",
    chunk_num: Optional[int] = None,
) -> str:
    """
    Save details DataFrame to Bronze in Parquet format.

    Args:
        df: DataFrame with details
        storage_client: Storage client (MinIO/S3)
        execution_date: Date for partitioning
        mode: 'overwrite' or 'append' (deprecated, use chunk_num for multiple files)
        chunk_num: Optional chunk number for multi-file storage

    Returns:
        S3 key where data was saved
    """
    import io

    year = execution_date.year
    month = execution_date.month
    day = execution_date.day

    # Determine filename based on chunk_num
    if chunk_num is not None:
        filename = f"chunk_{chunk_num:04d}.parquet"
    else:
        filename = "details.parquet"

    s3_key = f"pncp_details/year={year}/month={month:02d}/day={day:02d}/{filename}"

    # DEPRECATED: append mode (kept for backward compatibility)
    if mode == "append" and chunk_num is None:
        # Read existing file if it exists
        try:
            # Access underlying client
            client = getattr(storage_client, "_client", storage_client)
            existing_df = client.read_parquet_from_s3(
                bucket_name=storage_client.BUCKET_BRONZE, object_name=s3_key
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
    client = getattr(storage_client, "_client", storage_client)

    client.upload_fileobj(
        file_obj=buffer, bucket_name=storage_client.BUCKET_BRONZE, object_name=s3_key
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
        checkpoint_every: int = 100,
    ) -> Dict:
        """
        Fetch details (items + arquivos) for all contratacoes from a specific date.

        Args:
            execution_date: Date to fetch details for
            max_contratacoes: Optional limit for testing (default: all)
            batch_size: Number of contratacoes to process per execution (auto-resume mode)
            auto_resume: If True, automatically resume from last checkpoint
            checkpoint_every: Save to Bronze every N contratacoes (default: 100)

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
                logger.info(
                    "✅ All contratacoes already processed (auto-resume complete)"
                )
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

        # Print startup banner for Airflow UI
        print(f"\n{'='*70}")
        print("🚀 STARTING DETAILS INGESTION")
        print(f"{'='*70}")
        print(f"📅 Date: {execution_date.date()}")
        print(f"📦 Total contratacoes: {len(contratacoes)}")
        print(f"🔄 Checkpoint every: {checkpoint_every}")
        if batch_size:
            print(f"📊 Batch size: {batch_size}")
        if auto_resume:
            print("♻️  Auto-resume: ENABLED")
        print(f"{'='*70}\n")

        # 2. Fetch details for each contratacao with chunking
        chunk_buffer = []  # ✅ Buffer for current chunk only
        total_itens = 0
        total_arquivos = 0
        api_calls = 0
        errors = 0

        # ✅ Start from last existing chunk to avoid overwriting
        chunks_saved = self._get_next_chunk_number(execution_date) - 1

        for idx, contratacao in enumerate(contratacoes, 1):
            try:
                # Fetch details
                enriched, stats = self._fetch_single_contratacao_details(contratacao)

                # Accumulate stats
                total_itens += stats["itens_count"]
                total_arquivos += stats["arquivos_count"]
                api_calls += stats["api_calls"]

                chunk_buffer.append(enriched)

                # 🔄 CHECKPOINT: Save chunk and clear buffer every N contratacoes
                if idx % checkpoint_every == 0:
                    chunks_saved += 1
                    self._save_chunk(
                        chunk_data=chunk_buffer,
                        execution_date=execution_date,
                        chunk_num=chunks_saved,
                        auto_resume=auto_resume,
                    )

                    checkpoint_msg = (
                        f"💾 Chunk {chunks_saved}: Saved {len(chunk_buffer)} contratacoes "
                        f"({idx}/{len(contratacoes)} total progress, "
                        f"{total_itens} itens, {total_arquivos} arquivos)"
                    )
                    logger.info(checkpoint_msg)
                    # Print for Airflow UI visibility
                    print(f"\n{'='*70}")
                    print(checkpoint_msg)
                    print(f"{'='*70}\n")

                    # ✅ CLEAR BUFFER - Free memory
                    chunk_buffer = []

                # Log progress every 100 contratacoes (if checkpoint_every > 100)
                elif idx % 100 == 0:
                    progress_msg = (
                        f"Progress: {idx}/{len(contratacoes)} contratacoes, "
                        f"{total_itens} itens, {total_arquivos} arquivos"
                    )
                    logger.info(progress_msg)
                    # Print for Airflow UI visibility
                    print(progress_msg)

            except Exception as e:
                logger.error(
                    f"Error fetching details for contratacao #{idx}: {e}", exc_info=True
                )
                errors += 1
                # Still add contratacao without details
                chunk_buffer.append(
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

        # 🔄 FINAL CHUNK: Save any remaining contratacoes
        if chunk_buffer:
            chunks_saved += 1
            self._save_chunk(
                chunk_data=chunk_buffer,
                execution_date=execution_date,
                chunk_num=chunks_saved,
                auto_resume=auto_resume,
            )
            final_msg = f"💾 Final chunk {chunks_saved}: Saved remaining {len(chunk_buffer)} contratacoes"
            logger.info(final_msg)
            # Print for Airflow UI visibility
            print(f"\n{'='*70}")
            print(final_msg)
            print(f"{'='*70}\n")

        # ✅ State is now saved incrementally in _save_chunk()
        # No need for final state update here

        # Print completion summary for Airflow UI
        print(f"\n{'='*70}")
        print("✅ INGESTION COMPLETE")
        print(f"{'='*70}")
        print(f"📦 Contratacoes processed: {len(contratacoes)}")
        print(f"📝 Total itens: {total_itens}")
        print(f"📄 Total arquivos: {total_arquivos}")
        print(f"🌐 API calls: {api_calls}")
        print(f"❌ Errors: {errors}")
        print(f"💾 Chunks saved: {chunks_saved}")
        print(f"{'='*70}\n")

        logger.info(
            f"✅ Processed {len(contratacoes)} contratacoes: "
            f"{total_itens} itens, {total_arquivos} arquivos "
            f"({api_calls} API calls, {errors} errors, {chunks_saved} chunks saved)"
        )

        # Calculate remaining contratacoes for auto-resume
        remaining_contratacoes = 0
        if auto_resume:
            remaining_contratacoes = total_available - len(contratacoes)
            if remaining_contratacoes > 0:
                logger.info(
                    f"📋 Remaining: {remaining_contratacoes} contratacoes to process in future runs"
                )

        # ✅ Return only metadata (data already saved in chunks)
        return {
            "data": [],  # Empty - data saved incrementally in chunks
            "metadata": {
                "execution_date": execution_date.isoformat(),
                "contratacoes_processed": len(contratacoes),
                "total_itens": total_itens,
                "total_arquivos": total_arquivos,
                "api_calls": api_calls,
                "errors": errors,
                "chunks_saved": chunks_saved,
                "ingestion_timestamp": datetime.now().isoformat(),
                "remaining_contratacoes": remaining_contratacoes
                if auto_resume
                else None,
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
                total_before = len(combined_df)

                # ✅ DEDUPLICATE by numeroControlePNCP (multiple files may have duplicates)
                if "numeroControlePNCP" in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(
                        subset=["numeroControlePNCP"], keep="first"
                    )
                    total_after = len(combined_df)
                    duplicates_removed = total_before - total_after

                    logger.info(
                        f"Loaded {total_before} contratacoes from Bronze → "
                        f"{total_after} unique ({duplicates_removed} duplicates removed)"
                    )
                else:
                    logger.warning(
                        "numeroControlePNCP column not found - skipping deduplication"
                    )
                    logger.info(f"Loaded {total_before} contratacoes from Bronze")

                return combined_df.to_dict(orient="records")
            else:
                return []

        except Exception as e:
            logger.warning(
                f"No contratacoes found in Bronze for {execution_date.date()}: {e}"
            )
            return []

    def _fetch_single_contratacao_details(self, contratacao: Dict) -> Tuple[Dict, Dict]:
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

    def _get_next_chunk_number(self, execution_date: datetime) -> int:
        """
        Discover existing chunks for a date and return next chunk number.

        This ensures chunks are numbered sequentially across multiple DAG executions,
        preventing overwriting of existing chunks.

        Args:
            execution_date: Date to check for existing chunks

        Returns:
            Next chunk number (max_existing + 1, or 1 if none exist)
        """
        import re

        year = execution_date.year
        month = execution_date.month
        day = execution_date.day
        prefix = f"pncp_details/year={year}/month={month:02d}/day={day:02d}/"

        try:
            objects = self.storage_client.list_objects(
                bucket=self.storage_client.BUCKET_BRONZE,
                prefix=prefix,
            )
        except Exception as e:
            logger.warning(f"Could not list existing chunks: {e}. Starting from 1.")
            return 1

        chunk_pattern = r"chunk_(\d{4})\.parquet"
        chunk_numbers = []

        for obj in objects:
            filename = obj["Key"].split("/")[-1]
            match = re.match(chunk_pattern, filename)
            if match:
                chunk_numbers.append(int(match.group(1)))

        if chunk_numbers:
            next_num = max(chunk_numbers) + 1
            logger.info(
                f"Found {len(chunk_numbers)} existing chunks (max: {max(chunk_numbers)}). "
                f"Next chunk: {next_num}"
            )
            return next_num
        else:
            logger.info("No existing chunks found. Starting from 1.")
            return 1

    def consolidate_and_deduplicate(self, execution_date: datetime) -> dict:
        """
        Consolidate all chunks for a date into a single file and remove duplicates.

        This method:
        1. Reads all existing parquet files (chunks + details.parquet)
        2. Concatenates into a single DataFrame
        3. Removes duplicates based on numeroControlePNCP (keeps first)
        4. Saves as a single details.parquet file
        5. Deletes old chunk files

        Should be called after backfill operations to clean up duplicates.

        Args:
            execution_date: Date to consolidate

        Returns:
            Dict with consolidation stats
        """
        import io
        import pandas as pd

        year = execution_date.year
        month = execution_date.month
        day = execution_date.day
        prefix = f"pncp_details/year={year}/month={month:02d}/day={day:02d}/"

        try:
            objects = self.storage_client.list_objects(
                bucket=self.storage_client.BUCKET_BRONZE,
                prefix=prefix,
            )
        except Exception as e:
            logger.warning(f"Could not list existing files: {e}")
            return {"consolidated": False, "error": str(e)}

        # Filter only parquet files
        parquet_files = [
            obj["Key"] for obj in objects if obj["Key"].endswith(".parquet")
        ]

        if not parquet_files:
            logger.info(f"No data files to consolidate for {execution_date.date()}")
            return {"consolidated": False, "reason": "no_files"}

        if len(parquet_files) == 1 and parquet_files[0].endswith("details.parquet"):
            logger.info(f"Already consolidated for {execution_date.date()}")
            return {"consolidated": False, "reason": "already_consolidated"}

        # Read all parquet files
        logger.info(f"Reading {len(parquet_files)} files for consolidation...")
        dfs = []
        for key in parquet_files:
            try:
                df = self.storage_client.read_parquet_from_s3(
                    bucket=self.storage_client.BUCKET_BRONZE,
                    key=key,
                )
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to read {key}: {e}")

        if not dfs:
            return {"consolidated": False, "error": "no_readable_files"}

        # Concatenate and deduplicate
        combined = pd.concat(dfs, ignore_index=True)
        total_before = len(combined)

        # Deduplicate by numeroControlePNCP (keep first occurrence)
        if "numeroControlePNCP" in combined.columns:
            deduped = combined.drop_duplicates(
                subset=["numeroControlePNCP"], keep="first"
            )
        else:
            deduped = combined.drop_duplicates(keep="first")

        total_after = len(deduped)
        duplicates_removed = total_before - total_after

        logger.info(
            f"Deduplication: {total_before} → {total_after} "
            f"({duplicates_removed} duplicates removed)"
        )

        # Save as single file
        new_key = f"{prefix}details.parquet"

        # Convert to parquet bytes
        buffer = io.BytesIO()
        deduped.to_parquet(buffer, index=False, compression="snappy")
        buffer.seek(0)

        # Upload using low-level S3 client
        try:
            # Use the underlying client for raw upload
            if hasattr(self.storage_client, "_client"):
                self.storage_client._client.s3_client.put_object(
                    Bucket=self.storage_client.BUCKET_BRONZE,
                    Key=new_key,
                    Body=buffer.getvalue(),
                )
            else:
                self.storage_client.s3_client.put_object(
                    Bucket=self.storage_client.BUCKET_BRONZE,
                    Key=new_key,
                    Body=buffer.getvalue(),
                )
        except Exception as e:
            logger.error(f"Failed to save consolidated file: {e}")
            return {"consolidated": False, "error": str(e)}

        logger.info(f"Saved consolidated file: {new_key}")

        # Delete old chunk files (but not the new details.parquet)
        deleted_count = 0
        for key in parquet_files:
            if key != new_key:
                try:
                    self.storage_client.delete_object(
                        bucket=self.storage_client.BUCKET_BRONZE,
                        key=key,
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {key}: {e}")

        logger.info(f"Deleted {deleted_count} old chunk files")

        result = {
            "consolidated": True,
            "total_before": total_before,
            "total_after": total_after,
            "duplicates_removed": duplicates_removed,
            "chunks_deleted": deleted_count,
            "output_file": new_key,
        }

        print(
            f"✅ Consolidation complete: {total_after} unique records "
            f"({duplicates_removed} duplicates removed)"
        )

        return result

    def _save_chunk(
        self,
        chunk_data: List[Dict],
        execution_date: datetime,
        chunk_num: int,
        auto_resume: bool,
    ) -> None:
        """
        Save chunk to Bronze layer as separate Parquet file and update state.

        Args:
            chunk_data: Contratacoes in current chunk (not cumulative)
            execution_date: Date for partitioning
            chunk_num: Chunk number (for filename)
            auto_resume: Whether to update state tracking
        """
        try:
            # 1. Convert to DataFrame
            df = convert_nested_to_dataframe(chunk_data)

            # 2. Save to Bronze as separate chunk file
            s3_key = save_to_parquet_bronze(
                df=df,
                storage_client=self.storage_client,
                execution_date=execution_date,
                mode="overwrite",  # Each chunk is independent
                chunk_num=chunk_num,  # Pass chunk number for filename
            )

            logger.debug(
                f"Chunk {chunk_num} saved to {s3_key} ({len(df)} contratacoes)"
            )

            # Print chunk save confirmation for Airflow UI
            print(f"   ✓ Saved to Bronze: {s3_key}")

            # 3. Update state incrementally (if auto-resume enabled)
            if auto_resume:
                from backend.app.services import StateManager

                state_manager = StateManager()

                # Extract keys from chunk
                chunk_keys = []
                for c in chunk_data:
                    key = self.extract_key_from_contratacao(c)
                    if key:
                        chunk_keys.append(key)

                # Update itens state
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="itens",
                    new_keys=chunk_keys,
                    execution_metadata={
                        "chunk_num": chunk_num,
                        "contratacoes_in_chunk": len(chunk_data),
                    },
                )

                # Update arquivos state (same keys)
                state_manager.update_details_state(
                    source="pncp_details",
                    date=execution_date,
                    detail_type="arquivos",
                    new_keys=chunk_keys,
                    execution_metadata={
                        "chunk_num": chunk_num,
                        "contratacoes_in_chunk": len(chunk_data),
                    },
                )

                logger.debug(
                    f"State updated: {len(chunk_keys)} keys from chunk {chunk_num}"
                )

        except Exception as e:
            error_msg = f"⚠️  Failed to save chunk {chunk_num}: {e}"
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            # Don't raise - chunk failure shouldn't stop processing

    @staticmethod
    def extract_key_from_contratacao(contratacao: Dict) -> Optional[str]:
        """
        Extract unique key from contratacao dict for state management.

        Uses numeroControlePNCP directly as the unique identifier.
        This is more robust than building composite keys from nested fields
        (like orgaoEntidade.cnpj) which may be serialized differently in parquet.

        Args:
            contratacao: Contratacao dict

        Returns:
            numeroControlePNCP string or None if not found

        Example:
            >>> contratacao = {'numeroControlePNCP': '07811946000187-1-000001/2024'}
            >>> PNCPDetailsIngestionService.extract_key_from_contratacao(contratacao)
            '07811946000187-1-000001/2024'
        """
        key = contratacao.get("numeroControlePNCP")
        if key and isinstance(key, str) and len(key) > 0:
            return key
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
