#!/bin/bash
set -e

# Create MLflow database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mlflow;
EOSQL

echo "✅ MLflow database created successfully"
