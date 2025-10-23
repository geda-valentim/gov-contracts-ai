# How to Run Airflow DAGs Manually

## Prerequisites

### 1. Start All Services

```bash
# From project root
docker compose up -d

# Wait for services to be healthy (~2 minutes)
docker compose ps
```

### 2. Check Services Status

```bash
# Check if all services are running
docker compose ps

# Expected output:
# - postgres (healthy)
# - redis (healthy)
# - minio (healthy)
# - airflow-webserver (healthy)
# - airflow-scheduler (healthy)
# - airflow-worker (healthy)
```

### 3. Access Airflow UI

Open browser: **http://localhost:8081**

**Default credentials:**
- Username: `airflow`
- Password: `airflow`

---

## Method 1: Via Airflow Web UI (Easiest)

### Step 1: Navigate to DAGs Page

1. Open http://localhost:8081
2. Login with `airflow / airflow`
3. You'll see the DAGs list

### Step 2: Enable the DAG

1. Find your DAG (e.g., `bronze_pncp_hourly_ingestion`)
2. Toggle the **switch on the left** to enable it
3. DAG should turn from gray to green/active

### Step 3: Trigger Manual Run

**Option A: Quick Trigger**
1. Click the **▶️ Play button** on the right side of the DAG row
2. Click **"Trigger DAG"**
3. Click **"Trigger"** in the modal

**Option B: Trigger with Config**
1. Click the **▶️ Play button**
2. Click **"Trigger DAG w/ config"**
3. Add custom configuration (optional):
   ```json
   {
     "modalidades_count": 3,
     "test_mode": true
   }
   ```
4. Click **"Trigger"**

### Step 4: Monitor Execution

1. Click on the **DAG name** to open the detail page
2. You'll see the **Graph View** or **Grid View**
3. Watch the tasks turn from:
   - ⚪ Queued → 🟡 Running → 🟢 Success
   - Or 🔴 Failed if there's an error

### Step 5: View Logs

1. Click on a **task box** in the Graph View
2. Click **"Log"** button
3. See real-time logs of the task execution

---

## Method 2: Via Airflow CLI (Docker)

### Step 1: Access Airflow Container

```bash
# Enter the airflow-webserver container
docker compose exec airflow-webserver bash

# Or use scheduler container
docker compose exec airflow-scheduler bash
```

### Step 2: List Available DAGs

```bash
# Inside container
airflow dags list

# Expected output:
# bronze_pncp_backfill
# bronze_pncp_daily_ingestion
# bronze_pncp_hourly_ingestion
# silver_bronze_to_silver
# gold_feature_engineering
```

### Step 3: Test DAG (Dry Run)

```bash
# Test if DAG is valid (doesn't execute tasks)
airflow dags test bronze_pncp_hourly_ingestion 2024-10-22
```

### Step 4: Trigger DAG Manually

```bash
# Trigger DAG run
airflow dags trigger bronze_pncp_hourly_ingestion

# Trigger with execution date
airflow dags trigger bronze_pncp_hourly_ingestion --exec-date 2024-10-22

# Trigger with config
airflow dags trigger bronze_pncp_hourly_ingestion --conf '{"test": true}'
```

### Step 5: Check DAG Run Status

```bash
# List recent DAG runs
airflow dags list-runs -d bronze_pncp_hourly_ingestion

# Get specific run info
airflow dags show bronze_pncp_hourly_ingestion
```

### Step 6: Run Individual Task (Testing)

```bash
# Test single task without dependencies
airflow tasks test bronze_pncp_hourly_ingestion fetch_last_pages 2024-10-22

# Run task with full context
airflow tasks run bronze_pncp_hourly_ingestion fetch_last_pages 2024-10-22
```

---

## Method 3: Via Python Script (Direct Testing)

### Create Test Script

Create `test_dag.py`:

```python
"""Test DAG execution directly"""

import sys
sys.path.insert(0, '/opt/airflow')

from datetime import datetime
from airflow.models import DagBag

# Load DAG
dagbag = DagBag(dag_folder='/opt/airflow/dags/bronze')
dag = dagbag.get_dag('bronze_pncp_hourly_ingestion')

if dag:
    print(f"✅ DAG loaded: {dag.dag_id}")
    print(f"Tasks: {[task.task_id for task in dag.tasks]}")

    # Test run
    execution_date = datetime.now()
    dag.test(execution_date=execution_date)
else:
    print("❌ DAG not found or has errors")
    print(f"Import errors: {dagbag.import_errors}")
```

