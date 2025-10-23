# Data Persistence and Backup Guide

## Overview

This document lists all data persistence locations that need to be backed up on the server.

## Docker Volumes (Persistent Data)

All Docker volumes are stored in `/var/lib/docker/volumes/` by default.

### Critical Data Volumes

| Service | Volume Name | Mountpoint | Purpose | Backup Priority |
|---------|-------------|------------|---------|-----------------|
| **PostgreSQL** | `gov-contracts-ai_postgres_data` | `/var/lib/docker/volumes/gov-contracts-ai_postgres_data/_data` | Database data (contracts, metadata, MLflow tracking) | 🔴 **CRITICAL** |
| **MinIO** | `gov-contracts-ai_minio_data` | `/var/lib/docker/volumes/gov-contracts-ai_minio_data/_data` | Data Lake (Bronze/Silver/Gold layers, ML artifacts) | 🔴 **CRITICAL** |
| **Redis** | `gov-contracts-ai_redis_data` | `/var/lib/docker/volumes/gov-contracts-ai_redis_data/_data` | Cache and Celery queue state | 🟡 **MEDIUM** |
| **MLflow** | `gov-contracts-ai_mlflow_data` | `/var/lib/docker/volumes/gov-contracts-ai_mlflow_data/_data` | MLflow metadata | 🟡 **MEDIUM** |
| **OpenSearch** | `gov-contracts-ai_opensearch_data` | `/var/lib/docker/volumes/gov-contracts-ai_opensearch_data/_data` | Search indexes | 🟢 **LOW** (can rebuild) |

### Project Directories (Host-mounted)

These directories are mounted from the project and should also be backed up:

| Directory | Purpose | Backup Priority |
|-----------|---------|-----------------|
| `airflow/dags/` | DAG definitions | 🔴 **CRITICAL** (version controlled) |
| `airflow/logs/` | Execution logs | 🟢 **LOW** (for debugging) |
| `airflow/plugins/` | Custom Airflow plugins | 🔴 **CRITICAL** (version controlled) |
| `backend/` | Application code | 🔴 **CRITICAL** (version controlled) |

## Backup Strategy

### 1. PostgreSQL Database

**Method 1: Docker Volume Backup (Recommended)**
```bash
# Stop the container
docker compose stop postgres

# Backup the volume
sudo tar -czf postgres_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  -C /var/lib/docker/volumes/gov-contracts-ai_postgres_data/_data .

# Restart the container
docker compose start postgres
```

**Method 2: SQL Dump (Portable)**
```bash
# Backup all databases
docker exec govcontracts-postgres pg_dumpall -U admin > \
  postgres_backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific database
docker exec govcontracts-postgres pg_dump -U admin govcontracts > \
  govcontracts_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from dump
docker exec -i govcontracts-postgres psql -U admin < backup.sql
```

### 2. MinIO Data Lake

**Method 1: Docker Volume Backup**
```bash
# Stop the container
docker compose stop minio

# Backup the volume (WARNING: Can be LARGE)
sudo tar -czf minio_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  -C /var/lib/docker/volumes/gov-contracts-ai_minio_data/_data .

# Restart
docker compose start minio
```

**Method 2: MinIO Client (mc) - Selective Backup**
```bash
# Install mc
docker run -it --rm --network gov-contracts-ai_govcontracts-network \
  minio/mc:latest alias set myminio http://minio:9000 minioadmin minioadmin

# Backup specific bucket
docker run -it --rm --network gov-contracts-ai_govcontracts-network \
  -v $(pwd)/backup:/backup \
  minio/mc:latest mirror myminio/lh-bronze /backup/lh-bronze

# Restore
docker run -it --rm --network gov-contracts-ai_govcontracts-network \
  -v $(pwd)/backup:/backup \
  minio/mc:latest mirror /backup/lh-bronze myminio/lh-bronze
```

**Method 3: Sync to S3 (Production)**
```bash
# Sync MinIO to AWS S3
mc mirror myminio/lh-bronze s3/production-backup-bronze
```

### 3. Redis Data

**Method 1: RDB Snapshot**
```bash
# Trigger manual snapshot
docker exec govcontracts-redis redis-cli SAVE

# Backup RDB file
sudo cp /var/lib/docker/volumes/gov-contracts-ai_redis_data/_data/dump.rdb \
  redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# Restore: Just copy dump.rdb back and restart
```

**Method 2: Volume Backup**
```bash
docker compose stop redis
sudo tar -czf redis_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  -C /var/lib/docker/volumes/gov-contracts-ai_redis_data/_data .
docker compose start redis
```

### 4. MLflow Data

MLflow stores metadata in PostgreSQL and artifacts in MinIO, so:
- **Metadata**: Backed up with PostgreSQL
- **Artifacts**: Backed up with MinIO (`mlflow` bucket)
- **Volume**: Contains temporary files only

```bash
# Optional: Backup MLflow volume
docker compose stop mlflow
sudo tar -czf mlflow_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  -C /var/lib/docker/volumes/gov-contracts-ai_mlflow_data/_data .
docker compose start mlflow
```

### 5. Airflow Logs

```bash
# Backup logs directory
tar -czf airflow_logs_$(date +%Y%m%d_%H%M%S).tar.gz airflow/logs/

# Usually not needed - logs are for debugging only
```

## Complete Backup Script

