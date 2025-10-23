#!/bin/bash
# Complete backup script for Gov Contracts AI
# Backs up PostgreSQL, MinIO data lake, Redis, and configuration

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
PROJECT_NAME="gov-contracts-ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_PATH"

log_info "Starting full backup to $BACKUP_PATH..."
echo ""

# 1. PostgreSQL Backup
log_info "Backing up PostgreSQL databases..."
if docker ps --format '{{.Names}}' | grep -q "govcontracts-postgres"; then
    docker exec govcontracts-postgres pg_dumpall -U admin | \
        gzip > "$BACKUP_PATH/postgres.sql.gz"
    log_success "PostgreSQL backup completed ($(du -h "$BACKUP_PATH/postgres.sql.gz" | cut -f1))"
else
    log_warning "PostgreSQL container not running, skipping..."
fi
echo ""

# 2. MinIO Data Lake Backup
log_info "Backing up MinIO data lake..."
if docker ps --format '{{.Names}}' | grep -q "govcontracts-minio"; then
    mkdir -p "$BACKUP_PATH/minio"

    # List of buckets to backup
    BUCKETS=("lh-bronze" "lh-silver" "lh-gold" "mlflow")

    for bucket in "${BUCKETS[@]}"; do
        log_info "  - Backing up bucket: $bucket"

        # Check if bucket exists
        bucket_exists=$(docker run --rm \
            --network ${PROJECT_NAME}_govcontracts-network \
            minio/mc:latest sh -c "
                mc alias set myminio http://minio:9000 minioadmin minioadmin > /dev/null 2>&1 && \
                mc ls myminio/$bucket > /dev/null 2>&1 && echo 'yes' || echo 'no'
            " 2>/dev/null || echo 'no')

        if [ "$bucket_exists" = "yes" ]; then
            docker run --rm \
                --network ${PROJECT_NAME}_govcontracts-network \
                -v "$BACKUP_PATH/minio:/backup" \
                minio/mc:latest sh -c "
                    mc alias set myminio http://minio:9000 minioadmin minioadmin > /dev/null && \
                    mc mirror --quiet myminio/$bucket /backup/$bucket
                "

            bucket_size=$(du -sh "$BACKUP_PATH/minio/$bucket" 2>/dev/null | cut -f1 || echo "0")
            log_success "  ✓ $bucket backed up ($bucket_size)"
        else
            log_warning "  ✗ Bucket $bucket does not exist, skipping..."
        fi
    done

    log_success "MinIO backup completed"
else
    log_warning "MinIO container not running, skipping..."
fi
echo ""

# 3. Redis Backup
log_info "Backing up Redis..."
if docker ps --format '{{.Names}}' | grep -q "govcontracts-redis"; then
    # Trigger save
    docker exec govcontracts-redis redis-cli SAVE > /dev/null 2>&1 || true

    # Copy RDB file
    if sudo test -f /var/lib/docker/volumes/${PROJECT_NAME}_redis_data/_data/dump.rdb; then
        sudo cp /var/lib/docker/volumes/${PROJECT_NAME}_redis_data/_data/dump.rdb \
            "$BACKUP_PATH/redis.rdb"
        sudo chown $(whoami):$(whoami) "$BACKUP_PATH/redis.rdb"
        log_success "Redis backup completed ($(du -h "$BACKUP_PATH/redis.rdb" | cut -f1))"
    else
        log_warning "Redis dump file not found, skipping..."
    fi
else
    log_warning "Redis container not running, skipping..."
fi
echo ""

# 4. Configuration Backup
log_info "Backing up configuration files..."
tar -czf "$BACKUP_PATH/config.tar.gz" \
    .env.example \
    infrastructure/docker/ \
    2>/dev/null || log_warning "Some config files not found"
log_success "Configuration backup completed"
echo ""

# 5. Create backup manifest
log_info "Creating backup manifest..."
cat > "$BACKUP_PATH/backup_info.txt" <<EOF
Gov Contracts AI - Backup Manifest
=====================================

Backup Created: $(date '+%Y-%m-%d %H:%M:%S %Z')
Hostname: $(hostname)
User: $(whoami)
Project: Gov Contracts AI
Docker Compose Project: $PROJECT_NAME

Included Components:
-------------------
- PostgreSQL databases (all databases)
- MinIO buckets (lh-bronze, lh-silver, lh-gold, mlflow)
- Redis snapshot (dump.rdb)
- Configuration files (.env.example, docker configs)

Backup Contents:
---------------
$(ls -lh "$BACKUP_PATH")

To Restore:
----------
See docs/DATA_PERSISTENCE_AND_BACKUP.md for detailed restore instructions.

Quick Restore Commands:
1. Extract: tar -xzf backup_$TIMESTAMP.tar.gz
2. Restore PostgreSQL: gunzip -c postgres.sql.gz | docker exec -i govcontracts-postgres psql -U admin
3. Restore MinIO: Use mc mirror command (see docs)
4. Restore Redis: Copy redis.rdb to volume and restart

Notes:
-----
- Always test backups before production use
- Verify data integrity after restore
- Keep backups encrypted and secure
EOF

log_success "Backup manifest created"
echo ""

# 6. Compress entire backup
log_info "Compressing backup archive..."
cd "$BACKUP_DIR"
tar -czf "backup_$TIMESTAMP.tar.gz" "$TIMESTAMP" 2>/dev/null || {
    log_error "Compression failed"
    exit 1
}

# Calculate sizes
ARCHIVE_SIZE=$(du -h "backup_$TIMESTAMP.tar.gz" | cut -f1)
UNCOMPRESSED_SIZE=$(du -sh "$TIMESTAMP" | cut -f1)

# Clean up uncompressed backup
rm -rf "$TIMESTAMP"

log_success "Backup compressed successfully"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "BACKUP COMPLETED SUCCESSFULLY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Archive: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
echo "📊 Compressed size: $ARCHIVE_SIZE"
echo "📊 Uncompressed size: $UNCOMPRESSED_SIZE"
echo "🕐 Timestamp: $TIMESTAMP"
echo ""
echo "To restore this backup, see: docs/DATA_PERSISTENCE_AND_BACKUP.md"
echo ""
