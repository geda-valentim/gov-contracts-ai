# Standalone Services Guide

This guide explains how to use the standalone services for PNCP ingestion without requiring Airflow.

## Overview

The business logic has been separated from Airflow into standalone Python services that can be executed independently. This provides:

- **Faster development**: Test logic without starting Airflow
- **Framework independence**: Services can be used with any orchestrator
- **Easier testing**: Unit tests don't need Airflow mocks
- **Better maintainability**: Clear separation of concerns

## Architecture

### Service Layer (No Airflow Dependencies)

Located in `backend/app/services/`:

1. **PNCPIngestionService** ([backend/app/services/pncp_ingestion.py](../backend/app/services/pncp_ingestion.py))
   - Fetches data from PNCP API
   - Supports hourly, daily, backfill modes
   - Can be executed as standalone script

2. **DataTransformationService** ([backend/app/services/data_transformation.py](../backend/app/services/data_transformation.py))
   - Validates records
   - Deduplicates data
   - Transforms to pandas DataFrame
   - Can be executed as standalone script

3. **StorageService** ([backend/app/services/storage.py](../backend/app/services/storage.py))
   - Uploads to Bronze/Silver/Gold layers
   - Reads from Data Lake
   - Lists objects
   - Can be executed as standalone script

### DAG Layer (Thin Airflow Wrappers)

Located in `airflow/dags/bronze/`:

- [pncp_hourly_ingestion.py](../airflow/dags/bronze/pncp_hourly_ingestion.py) - Thin wrapper for hourly ingestion
- [pncp_daily_ingestion.py](../airflow/dags/bronze/pncp_daily_ingestion.py) - Thin wrapper for daily ingestion

DAGs are now ~200 lines (vs ~300 before) and only handle:
- Extracting Airflow context
- Calling standalone services
- Managing XCom for task communication

## Usage

### 1. Standalone Python Scripts

Execute services directly without Airflow:

```bash
# Quick test (5 pages, 3 modalidades)
python scripts/run_pncp_ingestion.py --mode custom --pages 5 --modalidades 3

# Hourly ingestion (20 pages, all modalidades)
python scripts/run_pncp_ingestion.py --mode hourly

# Daily ingestion (all pages, all modalidades)
python scripts/run_pncp_ingestion.py --mode daily

# Custom date and pagination
python scripts/run_pncp_ingestion.py --mode custom --date 20241022 --pages 10

# Backfill historical data
python scripts/run_pncp_ingestion.py --mode backfill --start-date 20241001 --end-date 20241031
```

### 2. Makefile Commands

Simplified commands using Poetry:

```bash
# Quick test
make run-ingestion-test

# Hourly ingestion
make run-ingestion-hourly

# Daily ingestion
make run-ingestion-daily

# Custom with parameters
make run-ingestion-custom DATE=20241022 PAGES=10 MODALIDADES=5
```

### 3. Python API (Programmatic Usage)

Use services in your own scripts:

```python
from datetime import datetime
from backend.app.services import (
    PNCPIngestionService,
    DataTransformationService,
    StorageService,
    ALL_MODALIDADES,
)

# Fetch data
ingestion = PNCPIngestionService()
result = ingestion.fetch_hourly_incremental(
    execution_date=datetime(2024, 10, 22, 14, 0),
    num_pages=20,
    modalidades=ALL_MODALIDADES,
)

# Transform
transformation = DataTransformationService()
validation_report = transformation.validate_records(result['data'])
df = transformation.to_dataframe(result['data'], deduplicate=True)

# Store
storage = StorageService()
upload_result = storage.upload_to_bronze(
    data=result['data'],
    source='pncp',
    date=datetime(2024, 10, 22)
)

print(f"Uploaded to: {upload_result['s3_key']}")
```

### 4. Individual Service CLI

Each service can be executed standalone:

