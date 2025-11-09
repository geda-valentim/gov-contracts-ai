"""
State Management Service - Framework-agnostic state tracking.

Handles incremental ingestion state for deduplication across executions.
No Airflow dependencies - pure Python business logic.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class StateManager:
    """
    Service for managing incremental ingestion state.

    Tracks processed record IDs to enable incremental ingestion
    and avoid duplicate processing across multiple executions.

    State is persisted in storage (MinIO/S3) with one file per day.
    """

    def __init__(self, storage_client=None):
        """
        Initialize state manager.

        Args:
            storage_client: Storage client instance (MinIOClient or S3StorageClient)
                           If None, will be lazy-loaded when needed
        """
        self._storage_client = storage_client
        self._state_cache: Dict[str, Dict] = {}

    @property
    def storage_client(self):
        """Lazy-load storage client."""
        if self._storage_client is None:
            from backend.app.core.storage_client import get_storage_client

            self._storage_client = get_storage_client()
        return self._storage_client

    def get_state_key(self, source: str, date: datetime) -> str:
        """
        Generate S3 key for state file.

        Args:
            source: Data source name (e.g., 'pncp')
            date: Date for state file

        Returns:
            S3 key for state file

        Example:
            >>> manager = StateManager()
            >>> key = manager.get_state_key('pncp', datetime(2025, 10, 22))
            >>> print(key)
            'pncp/_state/year=2025/month=10/day=22/state_20251022.json'
        """
        state_key = (
            f"{source}/_state/year={date.year}/month={date.month:02d}/"
            f"day={date.day:02d}/state_{date.strftime('%Y%m%d')}.json"
        )
        return state_key

    def load_state(self, source: str, date: datetime) -> Dict[str, Any]:
        """
        Load state file for given date.

        Args:
            source: Data source name
            date: Date for state file

        Returns:
            State dict with:
                - date: Date string (YYYY-MM-DD)
                - processed_ids: List of processed record IDs
                - last_execution: ISO timestamp of last execution
                - total_processed: Total count of processed records
                - executions: List of execution metadata

        Example:
            >>> manager = StateManager()
            >>> state = manager.load_state('pncp', datetime(2025, 10, 22))
            >>> print(state['total_processed'])
            3
        """
        state_key = self.get_state_key(source, date)
        cache_key = f"{source}_{date.strftime('%Y%m%d')}"

        # Check cache first
        if cache_key in self._state_cache:
            logger.debug(f"State loaded from cache: {cache_key}")
            return self._state_cache[cache_key]

        try:
            # Try to read existing state file
            state_data = self.storage_client.read_json_from_s3(
                bucket=self.storage_client.BUCKET_BRONZE, key=state_key
            )

            logger.info(
                f"Loaded state for {source} {date.strftime('%Y-%m-%d')}: "
                f"{len(state_data.get('processed_ids', []))} processed IDs"
            )

            # Cache the state
            self._state_cache[cache_key] = state_data
            return state_data

        except Exception as e:
            # State file doesn't exist or error reading - create new state
            logger.info(
                f"No existing state for {source} {date.strftime('%Y-%m-%d')}, "
                f"creating new state (reason: {e})"
            )

            new_state = self._create_empty_state(date)
            self._state_cache[cache_key] = new_state
            return new_state

    def save_state(
        self, source: str, date: datetime, state_data: Dict[str, Any]
    ) -> str:
        """
        Save state file to storage.

        Args:
            source: Data source name
            date: Date for state file
            state_data: State dict to save

        Returns:
            S3 key where state was saved

        Example:
            >>> manager = StateManager()
            >>> state = {
            ...     'date': '2025-10-22',
            ...     'processed_ids': ['001', '002'],
            ...     'last_execution': '2025-10-22T12:00:00Z',
            ...     'total_processed': 2
            ... }
            >>> key = manager.save_state('pncp', datetime(2025, 10, 22), state)
        """
        state_key = self.get_state_key(source, date)

        # Validate state structure
        required_fields = ["date", "processed_ids", "last_execution", "total_processed"]
        for field in required_fields:
            if field not in state_data:
                raise ValueError(f"State data missing required field: {field}")

        # Write to storage
        self.storage_client.write_json_to_s3(
            bucket=self.storage_client.BUCKET_BRONZE, key=state_key, data=state_data
        )

        # Update cache
        cache_key = f"{source}_{date.strftime('%Y%m%d')}"
        self._state_cache[cache_key] = state_data

        logger.info(
            f"Saved state for {source} {date.strftime('%Y-%m-%d')}: "
            f"{state_data['total_processed']} total processed IDs"
        )

        return state_key

    def update_state(
        self,
        source: str,
        date: datetime,
        new_ids: List[str],
        execution_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Update state with new processed IDs.

        Args:
            source: Data source name
            date: Date for state file
            new_ids: List of new record IDs to add
            execution_metadata: Optional metadata about this execution

        Returns:
            Updated state dict

        Example:
            >>> manager = StateManager()
            >>> updated = manager.update_state(
            ...     'pncp',
            ...     datetime(2025, 10, 22),
            ...     ['003', '004'],
            ...     {'new_records': 2, 'duplicates_filtered': 0}
            ... )
        """
        # Load current state
        state = self.load_state(source, date)

        # Get existing processed IDs as set for faster lookup
        processed_ids_set = set(state.get("processed_ids", []))

        # Add new IDs
        original_count = len(processed_ids_set)
        processed_ids_set.update(new_ids)
        actually_new = len(processed_ids_set) - original_count

        logger.info(
            f"Updating state: {len(new_ids)} IDs provided, "
            f"{actually_new} actually new (avoiding duplicates)"
        )

        # Update state
        state["processed_ids"] = sorted(list(processed_ids_set))
        state["last_execution"] = datetime.now().isoformat()
        state["total_processed"] = len(processed_ids_set)

        # Add execution metadata
        if "executions" not in state:
            state["executions"] = []

        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "new_records": actually_new,
            **(execution_metadata or {}),
        }
        state["executions"].append(execution_record)

        # Save updated state
        self.save_state(source, date, state)

        return state

    def get_processed_ids(self, source: str, date: datetime) -> Set[str]:
        """
        Get set of processed IDs for given date.

        Args:
            source: Data source name
            date: Date to check

        Returns:
            Set of processed record IDs

        Example:
            >>> manager = StateManager()
            >>> ids = manager.get_processed_ids('pncp', datetime(2025, 10, 22))
            >>> '001' in ids
            True
        """
        state = self.load_state(source, date)
        return set(state.get("processed_ids", []))

    def filter_new_records(
        self, source: str, date: datetime, records: List[Dict], id_field: str
    ) -> tuple[List[Dict], Dict[str, int]]:
        """
        Filter records to only include new (not previously processed) ones.

        Args:
            source: Data source name
            date: Date for state file
            records: List of raw records
            id_field: Field name containing unique ID

        Returns:
            Tuple of (filtered_records, stats_dict)
            - filtered_records: List of new records only
            - stats_dict: Statistics about filtering
                - total_input: Total records provided
                - already_processed: Count of duplicates filtered
                - new_records: Count of new records
                - filter_rate: Percentage filtered

        Example:
            >>> manager = StateManager()
            >>> records = [
            ...     {'numeroControlePNCP': '001'},
            ...     {'numeroControlePNCP': '002'},  # Already processed
            ...     {'numeroControlePNCP': '003'},
            ... ]
            >>> new_records, stats = manager.filter_new_records(
            ...     'pncp', datetime(2025, 10, 22), records, 'numeroControlePNCP'
            ... )
            >>> print(f"New: {stats['new_records']}, Filtered: {stats['already_processed']}")
        """
        if not records:
            logger.info("No records to filter")
            return [], {
                "total_input": 0,
                "already_processed": 0,
                "new_records": 0,
                "filter_rate": 0,
            }

        # Load processed IDs
        processed_ids = self.get_processed_ids(source, date)

        # Filter records
        new_records = []
        for record in records:
            record_id = record.get(id_field)

            if not record_id:
                logger.warning(f"Record missing {id_field} field, skipping")
                continue

            if record_id not in processed_ids:
                new_records.append(record)

        # Calculate statistics
        total_input = len(records)
        already_processed = total_input - len(new_records)
        new_count = len(new_records)
        filter_rate = (already_processed / total_input * 100) if total_input > 0 else 0

        stats = {
            "total_input": total_input,
            "already_processed": already_processed,
            "new_records": new_count,
            "filter_rate": round(filter_rate, 2),
        }

        logger.info(
            f"Filtered records: {total_input} input → {new_count} new "
            f"({already_processed} already processed, {filter_rate:.1f}% filtered)"
        )

        return new_records, stats

    def _create_empty_state(self, date: datetime) -> Dict[str, Any]:
        """
        Create empty state structure for a new day.

        Args:
            date: Date for state file

        Returns:
            Empty state dict
        """
        return {
            "date": date.strftime("%Y-%m-%d"),
            "processed_ids": [],
            "last_execution": None,
            "total_processed": 0,
            "executions": [],
            "created_at": datetime.now().isoformat(),
        }

    def get_state_summary(self, source: str, date: datetime) -> Dict[str, Any]:
        """
        Get summary of state for given date.

        Args:
            source: Data source name
            date: Date to check

        Returns:
            Summary dict with key metrics

        Example:
            >>> manager = StateManager()
            >>> summary = manager.get_state_summary('pncp', datetime(2025, 10, 22))
            >>> print(f"Total executions: {summary['total_executions']}")
        """
        state = self.load_state(source, date)

        executions = state.get("executions", [])
        total_new_records = sum(e.get("new_records", 0) for e in executions)

        return {
            "date": state.get("date"),
            "total_processed": state.get("total_processed", 0),
            "total_executions": len(executions),
            "last_execution": state.get("last_execution"),
            "total_new_across_executions": total_new_records,
            "first_execution": executions[0]["timestamp"] if executions else None,
        }

    def clear_cache(self):
        """Clear internal state cache."""
        self._state_cache.clear()
        logger.info("State cache cleared")

    def get_details_state_key(
        self, source: str, date: datetime, detail_type: str
    ) -> str:
        """
        Generate S3 key for granular details state file.

        Args:
            source: Data source name (e.g., 'pncp_details')
            date: Date for state file
            detail_type: Type of detail ('itens' or 'arquivos')

        Returns:
            S3 key for state file

        Example:
            >>> manager = StateManager()
            >>> key = manager.get_details_state_key('pncp_details', datetime(2025, 10, 22), 'itens')
            >>> print(key)
            'pncp_details/_state/itens/year=2025/month=10/day=22/state_20251022.json'
        """
        state_key = (
            f"{source}/_state/{detail_type}/year={date.year}/month={date.month:02d}/"
            f"day={date.day:02d}/state_{date.strftime('%Y%m%d')}.json"
        )
        return state_key

    def filter_new_details(
        self,
        source: str,
        date: datetime,
        contratacoes: List[Dict],
        detail_type: str,
        key_extractor_fn,
    ) -> tuple[List[Dict], Dict[str, int]]:
        """
        Filter contratacoes to only include those not yet processed for specific detail type.

        This enables granular state management where itens and arquivos can be
        processed independently.

        Args:
            source: Data source name (e.g., 'pncp_details')
            date: Date for state file
            contratacoes: List of contratacao dicts
            detail_type: Type of detail ('itens' or 'arquivos')
            key_extractor_fn: Function to extract composite key from contratacao

        Returns:
            Tuple of (filtered_contratacoes, stats_dict)

        Example:
            >>> manager = StateManager()
            >>> from backend.app.services.ingestion.pncp_details import PNCPDetailsIngestionService
            >>> contratacoes = [...]
            >>> new_contratacoes, stats = manager.filter_new_details(
            ...     'pncp_details',
            ...     datetime(2025, 10, 22),
            ...     contratacoes,
            ...     'itens',
            ...     PNCPDetailsIngestionService.extract_key_from_contratacao
            ... )
        """
        if not contratacoes:
            logger.info("No contratacoes to filter")
            return [], {
                "total_input": 0,
                "already_processed": 0,
                "new_records": 0,
                "filter_rate": 0,
            }

        # Load processed keys for this detail type
        state_key = self.get_details_state_key(source, date, detail_type)

        # Try to load existing state
        try:
            state_data = self.storage_client.read_json_from_s3(
                bucket=self.storage_client.BUCKET_BRONZE, key=state_key
            )
            processed_keys = set(state_data.get("processed_keys", []))
            logger.info(
                f"Loaded {detail_type} state: {len(processed_keys)} processed keys"
            )
        except Exception:
            # No state file exists yet
            processed_keys = set()
            logger.info(f"No existing {detail_type} state, starting fresh")

        # Filter contratacoes
        new_contratacoes = []
        for contratacao in contratacoes:
            key = key_extractor_fn(contratacao)

            if not key:
                logger.warning("Could not extract key from contratacao, skipping")
                continue

            if key not in processed_keys:
                new_contratacoes.append(contratacao)

        # Calculate statistics
        total_input = len(contratacoes)
        already_processed = total_input - len(new_contratacoes)
        new_count = len(new_contratacoes)
        filter_rate = (already_processed / total_input * 100) if total_input > 0 else 0

        stats = {
            "total_input": total_input,
            "already_processed": already_processed,
            "new_records": new_count,
            "filter_rate": round(filter_rate, 2),
        }

        logger.info(
            f"Filtered {detail_type}: {total_input} input → {new_count} new "
            f"({already_processed} already processed, {filter_rate:.1f}% filtered)"
        )

        return new_contratacoes, stats

    def update_details_state(
        self,
        source: str,
        date: datetime,
        detail_type: str,
        new_keys: List[str],
        execution_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Update granular details state with new processed keys.

        Args:
            source: Data source name (e.g., 'pncp_details')
            date: Date for state file
            detail_type: Type of detail ('itens' or 'arquivos')
            new_keys: List of new composite keys to add
            execution_metadata: Optional metadata about this execution

        Returns:
            Updated state dict

        Example:
            >>> manager = StateManager()
            >>> updated = manager.update_details_state(
            ...     'pncp_details',
            ...     datetime(2025, 10, 22),
            ...     'itens',
            ...     ['83102277000152|2025|423', '12345678000190|2025|424'],
            ...     {'new_records': 2, 'total_itens': 45}
            ... )
        """
        state_key = self.get_details_state_key(source, date, detail_type)
        cache_key = f"{source}_{detail_type}_{date.strftime('%Y%m%d')}"

        # Try to load existing state
        try:
            state_data = self.storage_client.read_json_from_s3(
                bucket=self.storage_client.BUCKET_BRONZE, key=state_key
            )
            logger.info(f"Loaded existing {detail_type} state for update")
        except Exception:
            # Create new state
            state_data = {
                "date": date.strftime("%Y-%m-%d"),
                "detail_type": detail_type,
                "processed_keys": [],
                "last_execution": None,
                "total_processed": 0,
                "executions": [],
                "created_at": datetime.now().isoformat(),
            }
            logger.info(f"Created new {detail_type} state")

        # Get existing processed keys as set
        processed_keys_set = set(state_data.get("processed_keys", []))

        # Add new keys
        original_count = len(processed_keys_set)
        processed_keys_set.update(new_keys)
        actually_new = len(processed_keys_set) - original_count

        logger.info(
            f"Updating {detail_type} state: {len(new_keys)} keys provided, "
            f"{actually_new} actually new"
        )

        # Update state (no need to sort - order doesn't matter for lookups)
        state_data["processed_keys"] = list(processed_keys_set)
        state_data["last_execution"] = datetime.now().isoformat()
        state_data["total_processed"] = len(processed_keys_set)

        # Add execution metadata
        if "executions" not in state_data:
            state_data["executions"] = []

        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "new_records": actually_new,
            **(execution_metadata or {}),
        }
        state_data["executions"].append(execution_record)

        # Save updated state
        self.storage_client.write_json_to_s3(
            bucket=self.storage_client.BUCKET_BRONZE, key=state_key, data=state_data
        )

        # Update cache
        self._state_cache[cache_key] = state_data

        logger.info(
            f"Saved {detail_type} state: {state_data['total_processed']} total processed keys"
        )

        return state_data


# Standalone execution for testing
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="State Management Service")
    parser.add_argument("--source", default="pncp", help="Data source name")
    parser.add_argument("--date", help="Date (YYYYMMDD format)")
    parser.add_argument(
        "--action",
        choices=["load", "summary", "filter"],
        default="summary",
        help="Action to perform",
    )

    args = parser.parse_args()

    # Parse date
    if args.date:
        date = datetime.strptime(args.date, "%Y%m%d")
    else:
        date = datetime.now()

    # Initialize manager
    manager = StateManager()

    # Perform action
    if args.action == "load":
        state = manager.load_state(args.source, date)
        print(json.dumps(state, indent=2))

    elif args.action == "summary":
        summary = manager.get_state_summary(args.source, date)
        print("\n" + "=" * 60)
        print(f"STATE SUMMARY - {args.source.upper()}")
        print("=" * 60)
        print(f"Date: {summary['date']}")
        print(f"Total processed: {summary['total_processed']}")
        print(f"Total executions: {summary['total_executions']}")
        print(f"Last execution: {summary['last_execution']}")
        print(f"First execution: {summary['first_execution']}")
        print("=" * 60)

    elif args.action == "filter":
        # Example filtering
        test_records = [
            {"numeroControlePNCP": "001-test"},
            {"numeroControlePNCP": "002-test"},
            {"numeroControlePNCP": "003-test"},
        ]

        new_records, stats = manager.filter_new_records(
            args.source, date, test_records, "numeroControlePNCP"
        )

        print("\n" + "=" * 60)
        print("FILTER TEST")
        print("=" * 60)
        print(f"Input records: {stats['total_input']}")
        print(f"New records: {stats['new_records']}")
        print(f"Already processed: {stats['already_processed']}")
        print(f"Filter rate: {stats['filter_rate']}%")
        print("=" * 60)