### Run Test Script

```bash
# Inside container
docker compose exec airflow-webserver python /opt/airflow/test_dag.py
```

---

## Method 4: Quick Test with Makefile (Recommended)

### Create Makefile Commands

Add to `/home/gov-contracts-ai/Makefile`:

```makefile
# Airflow DAG commands

.PHONY: airflow-test-hourly
airflow-test-hourly: ## Test hourly ingestion DAG
	docker compose exec airflow-webserver airflow dags test bronze_pncp_hourly_ingestion $$(date +%Y-%m-%d)

.PHONY: airflow-trigger-hourly
airflow-trigger-hourly: ## Trigger hourly ingestion DAG
	docker compose exec airflow-webserver airflow dags trigger bronze_pncp_hourly_ingestion

.PHONY: airflow-test-daily
airflow-test-daily: ## Test daily ingestion DAG
	docker compose exec airflow-webserver airflow dags test bronze_pncp_daily_ingestion $$(date +%Y-%m-%d)

.PHONY: airflow-trigger-daily
airflow-trigger-daily: ## Trigger daily ingestion DAG
	docker compose exec airflow-webserver airflow dags trigger bronze_pncp_daily_ingestion

.PHONY: airflow-logs
airflow-logs: ## View Airflow logs
	docker compose logs -f airflow-scheduler airflow-worker

.PHONY: airflow-ui
airflow-ui: ## Open Airflow UI in browser
	@echo "Opening http://localhost:8081"
	@echo "Login: airflow / airflow"
	xdg-open http://localhost:8081 || open http://localhost:8081 || echo "Open manually: http://localhost:8081"

.PHONY: airflow-list-dags
airflow-list-dags: ## List all DAGs
	docker compose exec airflow-webserver airflow dags list

.PHONY: airflow-bash
airflow-bash: ## Enter Airflow container shell
	docker compose exec airflow-webserver bash
```

### Usage

```bash
# List all DAGs
make airflow-list-dags

# Test hourly DAG (dry run)
make airflow-test-hourly

# Trigger hourly DAG (real execution)
make airflow-trigger-hourly

# View logs in real-time
make airflow-logs

# Open Airflow UI
make airflow-ui

# Enter container for debugging
make airflow-bash
```

---

## Troubleshooting

### Issue 1: DAG Not Appearing in UI

**Cause:** DAG file has syntax errors or import issues

**Solution:**
```bash
# Check DAG bag for errors
docker compose exec airflow-webserver airflow dags list-import-errors

# Test DAG file syntax
docker compose exec airflow-webserver python -m py_compile /opt/airflow/dags/bronze/pncp_hourly_ingestion.py
```

### Issue 2: Tasks Stuck in "Queued"

**Cause:** Worker not running or too many concurrent tasks

**Solution:**
```bash
# Check worker status
docker compose ps airflow-worker

# Restart worker
docker compose restart airflow-worker

# Check worker logs
docker compose logs airflow-worker
```

### Issue 3: Import Errors (Module Not Found)

**Cause:** Dependencies not installed in Airflow container

**Solution:**
```bash
# Enter container
docker compose exec airflow-webserver bash

# Install missing packages
pip install boto3 pandas pyarrow

# Or rebuild container with updated requirements
docker compose build airflow-webserver
docker compose up -d airflow-webserver
```

### Issue 4: Connection to MinIO/Postgres Failed

**Cause:** Services not ready or network issues

**Solution:**
```bash
# Check all services are healthy
docker compose ps

# Test MinIO connection
docker compose exec airflow-webserver curl http://minio:9000/minio/health/live

# Test Postgres connection
docker compose exec airflow-webserver pg_isready -h postgres -p 5432
```

### Issue 5: Permission Denied on /tmp

**Cause:** Container user doesn't have write permissions

**Solution:**
```bash
# Inside container
chmod 777 /tmp

# Or set proper user permissions in docker-compose.yml
user: "${AIRFLOW_UID:-50000}:0"
```

