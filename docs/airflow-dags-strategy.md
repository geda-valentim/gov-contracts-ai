# Airflow DAGs Strategy - PNCP Bronze Ingestion

## Overview

Temos **2 estratégias** complementares para ingestão de dados do PNCP na camada Bronze:

1. **Hourly Ingestion** (Near Real-Time) - `pncp_hourly_ingestion.py`
2. **Daily Ingestion** (Full Day Batch) - `pncp_daily_ingestion.py`

---

## 1. Hourly Ingestion (RECOMMENDED)

**File:** `airflow/dags/bronze/pncp_hourly_ingestion.py`

### Strategy
- Roda **a cada hora** (`0 * * * *`)
- Busca **últimas 20 páginas** (não por data específica)
- Captura atualizações recentes do PNCP
- ~10.000 registros por execução (20 páginas × 500/página)

### Characteristics

| Aspect | Details |
|--------|---------|
| **Schedule** | Every hour at :00 |
| **Duration** | ~5 minutes |
| **Data Volume** | ~10.000 records/hour |
| **API Calls** | 60 requests (20 pages × 3 modalidades) |
| **Partitioning** | `year=YYYY/month=MM/day=DD/hour=HH/` |
| **Deduplication** | Yes (by `numeroControlePNCP`) |
| **Use Case** | Near real-time dashboards, alerts |

### Advantages
- ✅ **Low latency**: Data available within 1 hour
- ✅ **Incremental**: Captures new data as it arrives
- ✅ **Efficient**: Only fetches recent pages (not entire day)
- ✅ **Resilient**: Hourly retries if PNCP API fails
- ✅ **Scalable**: Can handle high-frequency updates

### Partitioning Example
```
s3://lh-bronze/pncp/
├── year=2024/
│   └── month=10/
│       └── day=22/
│           ├── hour=00/data_000523.parquet
│           ├── hour=01/data_010345.parquet
│           ├── hour=02/data_020134.parquet
│           └── ...
```

### Task Flow
```
fetch_last_pages (5 min)
    ↓
transform_to_dataframe (30 sec)
    ↓
upload_to_bronze (10 sec)
    ↓
validate_bronze_data (5 sec)
```

---

## 2. Daily Ingestion (Batch Fallback)

**File:** `airflow/dags/bronze/pncp_daily_ingestion.py`

### Strategy
- Roda **diariamente às 2 AM** (`0 2 * * *`)
- Busca **dia completo** (D-1)
- Garante completude dos dados
- Usada como **fallback** ou validação

### Characteristics

| Aspect | Details |
|--------|---------|
| **Schedule** | Daily at 2 AM |
| **Duration** | ~15 minutes |
| **Data Volume** | Full day (~50.000-100.000 records) |
| **API Calls** | Paginação completa (até finalizar) |
| **Partitioning** | `year=YYYY/month=MM/day=DD/` |
| **Use Case** | Batch processing, data quality checks |

### Advantages
- ✅ **Complete**: Ensures all data for the day is captured
- ✅ **Validation**: Can detect missing data from hourly runs
- ✅ **Simple**: Single execution per day
- ✅ **Reliable**: Full day snapshot

---

## Comparison Matrix

| Feature | Hourly | Daily |
|---------|--------|-------|
| **Latency** | 1 hour | 24 hours |
| **Completeness** | 95-98% | 100% |
| **API Load** | Low (20 pages/hour) | High (full pagination) |
| **Storage** | 24 files/day | 1 file/day |
| **Deduplication** | Required | Optional |
| **Use Case** | Real-time analytics | Batch ML training |

---

## Recommended Architecture

### Use BOTH DAGs in Production

```
┌─────────────────────────────────────────────────────────────┐
│                    HOURLY INGESTION                         │
│  Every hour: Fetch last 20 pages → Bronze (hour partition) │
│  Use for: Dashboards, alerts, near real-time analytics     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    DAILY INGESTION                          │
│  2 AM: Fetch full day → Validate completeness              │
│  Use for: Data quality, ML training, historical analysis   │
└─────────────────────────────────────────────────────────────┘
```

### Deduplication Strategy

