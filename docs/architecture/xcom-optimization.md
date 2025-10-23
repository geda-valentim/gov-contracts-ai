# XCom Optimization: S3 Temp Storage

## Problem

Airflow XCom stores data **directly in the Airflow database** (PostgreSQL by default), not in external storage. When passing large datasets between tasks via XCom, this causes:

1. **Database bloat** - Each DAG run adds megabytes to the database
2. **Performance degradation** - Large serialization/deserialization overhead
3. **Memory issues** - Data loaded into scheduler and worker memory
4. **Size limits** - XCom typically has 1-10MB limits depending on backend

### Example (Before Optimization)

```python
def fetch_pncp_data(**context):
    result = service.fetch_hourly_incremental(...)

    # ❌ PROBLEM: Pushing 5,000 records (~5MB) to XCom
    context["task_instance"].xcom_push(key="fetched_data", value=result["data"])
    return result["metadata"]

def transform_data(**context):
    # ❌ PROBLEM: Pulling 5MB from Airflow database
    raw_data = task_instance.xcom_pull(task_ids="fetch_pncp_data", key="fetched_data")
    # ... process data
```

**Impact per DAG run:**
- `fetch_pncp_data`: ~5MB in XCom
- `transform_data`: ~5MB in XCom (transformed DataFrame)
- Total: **~10MB per run** in Airflow database

**Daily impact** (hourly DAG):
- 24 runs/day × 10MB = **240MB/day**
- 30 days = **7.2GB/month**

## Solution: S3 Temp Storage

Instead of passing data through XCom, we:
1. Store large datasets in **S3/MinIO temp storage**
2. Pass only **S3 references** (~100 bytes) through XCom
3. Clean up temp files after DAG completion

### Implementation

#### 1. Storage Client Methods

Added three methods to `StorageClient`:

```python
# backend/app/core/storage_client.py

def upload_temp(
    data: Union[pd.DataFrame, Dict, List[Dict]],
    execution_id: str,
    stage: str,
    format: str = "parquet",
) -> str:
    """
    Upload temporary data for inter-task communication.

    Returns S3 key like: "_temp/20251023_120000/raw.parquet"
    """

def read_temp(bucket: str, key: str) -> Union[pd.DataFrame, Dict, List[Dict]]:
    """Read temporary data from storage."""

def cleanup_temp(execution_id: str, bucket: Optional[str] = None) -> int:
    """Clean up temporary files for a specific execution."""
```

#### 2. Refactored DAG Tasks

**Fetch Task** (saves to temp storage):

```python
def fetch_pncp_data(**context) -> dict:
    execution_date = context.get("logical_date")
    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id  # e.g., "manual__2025-10-23T12:00:00+00:00"

    # Fetch data from API
    service = PNCPIngestionService()
    result = service.fetch_hourly_incremental(...)

    # ✅ SOLUTION: Save data to temp storage instead of XCom
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],  # Large data goes to S3
        execution_id=execution_id,
        stage="raw",
        format="parquet",
    )
    # Result: "_temp/manual__2025-10-23T12:00:00+00:00/raw.parquet"

    # ✅ XCom only stores lightweight metadata + S3 reference
    return {
        "temp_key": temp_key,  # ~100 bytes
        "metadata": result["metadata"],  # ~200 bytes
        "record_count": len(result["data"]),  # ~20 bytes
    }
    # Total XCom size: ~320 bytes (vs 5MB before)
```

**Transform Task** (reads from temp storage):

```python
def transform_data(**context) -> dict:
    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id

    # ✅ Get S3 reference from XCom (lightweight ~320 bytes)
    fetch_result = task_instance.xcom_pull(task_ids="fetch_pncp_data")

    # ✅ Read actual data from temp storage (not from XCom)
    storage = get_storage_client()
    raw_df = storage.read_temp(
        bucket=storage.BUCKET_BRONZE,
        key=fetch_result["temp_key"]
    )

    # Process data...
    df = service.to_dataframe(...)

    # ✅ Save transformed data to temp storage
    transformed_key = storage.upload_temp(
        data=df,
        execution_id=execution_id,
        stage="transformed",
        format="parquet"
    )

    # ✅ XCom only stores references
    return {
        "temp_key": transformed_key,  # ~100 bytes
        "record_count": len(df),
        "validation": validation_report,
        "filter_stats": filter_stats,
    }
```

**Upload Task** (reads from temp storage):