---

## Recommended Testing Flow

### 1. Start Services
```bash
docker compose up -d
sleep 30  # Wait for services to start
```

### 2. Check DAG is Valid
```bash
make airflow-list-dags | grep bronze_pncp_hourly
```

### 3. Test Single Task (Fastest)
```bash
# Test just the fetch task (doesn't upload to MinIO)
docker compose exec airflow-webserver airflow tasks test \
  bronze_pncp_hourly_ingestion \
  fetch_last_pages \
  2024-10-22
```

### 4. Test Full DAG (Dry Run)
```bash
make airflow-test-hourly
```

### 5. Trigger Real Execution
```bash
make airflow-trigger-hourly
```

### 6. Monitor in UI
- Open http://localhost:8081
- Watch the execution in Graph View
- Check logs if any task fails

### 7. Verify Data in MinIO
```bash
# Access MinIO Console
open http://localhost:9001

# Login: minioadmin / minioadmin
# Navigate to lh-bronze bucket
# Check for new files in pncp/year=2024/...
```

---

## Quick Start Script

Save as `scripts/test_airflow.sh`:

```bash
#!/bin/bash

echo "🚀 Testing Airflow DAGs"
echo "======================"

# 1. Start services
echo "1️⃣ Starting Docker Compose..."
docker compose up -d

# 2. Wait for Airflow to be ready
echo "2️⃣ Waiting for Airflow to be ready..."
sleep 30

# 3. List DAGs
echo "3️⃣ Available DAGs:"
docker compose exec -T airflow-webserver airflow dags list

# 4. Test hourly DAG
echo "4️⃣ Testing hourly ingestion DAG..."
docker compose exec -T airflow-webserver airflow dags test bronze_pncp_hourly_ingestion $(date +%Y-%m-%d)

echo "✅ Test complete! Open http://localhost:8081 to view Airflow UI"
```

Run it:
```bash
chmod +x scripts/test_airflow.sh
./scripts/test_airflow.sh
```

---

## Expected Output

### Successful Task Execution

```
[2024-10-22 10:30:15] INFO - Fetching 13 modalidades
[2024-10-22 10:30:16] INFO - [1/13] Fetching Leilão Eletrônico - last 20 pages...
[2024-10-22 10:30:17] INFO -   Page 1/20: Fetched 500 records
[2024-10-22 10:30:18] INFO -   Page 2/20: Fetched 500 records
...
[2024-10-22 10:35:42] INFO - ✅ Total records fetched: 10234
[2024-10-22 10:35:45] INFO - DataFrame shape: (9856, 45)
[2024-10-22 10:35:46] INFO - Removed 378 duplicates (3.8%)
[2024-10-22 10:35:48] INFO - ✅ Uploaded to s3://lh-bronze/pncp/year=2024/month=10/day=22/hour=10/data_103548.parquet
[2024-10-22 10:35:50] INFO - 📊 Validation Results:
[2024-10-22 10:35:50] INFO -   total_rows: 9856
[2024-10-22 10:35:50] INFO -   has_data: True
[2024-10-22 10:35:50] INFO -   has_required_columns: True
[2024-10-22 10:35:50] INFO -   no_duplicates: True
[2024-10-22 10:35:50] INFO - ✅ Validation passed for 9856 records
```

---

## Next Steps

After successful manual test:

1. **Enable automatic scheduling:**
   - Toggle DAG on in Airflow UI
   - It will run hourly automatically

2. **Monitor first 24 hours:**
   - Check for consistent execution
   - Verify data quality
   - Monitor MinIO storage usage

3. **Setup alerts:**
   - Configure email notifications for failures
   - Setup Slack/Discord webhooks (optional)

4. **Deploy Silver/Gold layers:**
   - Test silver transformation DAG
   - Test gold feature engineering DAG

---

## Tips

- 🔥 **Start small:** Test with 3 modalidades first, then expand to 13
- 📊 **Monitor resources:** Check Docker container CPU/memory usage
- 🐛 **Debug mode:** Add more logging in tasks if needed
- 💾 **Storage:** Monitor MinIO disk usage (expect ~5GB/month)
- ⏱️ **Execution time:** Hourly DAG should complete in <15 minutes