```bash
# PNCP Ingestion Service
python -m backend.app.services.pncp_ingestion \
    --mode hourly \
    --date 20241022 \
    --pages 20 \
    --modalidades 13

# Data Transformation Service
python -m backend.app.services.data_transformation \
    --input data/raw_pncp_data.json \
    --output data/transformed.csv

# Storage Service
python -m backend.app.services.storage \
    --action upload \
    --layer bronze \
    --input data/raw_pncp_data.json \
    --source pncp
```

### 5. Airflow DAGs (Production)

In production, use Airflow for scheduling:

```bash
# Trigger via Airflow UI
# http://localhost:8081

# Or via CLI
make airflow-trigger-hourly
make airflow-trigger-daily

# Or via Docker
docker compose exec airflow-webserver airflow dags trigger bronze_pncp_hourly_ingestion
```

## Service Details

### PNCPIngestionService

**Methods:**
- `fetch_hourly_incremental(execution_date, num_pages=20)` - Fetch last N pages
- `fetch_daily_complete(execution_date)` - Fetch complete day
- `fetch_backfill(start_date, end_date)` - Fetch historical range
- `fetch_by_date_range(data_inicial, data_final, num_pages=None)` - Custom fetch

**Constants:**
- `ALL_MODALIDADES` - All 13 procurement modalities
- `COMMON_MODALIDADES` - Top 3 for testing (Pregão, Dispensa, Inexigibilidade)

**Example:**
```python
service = PNCPIngestionService()
result = service.fetch_hourly_incremental(
    execution_date=datetime.now(),
    num_pages=20
)
# Returns: {"data": [...], "metadata": {...}}
```

### DataTransformationService

**Methods:**
- `validate_records(records)` - Validate required fields, data types
- `deduplicate_records(records, id_field="numeroControlePNCP")` - Remove duplicates
- `to_dataframe(records, deduplicate=True)` - Convert to pandas DataFrame
- `add_metadata_columns(df, metadata)` - Add ingestion metadata
- `filter_by_date_range(df, start_date, end_date)` - Filter by dates

**Example:**
```python
service = DataTransformationService()
validation = service.validate_records(raw_data)
df = service.to_dataframe(raw_data, deduplicate=True)
df = service.add_metadata_columns(df, {"source": "pncp"})
```

### StorageService

**Methods:**
- `upload_to_bronze(data, source, date)` - Upload raw JSON
- `upload_to_silver(df, table, date)` - Upload validated Parquet
- `upload_to_gold(df, feature_set, date)` - Upload features
- `read_from_bronze(s3_key)` - Read JSON from Bronze
- `read_from_silver(s3_key)` - Read Parquet from Silver
- `list_objects_in_layer(layer, prefix)` - List objects

**Example:**
```python
service = StorageService()
result = service.upload_to_bronze(
    data=raw_data,
    source="pncp",
    date=datetime.now()
)
# Returns: {"uploaded": True, "s3_key": "...", "record_count": 1000}
```

## Benefits

### Before (Coupled to Airflow)

```python
# DAG file - 317 lines
def fetch_pncp_data(**context):
    execution_date = context["execution_date"]
    pncp_client = get_pncp_client()

    # 150+ lines of business logic mixed with Airflow
    modalidades = [...]
    all_data = []
    for modalidade in modalidades:
        data = pncp_client.fetch_all_contratacoes_by_date(...)
        all_data.extend(data)

    context["task_instance"].xcom_push(...)  # Airflow coupling
    return metadata
```

**Problems:**
- Business logic tied to Airflow context
- Can't test without Airflow
- Hard to reuse in other contexts
- XCom coupling throughout

### After (Standalone Services)

```python
# Service file - pure Python
class PNCPIngestionService:
    def fetch_hourly_incremental(self, execution_date, num_pages):
        # Pure business logic - no Airflow
        return {"data": [...], "metadata": {...}}

# DAG file - thin wrapper (60 lines)
def fetch_pncp_data(**context):
    service = PNCPIngestionService()
    result = service.fetch_hourly_incremental(
        execution_date=context["execution_date"],
        num_pages=20
    )
    context["task_instance"].xcom_push(key="data", value=result["data"])
    return result["metadata"]
```