```python
def upload_to_bronze(**context) -> dict:
    # ✅ Get S3 reference from XCom (lightweight)
    transform_result = task_instance.xcom_pull(task_ids="transform_data")

    # ✅ Read DataFrame from temp storage
    storage = get_storage_client()
    df = storage.read_temp(
        bucket=storage.BUCKET_BRONZE,
        key=transform_result["temp_key"]
    )

    # Upload to final Bronze location
    s3_key = storage.upload_to_bronze(...)

    return {
        "uploaded": True,
        "s3_key": s3_key,
        "record_count": len(df),
    }
```

**Cleanup Task** (runs always, even on failure):

```python
def cleanup_temp_files(**context) -> dict:
    """
    Clean up temporary files.
    Runs with trigger_rule="all_done" to execute even if previous tasks fail.
    """
    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id

    storage = get_storage_client()
    deleted = storage.cleanup_temp(execution_id=execution_id)

    print(f"🧹 Cleaned up {deleted} temporary files")

    return {"deleted_files": deleted}


# In DAG definition
task_cleanup = PythonOperator(
    task_id="cleanup_temp_files",
    python_callable=cleanup_temp_files,
    trigger_rule="all_done",  # Run regardless of upstream success/failure
)

# Dependencies
task_fetch >> task_transform >> task_upload >> task_validate >> task_cleanup
```

## Results

### Before Optimization

**Per DAG run:**
- XCom size: ~10MB (raw data + transformed DataFrame)
- Airflow DB growth: ~10MB per run
- Memory usage: High (data in scheduler/worker memory)

**Monthly impact (hourly DAG):**
- 24 runs/day × 30 days = 720 runs
- 720 runs × 10MB = **7.2GB/month** in Airflow database

### After Optimization

**Per DAG run:**
- XCom size: ~1KB (only references and metadata)
- Temp storage: ~5MB (cleaned up after completion)
- Airflow DB growth: **~1KB per run** (99.99% reduction)
- Memory usage: Low (data stays in S3)

**Monthly impact:**
- 720 runs × 1KB = **720KB/month** in Airflow database
- **Reduction: 7.2GB → 720KB = 99.99% smaller**

### Performance Benefits

1. **Database stays lightweight**
   - No bloat over time
   - Fast queries and UI
   - Easier backups

2. **Better resource usage**
   - Less memory consumption
   - Faster serialization
   - No XCom size limits

3. **Scalability**
   - Can handle datasets of any size
   - No risk of hitting database limits
   - Temp storage auto-cleaned

4. **Reliability**
   - Cleanup runs even on failure
   - Temp files have timestamps for debugging
   - Clear separation of concerns

## Temp Storage Structure

```
lh-bronze/
├── pncp/                          # Final Bronze data
│   └── year=2025/month=10/day=23/
│       └── pncp_*.parquet
└── _temp/                         # Temporary inter-task data
    └── manual__2025-10-23T12:00:00+00:00/  # Execution ID
        ├── raw.parquet            # From fetch task
        └── transformed.parquet    # From transform task
```

**Cleanup:**
- Runs after DAG completion (success or failure)
- Deletes entire `_temp/{execution_id}/` folder
- Triggered by `trigger_rule="all_done"`

## Migration Checklist

If refactoring other DAGs to use this pattern:

- [ ] Add `execution_id = dag_run.run_id` extraction
- [ ] Replace `xcom_push(value=data)` with `storage.upload_temp()`
- [ ] Replace `xcom_pull()` data reading with `storage.read_temp()`
- [ ] Extract metadata from returned dicts instead of separate XCom keys
- [ ] Add `cleanup_temp_files` task with `trigger_rule="all_done"`
- [ ] Update task dependencies to include cleanup at the end
- [ ] Test with real data to verify temp files are created/cleaned

## Monitoring

**Metrics to track:**
- XCom table size in Airflow database
- Temp storage usage (should be near zero most of the time)
- Cleanup task success rate
- Average temp file lifetime

**Alerts:**
- If `_temp/` folder size > 1GB (indicates cleanup failures)
- If XCom table grows > 100MB (indicates some DAG not using temp storage)
- If cleanup task fails repeatedly

## References

- [Airflow XCom Documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html)
- [Custom XCom Backends](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/xcoms.html#custom-xcom-backends)
- Backend implementation: `backend/app/core/storage_client.py`
- Refactored DAGs:
  - `airflow/dags/bronze/pncp/hourly_ingestion.py`
  - `airflow/dags/bronze/pncp/daily_ingestion.py`
  - `airflow/dags/bronze/pncp/backfill.py`
