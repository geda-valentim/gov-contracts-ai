#!/bin/bash
# MinIO bucket initialization script
# Creates the Medallion Architecture buckets and configures versioning

echo "Waiting for MinIO to be ready..."
echo "Connecting to MinIO at http://minio:9000 with user: ${MINIO_ROOT_USER}"

# Wait for MinIO to be ready
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null; then
        if mc admin info local > /dev/null 2>&1; then
            echo "MinIO is ready!"
            break
        fi
    fi
    echo "MinIO not ready yet, waiting... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: MinIO failed to become ready after $MAX_RETRIES attempts"
    exit 1
fi

set -e

echo "Creating buckets..."

# Create Medallion Architecture buckets
# Use environment variables from .env, fallback to defaults
BUCKETS=(
    "${BUCKET_BRONZE:-lh-bronze}"
    "${BUCKET_SILVER:-lh-silver}"
    "${BUCKET_GOLD:-lh-gold}"
    "${BUCKET_MLFLOW:-mlflow}"
    "${BUCKET_BACKUPS:-backups}"
    "${BUCKET_TMP:-tmp}"
)

for bucket in "${BUCKETS[@]}"; do
    if mc ls local/${bucket} > /dev/null 2>&1; then
        echo "Bucket '${bucket}' already exists, skipping..."
    else
        echo "Creating bucket: ${bucket}"
        mc mb local/${bucket}

        # Enable versioning for bronze, silver, gold (data lineage)
        if [[ "$bucket" == *"bronze"* ]] || [[ "$bucket" == *"silver"* ]] || [[ "$bucket" == *"gold"* ]]; then
            echo "Enabling versioning for ${bucket}"
            mc version enable local/${bucket}
        fi

        # Set retention policy for backups (30 days)
        # Note: Object Lock requires bucket to be created with --with-lock flag
        # Skipping retention policy for now
        # if [[ "$bucket" == "backups" ]]; then
        #     echo "Setting retention policy for backups"
        #     mc retention set --default GOVERNANCE 30d local/${bucket}
        # fi

        # Set lifecycle policy for tmp (auto-delete after 7 days)
        if [[ "$bucket" == *"tmp"* ]]; then
            echo "Setting lifecycle policy for tmp"
            cat > /tmp/tmp-lifecycle.json <<EOF
{
    "Rules": [
        {
            "ID": "expire-tmp-files",
            "Status": "Enabled",
            "Expiration": {
                "Days": 7
            }
        }
    ]
}
EOF
            mc ilm import local/${bucket} < /tmp/tmp-lifecycle.json
        fi
    fi
done

echo "Creating folder structure in bronze bucket..."

# Create bronze bucket structure using environment variable
BRONZE_BUCKET="${BUCKET_BRONZE:-lh-bronze}"
BRONZE_FOLDERS=(
    "licitacoes"
    "editais_raw"
    "editais_text"
    "precos_mercado"
    "cnpj"
)

for folder in "${BRONZE_FOLDERS[@]}"; do
    # Create a .keep file to ensure folder exists
    echo "placeholder" | mc pipe local/${BRONZE_BUCKET}/${folder}/.keep
done

echo "MinIO buckets initialized successfully!"
echo ""
echo "Bucket list:"
mc ls local/

echo ""
echo "Versioning status:"
for bucket in "${BUCKET_BRONZE:-lh-bronze}" "${BUCKET_SILVER:-lh-silver}" "${BUCKET_GOLD:-lh-gold}"; do
    echo "${bucket}: $(mc version info local/${bucket})"
done