**Benefits:**
- ✅ Business logic is framework-independent
- ✅ Can be tested without Airflow
- ✅ Reusable in notebooks, scripts, other orchestrators
- ✅ DAGs are thin wrappers (minimal Airflow coupling)
- ✅ Faster development iteration

## Development Workflow

### Testing New Features

1. **Develop in standalone script:**
   ```bash
   python scripts/run_pncp_ingestion.py --mode custom --pages 1 --modalidades 1
   ```

2. **Test with more data:**
   ```bash
   make run-ingestion-test  # 5 pages, 3 modalidades
   ```

3. **Test in Airflow (if needed):**
   ```bash
   make airflow-test-hourly
   ```

4. **Deploy to production:**
   - Services are already deployed (no Airflow dependency)
   - DAGs automatically use the services

### Debugging

1. **Run standalone script with debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)

   from backend.app.services import PNCPIngestionService
   service = PNCPIngestionService()
   result = service.fetch_hourly_incremental(...)
   ```

2. **Use IPython for interactive testing:**
   ```bash
   cd backend
   poetry run ipython

   >>> from backend.app.services import *
   >>> service = PNCPIngestionService()
   >>> result = service.fetch_hourly_incremental(...)
   ```

3. **Test individual components:**
   ```bash
   # Test PNCP client
   python -m backend.app.services.pncp_ingestion --mode custom --pages 1

   # Test transformation
   python -m backend.app.services.data_transformation --input data.json

   # Test storage
   python -m backend.app.services.storage --action list --layer bronze
   ```

## Migration Path

### For Existing DAGs

To migrate existing DAGs to use standalone services:

1. **Extract business logic** to service class:
   ```python
   # backend/app/services/my_service.py
   class MyService:
       def process_data(self, data):
           # Move logic here
           return result
   ```

2. **Create thin wrapper** in DAG:
   ```python
   # airflow/dags/my_dag.py
   from backend.app.services import MyService

   def my_task(**context):
       service = MyService()
       result = service.process_data(...)
       context["ti"].xcom_push(...)
       return result
   ```

3. **Test standalone:**
   ```bash
   python -m backend.app.services.my_service
   ```

4. **Test in Airflow:**
   ```bash
   airflow dags test my_dag $(date +%Y-%m-%d)
   ```

## Best Practices

1. **Keep services pure:** No Airflow imports in `backend/app/services/`
2. **Return dicts:** Services should return serializable dicts, not Airflow objects
3. **Use dependency injection:** Pass clients as constructor args (e.g., `PNCPClient()`)
4. **Add CLI support:** All services should have `if __name__ == "__main__"` for standalone execution
5. **Document examples:** Add docstring examples showing standalone usage
6. **Test without Airflow:** Write unit tests that don't require Airflow

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Ensure backend is in path
export PYTHONPATH=/home/gov-contracts-ai:$PYTHONPATH

# Or use absolute imports
python -m backend.app.services.pncp_ingestion
```

### MinIO Connection

If storage fails:

```bash
# Check MinIO is running
docker compose ps minio

# Test MinIO connection
python -m backend.app.services.storage --action list --layer bronze
```

### PNCP API Rate Limits

If API calls fail:

```bash
# Test with fewer modalidades
python scripts/run_pncp_ingestion.py --mode custom --pages 1 --modalidades 1

# Or use COMMON_MODALIDADES (top 3 only)
```

## Next Steps

- [ ] Add unit tests for all services
- [ ] Create integration tests for full pipeline
- [ ] Add Jupyter notebook examples
- [ ] Document Silver and Gold layer services
- [ ] Add metrics/monitoring to services
- [ ] Create service for data quality validation

## See Also

- [QUICKSTART-AIRFLOW.md](QUICKSTART-AIRFLOW.md) - Airflow setup guide
- [how-to-run-dags-manually.md](how-to-run-dags-manually.md) - Manual DAG execution
- [airflow-dags-strategy.md](airflow-dags-strategy.md) - Ingestion strategy
- [project-structure.md](project-structure.md) - Project architecture