Since **both DAGs** may capture the same records, deduplication happens in **Silver layer**:

1. **Bronze**: Keep all data (hourly + daily)
2. **Silver**: Deduplicate by `numeroControlePNCP` + `dataPublicacaoPncp`
3. **Gold**: Clean, deduplicated features

---

## Data Flow Example (One Day)

### Hourly Captures
```
00:00 - Fetch pages 1-20   → 8.500 records
01:00 - Fetch pages 1-20   → 9.200 records (some duplicates with 00:00)
02:00 - Fetch pages 1-20   → 10.100 records
...
23:00 - Fetch pages 1-20   → 7.800 records

Total hourly: ~240.000 records (with duplicates)
```

### Daily Batch (2 AM)
```
02:00 - Fetch entire day   → 85.000 unique records

Total daily: 85.000 records (complete snapshot)
```

### Silver Deduplication
```
Input:  240.000 (hourly) + 85.000 (daily) = 325.000 records
Output: 85.000 unique records (duplicates removed)
```

---

## Configuration

### Hourly DAG Configuration

```python
# Number of pages to fetch per hour
NUM_PAGES = 20  # Adjust based on PNCP update frequency

# Page size (PNCP max)
PAGE_SIZE = 500

# Expected records per hour
EXPECTED_RECORDS_PER_HOUR = NUM_PAGES * PAGE_SIZE  # ~10.000
```

### Daily DAG Configuration

```python
# Fetch all pages until no more data
FETCH_ALL_PAGES = True

# Modalidades to fetch
MODALIDADES = [
    ModalidadeContratacao.PREGAO_ELETRONICO,
    ModalidadeContratacao.CONCORRENCIA_ELETRONICA,
    ModalidadeContratacao.DISPENSA_LICITACAO,
    ...
]
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Hourly DAG**:
   - Record count per hour (expect ~8.000-12.000)
   - Execution time (expect <5 min)
   - Duplicate percentage (expect ~20-30%)

2. **Daily DAG**:
   - Total records per day (expect 50K-100K)
   - Execution time (expect <20 min)
   - Data completeness (compare with PNCP website stats)

### Alerts

```python
# Alert if hourly ingestion has zero records for 3+ consecutive hours
if hourly_zero_records_count >= 3:
    send_alert("PNCP Hourly Ingestion: No data for 3 hours")

# Alert if daily ingestion < 50% of expected volume
if daily_record_count < expected_daily_volume * 0.5:
    send_alert("PNCP Daily Ingestion: Low volume detected")
```

---

## Migration Plan

### Phase 1: Setup (Week 1)
- ✅ Deploy hourly DAG
- ✅ Monitor for 7 days
- ✅ Validate data quality

### Phase 2: Validation (Week 2)
- ✅ Deploy daily DAG
- ✅ Compare hourly vs daily completeness
- ✅ Tune NUM_PAGES parameter

### Phase 3: Production (Week 3)
- ✅ Enable both DAGs
- ✅ Setup monitoring dashboards
- ✅ Configure alerts

---

## Cost Analysis

### API Calls

**Hourly:**
- 60 calls/hour (20 pages × 3 modalidades)
- 1.440 calls/day
- ~43.000 calls/month

**Daily:**
- ~300 calls/day (full pagination × 3 modalidades)
- ~9.000 calls/month

**Total:** ~52.000 API calls/month (well within PNCP limits)

### Storage

**Hourly:**
- 24 files/day × 5 MB/file = 120 MB/day
- 3.6 GB/month (Bronze only)

**Daily:**
- 1 file/day × 50 MB/file = 50 MB/day
- 1.5 GB/month (Bronze only)

**Total Bronze Storage:** ~5 GB/month (very affordable)

---

## Conclusion

**Recommended Setup:**
- ✅ Use **Hourly DAG** for near real-time ingestion
- ✅ Use **Daily DAG** for validation and completeness
- ✅ Deduplicate in **Silver layer**
- ✅ Monitor both DAGs for data quality

This dual-strategy approach provides:
- **Low latency** for dashboards
- **High completeness** for ML training
- **Resilience** through redundancy
- **Cost efficiency** through incremental loading
