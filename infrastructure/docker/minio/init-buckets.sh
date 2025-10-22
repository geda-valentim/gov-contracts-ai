#!/bin/bash
# MinIO bucket initialization script
# Creates the Medallion Architecture buckets and configures versioning

set -e

echo "Waiting for MinIO to be ready..."
until curl -sf http://minio:9100/minio/health/live > /dev/null 2>&1; do
    echo "MinIO not ready yet, waiting..."
    sleep 2
done

echo "MinIO is ready. Configuring mc client..."

# Configure MinIO client
mc alias set local http://minio:9100 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

echo "Creating buckets..."

# Create Medallion Architecture buckets
BUCKETS=("bronze" "silver" "gold" "mlflow" "backups" "tmp")

for bucket in "${BUCKETS[@]}"; do
    if mc ls local/${bucket} > /dev/null 2>&1; then
        echo "Bucket '${bucket}' already exists, skipping..."
    else
        echo "Creating bucket: ${bucket}"
        mc mb local/${bucket}

        # Enable versioning for bronze, silver, gold (data lineage)
        if [[ "$bucket" == "bronze" ]] || [[ "$bucket" == "silver" ]] || [[ "$bucket" == "gold" ]]; then
            echo "Enabling versioning for ${bucket}"
            mc version enable local/${bucket}
        fi

        # Set retention policy for backups (30 days)
        if [[ "$bucket" == "backups" ]]; then
            echo "Setting retention policy for backups"
            mc retention set --default GOVERNANCE 30d local/${bucket}
        fi

        # Set lifecycle policy for tmp (auto-delete after 7 days)
        if [[ "$bucket" == "tmp" ]]; then
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

# Create bronze bucket structure
BRONZE_FOLDERS=(
    "licitacoes"
    "editais_raw"
    "editais_text"
    "precos_mercado"
    "cnpj"
)

for folder in "${BRONZE_FOLDERS[@]}"; do
    # Create a .keep file to ensure folder exists
    echo "placeholder" | mc pipe local/bronze/${folder}/.keep
done

echo "MinIO buckets initialized successfully!"
echo ""
echo "Bucket list:"
mc ls local/

echo ""
echo "Versioning status:"
for bucket in bronze silver gold; do
    echo "${bucket}: $(mc version info local/${bucket})"
done
