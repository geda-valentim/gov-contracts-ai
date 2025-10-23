"""
Data Transformation Service - Framework-agnostic business logic.

Handles transformation, validation, and deduplication of raw PNCP data.
No Airflow dependencies - pure Python business logic.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger(__name__)


class DataTransformationService:
    """
    Service for transforming raw PNCP data.

    Pure Python class with no framework dependencies.
    Handles deduplication, validation, and DataFrame conversion.
    """

    def __init__(self):
        """Initialize data transformation service."""
        self.seen_ids: Set[str] = set()

    def deduplicate_records(
        self, records: List[Dict], id_field: str = "numeroControlePNCP"
    ) -> List[Dict]:
        """
        Remove duplicate records based on ID field.

        Args:
            records: List of raw records
            id_field: Field name to use for deduplication

        Returns:
            List of deduplicated records

        Example:
            >>> service = DataTransformationService()
            >>> records = [
            ...     {"numeroControlePNCP": "001", "valor": 1000},
            ...     {"numeroControlePNCP": "001", "valor": 1000},  # duplicate
            ...     {"numeroControlePNCP": "002", "valor": 2000},
            ... ]
            >>> deduplicated = service.deduplicate_records(records)
            >>> len(deduplicated)
            2
        """
        if not records:
            return []

        unique_records = []
        seen_in_batch: Set[str] = set()

        for record in records:
            record_id = record.get(id_field)

            if not record_id:
                logger.warning(f"Record missing {id_field} field, skipping")
                continue

            # Check both batch-level and instance-level deduplication
            if record_id not in seen_in_batch and record_id not in self.seen_ids:
                unique_records.append(record)
                seen_in_batch.add(record_id)
                self.seen_ids.add(record_id)
            else:
                logger.debug(f"Duplicate record found: {record_id}")

        duplicates_removed = len(records) - len(unique_records)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate records")

        return unique_records

    def to_dataframe(
        self, records: List[Dict], deduplicate: bool = True
    ) -> pd.DataFrame:
        """
        Convert raw records to pandas DataFrame.

        Args:
            records: List of raw records
            deduplicate: Whether to deduplicate before conversion

        Returns:
            pandas DataFrame

        Example:
            >>> service = DataTransformationService()
            >>> records = [{"id": "001", "valor": 1000}]
            >>> df = service.to_dataframe(records)
            >>> isinstance(df, pd.DataFrame)
            True
        """
        if not records:
            logger.warning("No records to convert to DataFrame")
            return pd.DataFrame()

        if deduplicate:
            records = self.deduplicate_records(records)

        df = pd.DataFrame(records)
        logger.info(f"Created DataFrame: {len(df)} rows, {len(df.columns)} columns")

        return df

    def validate_records(self, records: List[Dict]) -> Dict[str, Any]:
        """
        Validate raw records and return validation report.

        Args:
            records: List of raw records

        Returns:
            Dict with validation results:
                - total_records: Total count
                - valid_records: Count of valid records
                - invalid_records: Count of invalid records
                - validation_errors: List of error messages

        Example:
            >>> service = DataTransformationService()
            >>> records = [{"numeroControlePNCP": "001"}]
            >>> report = service.validate_records(records)
            >>> report['total_records']
            1
        """
        validation_errors = []
        valid_count = 0
        invalid_count = 0

        required_fields = ["numeroControlePNCP"]

        for idx, record in enumerate(records):
            is_valid = True

            # Check required fields
            for field in required_fields:
                if field not in record or not record[field]:
                    validation_errors.append(
                        f"Record {idx}: Missing required field '{field}'"
                    )
                    is_valid = False

            # Check data types
            if "dataPublicacaoPncp" in record:
                try:
                    # Validate date format if present
                    if record["dataPublicacaoPncp"]:
                        datetime.fromisoformat(
                            record["dataPublicacaoPncp"].replace("Z", "+00:00")
                        )
                except (ValueError, AttributeError):
                    validation_errors.append(
                        f"Record {idx}: Invalid date format in 'dataPublicacaoPncp'"
                    )
                    is_valid = False

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        validation_report = {
            "total_records": len(records),
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "validation_errors": validation_errors[:10],  # Limit to first 10 errors
            "validation_timestamp": datetime.now().isoformat(),
        }

        if invalid_count > 0:
            logger.warning(
                f"Validation found {invalid_count} invalid records out of {len(records)}"
            )
        else:
            logger.info(f"All {valid_count} records passed validation")

        return validation_report

    def add_metadata_columns(
        self, df: pd.DataFrame, metadata: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Add metadata columns to DataFrame.

        Args:
            df: Input DataFrame
            metadata: Optional metadata dict to add as columns

        Returns:
            DataFrame with metadata columns

        Example:
            >>> service = DataTransformationService()
            >>> df = pd.DataFrame([{"id": "001"}])
            >>> metadata = {"source": "pncp", "layer": "bronze"}
            >>> df_with_meta = service.add_metadata_columns(df, metadata)
            >>> "ingestion_timestamp" in df_with_meta.columns
            True
        """
        if df.empty:
            return df

        df = df.copy()

        # Add ingestion timestamp
        df["ingestion_timestamp"] = datetime.now().isoformat()

        # Add provided metadata as columns
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (list, dict, set, tuple)):
                    try:
                        serialized_value = json.dumps(value, default=str)
                    except TypeError:
                        serialized_value = str(value)
                elif isinstance(value, datetime):
                    serialized_value = value.isoformat()
                else:
                    serialized_value = value

                df[f"meta_{key}"] = serialized_value

        logger.info(
            f"Added metadata columns: {list(metadata.keys()) if metadata else ['ingestion_timestamp']}"
        )

        return df

    def filter_by_date_range(
        self,
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        date_column: str = "dataPublicacaoPncp",
    ) -> pd.DataFrame:
        """
        Filter DataFrame by date range.

        Args:
            df: Input DataFrame
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            date_column: Column name containing dates

        Returns:
            Filtered DataFrame

        Example:
            >>> service = DataTransformationService()
            >>> df = pd.DataFrame([
            ...     {"id": "001", "dataPublicacaoPncp": "2024-10-22T10:00:00Z"}
            ... ])
            >>> filtered = service.filter_by_date_range(df, "2024-10-22", "2024-10-22")
            >>> len(filtered)
            1
        """
        if df.empty or date_column not in df.columns:
            return df

        df = df.copy()

        # Convert date column to datetime
        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

        # Filter by date range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) + pd.Timedelta(days=1)  # Include end date

        df_filtered = df[(df[date_column] >= start) & (df[date_column] < end)]

        logger.info(
            f"Filtered by date range {start_date} to {end_date}: "
            f"{len(df)} → {len(df_filtered)} records"
        )

        return df_filtered

    def get_transformation_summary(
        self, original_count: int, final_count: int, validation_report: Dict
    ) -> Dict[str, Any]:
        """
        Generate transformation summary.

        Args:
            original_count: Original record count
            final_count: Final record count after transformations
            validation_report: Validation report dict

        Returns:
            Transformation summary dict
        """
        return {
            "original_count": original_count,
            "final_count": final_count,
            "records_removed": original_count - final_count,
            "removal_rate": (
                (original_count - final_count) / original_count * 100
                if original_count > 0
                else 0
            ),
            "validation_report": validation_report,
            "transformation_timestamp": datetime.now().isoformat(),
        }

    def reset_seen_ids(self):
        """Reset the internal deduplication cache."""
        self.seen_ids.clear()
        logger.info("Deduplication cache reset")


# Standalone execution
if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Data Transformation Service")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", help="Output CSV file path (optional)")
    parser.add_argument(
        "--no-deduplicate", action="store_true", help="Skip deduplication"
    )

    args = parser.parse_args()

    # Load data
    logger.info(f"Loading data from {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "data" in data:
        records = data["data"]
    else:
        records = data

    # Initialize service
    service = DataTransformationService()

    # Validate
    validation_report = service.validate_records(records)
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(f"Total records: {validation_report['total_records']}")
    print(f"Valid records: {validation_report['valid_records']}")
    print(f"Invalid records: {validation_report['invalid_records']}")
    if validation_report["validation_errors"]:
        print("\nFirst errors:")
        for error in validation_report["validation_errors"][:5]:
            print(f"  - {error}")

    # Transform
    df = service.to_dataframe(records, deduplicate=not args.no_deduplicate)

    print("\n" + "=" * 60)
    print("TRANSFORMATION RESULTS")
    print("=" * 60)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Save if requested
    if args.output:
        df.to_csv(args.output, index=False)
        logger.info(f"Saved to {args.output}")

    print("=" * 60)
