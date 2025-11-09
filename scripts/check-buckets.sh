#!/bin/bash
# Quick check if MinIO buckets exist
# Returns 0 if all buckets exist, 1 if any is missing

set -e

# Load environment variables
source .env 2>/dev/null || true

# Default bucket names
BUCKETS=(
    "${BUCKET_BRONZE:-gov-lh-bronze}"
    "${BUCKET_SILVER:-gov-lh-silver}"
    "${BUCKET_GOLD:-gov-lh-gold}"
    "${BUCKET_MLFLOW:-gov-mlflow}"
    "${BUCKET_BACKUPS:-gov-backups}"
    "${BUCKET_TMP:-gov-tmp}"
)

# Determine which MinIO container to check
if docker ps --format '{{.Names}}' | grep -q "^shared-minio$"; then
    CONTAINER="shared-minio"
elif docker ps --format '{{.Names}}' | grep -q "^govcontracts-minio$"; then
    CONTAINER="govcontracts-minio"
else
    echo "No MinIO container found"
    exit 1
fi

# Check if all buckets exist
ALL_EXIST=true
for bucket in "${BUCKETS[@]}"; do
    if ! docker exec $CONTAINER mc ls local/${bucket} > /dev/null 2>&1; then
        ALL_EXIST=false
        break
    fi
done

if [ "$ALL_EXIST" = true ]; then
    exit 0  # All buckets exist
else
    exit 1  # Some buckets are missing
fi
