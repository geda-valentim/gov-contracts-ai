# MinIO Buckets Configuration Guide

## Overview

MinIO bucket names are now **fully configurable via environment variables** in the `.env` file. This allows you to customize bucket naming conventions per environment without changing code.

## Problem Solved

Previously, bucket names were hardcoded in:
- ❌ `infrastructure/docker/minio/init-buckets.sh` - Bucket creation script
- ❌ `scripts/backup_all.sh` - Backup script

This caused issues when:
- Using different naming conventions per environment (dev/staging/prod)
- Migrating between environments with existing buckets
- Following company naming standards

## Solution

All bucket names are now read from `.env` variables with sensible defaults.

## Configuration

### 1. Edit your `.env` file

```bash
# Data Lake Buckets (Medallion Architecture)
BUCKET_BRONZE=lh-bronze
BUCKET_SILVER=lh-silver
BUCKET_GOLD=lh-gold

# Supporting Buckets
BUCKET_MLFLOW=mlflow
BUCKET_BACKUPS=backups
BUCKET_TMP=tmp
```

### 2. Customize per environment

**Development:**
```bash
BUCKET_BRONZE=dev-bronze
BUCKET_SILVER=dev-silver
BUCKET_GOLD=dev-gold
BUCKET_MLFLOW=dev-mlflow
BUCKET_BACKUPS=dev-backups
BUCKET_TMP=dev-tmp
```

**Staging:**
```bash
BUCKET_BRONZE=staging-bronze
BUCKET_SILVER=staging-silver
BUCKET_GOLD=staging-gold
BUCKET_MLFLOW=staging-mlflow
BUCKET_BACKUPS=staging-backups
BUCKET_TMP=staging-tmp
```

**Production:**
```bash
BUCKET_BRONZE=prod-bronze
BUCKET_SILVER=prod-silver
BUCKET_GOLD=prod-gold
BUCKET_MLFLOW=prod-mlflow
BUCKET_BACKUPS=prod-backups
BUCKET_TMP=prod-tmp
```

### 3. Alternative naming conventions

**Company standard (e.g., prefixed with project):**
```bash
BUCKET_BRONZE=govcontracts-lh-bronze
BUCKET_SILVER=govcontracts-lh-silver
BUCKET_GOLD=govcontracts-lh-gold
```

**Regional buckets:**
```bash
BUCKET_BRONZE=br-lh-bronze
BUCKET_SILVER=br-lh-silver
BUCKET_GOLD=br-lh-gold
```

## How It Works

### Bucket Creation (init-buckets.sh)

When MinIO starts, the init script reads bucket names from environment variables:

```bash
BUCKETS=(
    "${BUCKET_BRONZE:-lh-bronze}"
    "${BUCKET_SILVER:-lh-silver}"
    "${BUCKET_GOLD:-lh-gold}"
    "${BUCKET_MLFLOW:-mlflow}"
    "${BUCKET_BACKUPS:-backups}"
    "${BUCKET_TMP:-tmp}"
)
```

**Syntax explanation:**
- `${BUCKET_BRONZE:-lh-bronze}` - Use `BUCKET_BRONZE` from .env, or default to `lh-bronze` if not set

### Backup Script

The backup script also reads from `.env`:

```bash
# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use configured bucket names
BUCKETS=(
    "${BUCKET_BRONZE:-lh-bronze}"
    "${BUCKET_SILVER:-lh-silver}"
    "${BUCKET_GOLD:-lh-gold}"
    "${BUCKET_MLFLOW:-mlflow}"
)
```

### Application Code

Backend services automatically use the configured bucket names from environment variables:

```python
# backend/app/core/storage_client.py
from os import getenv

BUCKET_BRONZE = getenv("BUCKET_BRONZE", "lh-bronze")
BUCKET_SILVER = getenv("BUCKET_SILVER", "lh-silver")
BUCKET_GOLD = getenv("BUCKET_GOLD", "lh-gold")
```

## Bucket Features

### Versioning (Enabled by Default)

Bronze, Silver, and Gold buckets have versioning enabled for data lineage:

```bash
mc version enable local/${BUCKET_BRONZE}
mc version enable local/${BUCKET_SILVER}
mc version enable local/${BUCKET_GOLD}
```

This allows you to:
- Track changes to data over time
- Recover previous versions of files
- Maintain audit trail for compliance

### Lifecycle Policies

**TMP Bucket** - Auto-delete after 7 days:
```bash
# Files in tmp bucket are automatically deleted after 7 days
# Perfect for temporary processing data
```

**Future:** Backups bucket retention (30 days) can be enabled with Object Lock.

## Usage Examples

### Access buckets in Python

```python
from backend.app.core.storage_client import get_storage_client

storage = get_storage_client()

# Upload to bronze (uses BUCKET_BRONZE from .env)
storage.upload_file(
    file_path="data.parquet",
    key="licitacoes/2025/10/23/data.parquet",
    bucket="bronze"  # Will use BUCKET_BRONZE value
)
```