Save this as `scripts/backup_all.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

echo "🔄 Starting full backup to $BACKUP_PATH..."

# 1. PostgreSQL (SQL dump)
echo "📊 Backing up PostgreSQL..."
docker exec govcontracts-postgres pg_dumpall -U admin | \
  gzip > "$BACKUP_PATH/postgres.sql.gz"

# 2. MinIO buckets (selective)
echo "🗄️  Backing up MinIO data lake..."
for bucket in lh-bronze lh-silver lh-gold mlflow; do
  echo "  - Backing up bucket: $bucket"
  mkdir -p "$BACKUP_PATH/minio/$bucket"
  docker run --rm --network gov-contracts-ai_govcontracts-network \
    -v "$BACKUP_PATH/minio:/backup" \
    minio/mc:latest sh -c "
      mc alias set myminio http://minio:9000 minioadmin minioadmin && \
      mc mirror --quiet myminio/$bucket /backup/$bucket
    "
done

# 3. Redis RDB
echo "💾 Backing up Redis..."
docker exec govcontracts-redis redis-cli SAVE
sudo cp /var/lib/docker/volumes/gov-contracts-ai_redis_data/_data/dump.rdb \
  "$BACKUP_PATH/redis.rdb"

# 4. Configuration files
echo "⚙️  Backing up configuration..."
tar -czf "$BACKUP_PATH/config.tar.gz" \
  .env.example \
  infrastructure/docker/

# Create backup info
echo "📝 Creating backup manifest..."
cat > "$BACKUP_PATH/backup_info.txt" <<EOF
Backup Created: $TIMESTAMP
Hostname: $(hostname)
Project: Gov Contracts AI
Docker Compose Project: gov-contracts-ai

Included:
- PostgreSQL databases (all)
- MinIO buckets (lh-bronze, lh-silver, lh-gold, mlflow)
- Redis snapshot
- Configuration files

To Restore:
See docs/DATA_PERSISTENCE_AND_BACKUP.md
EOF

# Compress entire backup
echo "🗜️  Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "backup_$TIMESTAMP.tar.gz" "$TIMESTAMP"
rm -rf "$TIMESTAMP"

echo "✅ Backup completed: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
echo "📦 Backup size: $(du -h "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" | cut -f1)"
```

Make it executable:
```bash
chmod +x scripts/backup_all.sh
```

Run it:
```bash
./scripts/backup_all.sh
```

## Restore Procedure

### Full System Restore

```bash
# 1. Extract backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
cd backup_YYYYMMDD_HHMMSS

# 2. Stop all services
docker compose down

# 3. Restore PostgreSQL
gunzip -c postgres.sql.gz | docker exec -i govcontracts-postgres psql -U admin

# 4. Restore MinIO
for bucket in lh-bronze lh-silver lh-gold mlflow; do
  docker run --rm --network gov-contracts-ai_govcontracts-network \
    -v "$(pwd)/minio:/backup" \
    minio/mc:latest sh -c "
      mc alias set myminio http://minio:9000 minioadmin minioadmin && \
      mc mirror /backup/$bucket myminio/$bucket
    "
done

# 5. Restore Redis
docker compose stop redis
sudo cp redis.rdb /var/lib/docker/volumes/gov-contracts-ai_redis_data/_data/dump.rdb
docker compose start redis

# 6. Restart all services
docker compose up -d
```

## Migration to New Server

### On Old Server
```bash
# 1. Create full backup
./scripts/backup_all.sh

# 2. Transfer to new server
scp backups/backup_*.tar.gz user@newserver:/path/to/backups/
```

### On New Server
```bash
# 1. Clone repository
git clone https://github.com/your-org/gov-contracts-ai.git
cd gov-contracts-ai

# 2. Configure .env (update paths!)
cp .env.example .env
vim .env  # Set AIRFLOW_DAGS_PATH=/var/app/gov-contracts-ai/airflow/dags etc

# 3. Start infrastructure (creates volumes)
docker compose up -d

# 4. Wait for services to be healthy
docker compose ps

# 5. Stop services
docker compose down

# 6. Restore from backup (see Restore Procedure above)

# 7. Start services
docker compose up -d
```

## Automated Backup Schedule

### Using Cron (Linux)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /var/app/gov-contracts-ai/scripts/backup_all.sh >> /var/log/govcontracts-backup.log 2>&1

# Keep only last 7 days of backups
0 3 * * * find /var/app/gov-contracts-ai/backups -name "backup_*.tar.gz" -mtime +7 -delete
```

### Backup to S3

```bash
# After backup completes, sync to S3
aws s3 sync ./backups/ s3://your-backup-bucket/gov-contracts-ai/ \
  --exclude "*" --include "backup_*.tar.gz"
```

## Disk Space Monitoring

```bash
# Check volume sizes
docker system df -v

# Check specific volumes
sudo du -sh /var/lib/docker/volumes/gov-contracts-ai_*

# Expected sizes (approximate):
# - postgres_data: 1-10 GB (depends on data)
# - minio_data: 10-100+ GB (data lake, can be very large)
# - redis_data: 100 MB - 2 GB (cache)
# - mlflow_data: 100 MB - 1 GB (metadata)
# - opensearch_data: 1-10 GB (indexes)
```

## Important Notes

⚠️ **CRITICAL**:
- **PostgreSQL** contains all structured data (contracts, metadata, users)
- **MinIO** contains all raw data (Bronze layer) and ML models
- Always test restores regularly!

🔒 **Security**:
- Store backups encrypted
- Don't commit `.env` to version control
- Rotate backup encryption keys

📊 **Monitoring**:
- Set up alerts for failed backups
- Monitor disk space on backup destination
- Verify backup integrity regularly

## Related Files

- `.env` - Environment configuration (customize paths per machine)
- `docker-compose.yml` - Service orchestration
- `scripts/backup_all.sh` - Automated backup script
- `docs/AIRFLOW_PATHS_CONFIG.md` - Airflow paths configuration
