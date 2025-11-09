# Timezone Handling Guide

## Overview

This document explains how dates and timezones are handled throughout the Gov Contracts AI codebase to ensure consistency between Airflow DAGs, backend services, and data partitioning.

## The Problem

We had several timezone-related issues:

1. **Mixed timezones**: Airflow uses UTC internally, but business logic operates in Brazil (America/Sao_Paulo)
2. **Naive datetimes**: Using `datetime.now()` without timezone resulted in inconsistent partitioning
3. **Execution date confusion**: Mixing `execution_date` and `logical_date` without proper conversion
4. **File partitioning mismatches**: Data saved with UTC dates but queried with local dates

## The Solution

### 1. Standardized Timezone: America/Sao_Paulo

All business logic, data partitioning, and file timestamps use **America/Sao_Paulo** timezone.

**Why?**
- Aligns with Brazilian government procurement schedules
- Ensures date partitions match business dates (not UTC dates)
- Prevents confusion when data spans midnight UTC but not local time

### 2. Pendulum for Date Handling

We use [Pendulum](https://pendulum.eustace.io/) for all date operations.

**Why Pendulum?**
- Airflow internally uses Pendulum for `logical_date`
- Better timezone handling than stdlib `datetime`
- Consistent API across Python and Airflow
- Handles DST (Daylight Saving Time) correctly

**Example:**
```python
import pendulum

# Create timezone-aware datetime
dt = pendulum.datetime(2025, 10, 23, 15, 30, tz="America/Sao_Paulo")

# Get current time in São Paulo
now = pendulum.now("America/Sao_Paulo")

# Convert UTC to São Paulo
utc_dt = pendulum.datetime(2025, 10, 23, 18, 30, tz="UTC")
sp_dt = utc_dt.in_timezone("America/Sao_Paulo")  # 15:30 -03:00

# Format dates
date_str = sp_dt.format("YYYYMMDD")  # "20251023"
```

### 3. Utility Modules

#### Backend: `backend/app/core/datetime_utils.py`

```python
from backend.app.core.datetime_utils import (
    get_now_sao_paulo,    # Current time in São Paulo
    to_sao_paulo,          # Convert any datetime to São Paulo
    format_date,           # Format as YYYYMMDD
    format_datetime,       # Format as YYYYMMDD_HHMMSS
    get_partition_path,    # Get year/month/day components
    parse_date_str,        # Parse YYYYMMDD string
)

# Usage in backend services
now = get_now_sao_paulo()
storage.upload_to_bronze(data, source="pncp", date=now)
```

#### Airflow DAGs: `airflow/dags/utils/dates.py`

```python
from utils.dates import (
    to_sao_paulo,                   # Convert to São Paulo timezone
    get_date_range_for_execution,   # Get date range from execution_date
    get_yesterday,                  # Yesterday in São Paulo
    get_last_n_days,                # Last N days in São Paulo
    get_now_sao_paulo,              # Current time in São Paulo
    format_date,                    # Format as YYYYMMDD
)

# Usage in DAG tasks
def my_task(**context):
    # Airflow passes logical_date in UTC
    execution_date = context.get("logical_date")

    # Convert to São Paulo timezone
    sp_date = to_sao_paulo(execution_date)

    # Format for API or file naming
    date_str = format_date(sp_date)  # "20251023"
```

## Usage Patterns

### Pattern 1: DAG Task with Execution Date

```python
def fetch_pncp_data(**context) -> dict:
    # Airflow 3.x: logical_date is in UTC
    execution_date = context.get("logical_date") or context.get("data_interval_start")

    # Convert to São Paulo timezone for business logic
    from utils.dates import to_sao_paulo, format_date
    sp_date = to_sao_paulo(execution_date)
    date_str = format_date(sp_date)  # "20251023"

    # Fetch data for this date
    data = api_client.fetch(date=date_str)

    # Upload with timezone-aware date
    storage.upload_to_bronze(data, source="pncp", date=sp_date)
```

### Pattern 2: Scheduled DAG with Manual Trigger

```python
with DAG(
    dag_id="bronze_pncp_daily_ingestion",
    schedule="0 2 * * *",  # Daily at 2 AM
    start_date=pendulum.datetime(2025, 10, 1, tz="America/Sao_Paulo"),  # ✅ Use Pendulum
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp"],
) as dag:
    # Tasks use logical_date from Airflow
    pass
```

### Pattern 3: Backend Service with Current Time

```python
from backend.app.core.datetime_utils import get_now_sao_paulo

class PNCPIngestionService:
    def fetch_recent_data(self):
        # Get current time in São Paulo
        now = get_now_sao_paulo()

        # Format for API
        date_str = now.format("YYYYMMDD")

        # Fetch and store with timezone-aware date
        data = self.api_client.fetch(date=date_str)
        self.storage.upload_to_bronze(data, source="pncp", date=now)
```

### Pattern 4: Backfill with Date Range

```python
def backfill_pncp_data(days_back: int = 90):
    # Use Pendulum for date range
    end_date = pendulum.now("America/Sao_Paulo")
    start_date = end_date.subtract(days=days_back)

    current_date = start_date
    while current_date <= end_date:
        # Format date for API
        date_str = current_date.format("YYYYMMDD")

        # Process this date
        data = fetch_for_date(date_str)
        storage.upload_to_bronze(data, source="pncp", date=current_date)

        # Move to next day
        current_date = current_date.add(days=1)  # ✅ Use Pendulum's add()
```

## Common Pitfalls

### ❌ DON'T: Use naive datetime.now()

```python
from datetime import datetime

# ❌ WRONG: Naive datetime (timezone-unaware)
date = datetime.now()
storage.upload_to_bronze(data, date=date)
```

**Problem:** Uses system timezone, which may be UTC in Docker containers.

### ✅ DO: Use timezone-aware Pendulum

```python
import pendulum

# ✅ CORRECT: Timezone-aware datetime
date = pendulum.now("America/Sao_Paulo")
storage.upload_to_bronze(data, date=date)
```

---

### ❌ DON'T: Mix datetime.strftime() with timedelta

```python
from datetime import datetime, timedelta

# ❌ WRONG: Naive datetime arithmetic
current_date = datetime.now()
while current_date <= end_date:
    date_str = current_date.strftime("%Y%m%d")
    # ...
    current_date += timedelta(days=1)  # Doesn't handle DST
```

**Problem:** `timedelta` doesn't respect DST transitions.

### ✅ DO: Use Pendulum's add/subtract

```python
import pendulum

# ✅ CORRECT: Pendulum handles DST correctly
current_date = pendulum.now("America/Sao_Paulo")
while current_date <= end_date:
    date_str = current_date.format("YYYYMMDD")
    # ...
    current_date = current_date.add(days=1)  # Handles DST
```

---

### ❌ DON'T: Use execution_date directly for file partitioning

```python
def my_task(**context):
    # ❌ WRONG: execution_date is in UTC
    execution_date = context["execution_date"]
    date_str = execution_date.strftime("%Y%m%d")  # UTC date!

    # This creates partitions like 2025-10-22 when local date is 2025-10-23
    storage.upload_to_bronze(data, date=execution_date)
```

### ✅ DO: Convert to São Paulo timezone first

```python
def my_task(**context):
    # ✅ CORRECT: Convert to local timezone
    from utils.dates import to_sao_paulo, format_date

    execution_date = context.get("logical_date")
    sp_date = to_sao_paulo(execution_date)
    date_str = format_date(sp_date)  # São Paulo date

    storage.upload_to_bronze(data, date=sp_date)
```

---

### ❌ DON'T: Hardcode timezone offsets

```python
from datetime import datetime, timezone, timedelta

# ❌ WRONG: Hardcoded UTC-3 (doesn't respect DST)
SP_TZ = timezone(timedelta(hours=-3))
date = datetime.now(SP_TZ)
```

**Problem:** Brazil has DST (when it does), so offset changes.

### ✅ DO: Use named timezone

```python
import pendulum

# ✅ CORRECT: Named timezone handles DST automatically
date = pendulum.now("America/Sao_Paulo")
```

## Airflow Configuration

The Airflow Docker containers are configured with São Paulo timezone:

```yaml
# infrastructure/docker/airflow/compose.yml
x-airflow-common-env: &airflow-common-env
  AIRFLOW__CORE__DEFAULT_TIMEZONE: 'America/Sao_Paulo'
  AIRFLOW__CORE__DEFAULT_UI_TIMEZONE: 'America/Sao_Paulo'
  TZ: 'America/Sao_Paulo'
```

**What this does:**
- `DEFAULT_TIMEZONE`: Airflow interprets all naive datetimes as São Paulo
- `DEFAULT_UI_TIMEZONE`: Airflow UI displays times in São Paulo
- `TZ`: System timezone for the container

## Data Partitioning

All data lakes use Hive-style partitioning with **São Paulo dates**:

```
bronze/
  pncp/
    year=2025/
      month=10/
        day=23/          # ✅ São Paulo date (not UTC)
          pncp_20251023_153045.parquet
```

**Why this matters:**
- A DAG running at 2 AM São Paulo time processes data for Oct 23
- Without timezone conversion, it would create Oct 22 partition (UTC)
- Queries expecting Oct 23 data would fail

## Testing

To verify timezone handling:

```python
import pendulum

# Test UTC to São Paulo conversion
utc_midnight = pendulum.datetime(2025, 10, 23, 0, 0, tz="UTC")
sp_time = utc_midnight.in_timezone("America/Sao_Paulo")
assert sp_time.hour == 21  # UTC 00:00 = SP 21:00 previous day
assert sp_time.day == 22   # Still Oct 22 in São Paulo

# Test formatting
date_str = sp_time.format("YYYYMMDD")
assert date_str == "20251022"  # ✅ Correct São Paulo date
```

## Migration Checklist

When adding new DAGs or backend services:

- [ ] Import `pendulum` instead of `datetime`
- [ ] Use `pendulum.now("America/Sao_Paulo")` instead of `datetime.now()`
- [ ] Convert `logical_date` to São Paulo timezone in DAG tasks
- [ ] Use `current_date.add(days=1)` instead of `current_date + timedelta(days=1)`
- [ ] Use `format("YYYYMMDD")` instead of `strftime("%Y%m%d")`
- [ ] Import datetime utilities from `backend.app.core.datetime_utils` or `utils.dates`
- [ ] Test with dates around midnight UTC to catch timezone bugs

## References

- [Pendulum Documentation](https://pendulum.eustace.io/)
- [Airflow Timezone Guide](https://airflow.apache.org/docs/apache-airflow/stable/timezone.html)
- [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html)
- [IANA Time Zone Database](https://www.iana.org/time-zones)

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Date creation | `datetime.now()` | `pendulum.now("America/Sao_Paulo")` |
| Date arithmetic | `dt + timedelta(days=1)` | `dt.add(days=1)` |
| Date formatting | `dt.strftime("%Y%m%d")` | `dt.format("YYYYMMDD")` |
| Timezone conversion | Manual offset calculation | `dt.in_timezone("America/Sao_Paulo")` |
| DAG execution_date | Use directly (UTC) | Convert with `to_sao_paulo()` |
| File partitioning | Mixed UTC/local | Always São Paulo |
| Airflow config | Default (UTC) | Configured for São Paulo |

**Key Takeaway:** Always use timezone-aware Pendulum datetimes with `America/Sao_Paulo` for all business logic and data partitioning.