### Access buckets via MinIO Client (mc)

```bash
# Set alias
mc alias set myminio http://localhost:9000 minioadmin minioadmin

# List buckets (will show configured names)
mc ls myminio/

# Upload file
mc cp file.parquet myminio/lh-bronze/path/to/file.parquet
```

### Access via AWS CLI (S3 compatible)

```bash
# Configure AWS CLI
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
aws configure set default.region us-east-1

# List buckets
aws --endpoint-url=http://localhost:9000 s3 ls

# Upload file
aws --endpoint-url=http://localhost:9000 s3 cp \
  file.parquet s3://lh-bronze/path/to/file.parquet
```

## Migration Guide

### Changing Bucket Names

If you need to change bucket names in an existing deployment:

**Option 1: Rename buckets (preserves data)**
```bash
# Using MinIO Client
mc alias set myminio http://localhost:9000 minioadmin minioadmin

# Unfortunately, MinIO doesn't support direct rename
# You need to copy and delete:
mc mirror myminio/old-bucket-name myminio/new-bucket-name
mc rb --force myminio/old-bucket-name
```

**Option 2: Update .env and recreate (data loss)**
```bash
# 1. Backup data first!
./scripts/backup_all.sh

# 2. Stop services
docker compose down

# 3. Remove MinIO volume
docker volume rm gov-contracts-ai_minio_data

# 4. Update .env with new bucket names
vim .env

# 5. Restart services (buckets will be recreated)
docker compose up -d

# 6. Restore data to new buckets
# (see docs/DATA_PERSISTENCE_AND_BACKUP.md)
```

**Option 3: Keep old names, create new ones**
```bash
# Just update .env and restart
# Old buckets will remain, new ones will be created
vim .env
docker compose restart minio minio-init
```

## Verification

### Check created buckets

```bash
# Via Docker
docker exec govcontracts-minio mc ls local/

# Via MinIO Console
# Open http://localhost:9001
# Login: minioadmin / minioadmin
```

### Verify versioning status

```bash
docker exec govcontracts-minio \
  mc version info local/${BUCKET_BRONZE}
```

### Check bucket policies

```bash
docker exec govcontracts-minio \
  mc ilm export local/${BUCKET_TMP}
```

## Troubleshooting

### Buckets not created

**Check init container logs:**
```bash
docker compose logs minio-init
```

**Common issues:**
- MinIO not ready when init runs → Check MinIO health
- Environment variables not passed → Check docker-compose.yml env_file
- Network issues → Check docker network connectivity

### Wrong bucket names being used

**Verify environment variables:**
```bash
# Check what's loaded
grep BUCKET .env

# Check what container sees
docker compose config | grep BUCKET
```

**Restart services after .env changes:**
```bash
docker compose down
docker compose up -d
```

### Cannot access bucket

**Check bucket exists:**
```bash
mc ls myminio/${BUCKET_BRONZE}
```

**Check permissions:**
```bash
mc admin policy list myminio
```

## Related Files

- `.env` - Environment configuration (customize bucket names here)
- `.env.example` - Template with defaults
- `infrastructure/docker/minio/init-buckets.sh` - Bucket creation script
- `scripts/backup_all.sh` - Backup script (uses bucket names from .env)
- `backend/app/core/storage_client.py` - Storage abstraction layer
- `backend/app/core/minio_client.py` - MinIO client implementation

## Best Practices

✅ **DO:**
- Use descriptive, consistent naming conventions
- Include environment prefix (dev/staging/prod)
- Document custom naming in team wiki
- Test bucket names in dev before production
- Keep .env.example updated with current schema

❌ **DON'T:**
- Don't hardcode bucket names in code
- Don't use special characters in bucket names (stick to letters, numbers, hyphens)
- Don't change production bucket names without backup
- Don't commit `.env` to version control (use `.env.example`)

## Default Bucket Structure

```
lh-bronze/           # Raw data (Bronze layer)
├── licitacoes/      # PNCP procurement data
│   └── YYYY/MM/DD/  # Partitioned by date
├── editais_raw/     # Raw procurement documents
├── editais_text/    # Extracted text from documents
├── precos_mercado/  # Market price data
└── cnpj/            # Company registry data

lh-silver/           # Cleaned data (Silver layer)
├── contracts/       # Validated contracts
└── entities/        # Normalized entities

lh-gold/             # Analytics-ready (Gold layer)
├── metrics/         # Aggregated metrics
└── features/        # ML features

mlflow/              # ML artifacts
└── artifacts/       # Model artifacts, plots

backups/             # Manual backups
└── YYYY-MM-DD/      # Daily backups

tmp/                 # Temporary files (auto-delete 7 days)
└── processing/      # Processing intermediate files
```
