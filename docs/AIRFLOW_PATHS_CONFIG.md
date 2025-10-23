# Airflow Paths Configuration Guide

## Problem

Previously, Airflow DAG paths were **hardcoded** in the `docker-compose.yml` using relative paths like `../../../airflow/dags`. This caused issues when:

- Running Docker Compose from different directories
- Deploying to different machines with different project locations
- Setting up new development environments

## Solution

All Airflow paths are now **configurable via environment variables** in the `.env` file.

## Configuration

### 1. Edit your `.env` file

**IMPORTANT: Use absolute paths** for each machine:

```bash
# Machine 1 (WSL)
AIRFLOW_DAGS_PATH=/home/geda/gov-contracts-ai/airflow/dags
AIRFLOW_LOGS_PATH=/home/geda/gov-contracts-ai/airflow/logs
AIRFLOW_PLUGINS_PATH=/home/geda/gov-contracts-ai/airflow/plugins
AIRFLOW_CONFIG_PATH=/home/geda/gov-contracts-ai/airflow/config
BACKEND_PATH=/home/geda/gov-contracts-ai/backend

# Machine 2 (Linux Server)
AIRFLOW_DAGS_PATH=/var/app/gov-contracts-ai/airflow/dags
AIRFLOW_LOGS_PATH=/var/app/gov-contracts-ai/airflow/logs
AIRFLOW_PLUGINS_PATH=/var/app/gov-contracts-ai/airflow/plugins
AIRFLOW_CONFIG_PATH=/var/app/gov-contracts-ai/airflow/config
BACKEND_PATH=/var/app/gov-contracts-ai/backend
```

**Why absolute paths?** Docker Compose resolves relative paths (`./airflow/dags`) relative to the compose file location (`infrastructure/docker/airflow/`), not the project root. Absolute paths work from any directory.

### 2. Docker Compose will use these paths

The `infrastructure/docker/airflow/compose.yml` now references these variables:

```yaml
x-airflow-volumes: &airflow-volumes
  - ${AIRFLOW_DAGS_PATH:-./airflow/dags}:/opt/airflow/dags
  - ${AIRFLOW_LOGS_PATH:-./airflow/logs}:/opt/airflow/logs
  - ${AIRFLOW_PLUGINS_PATH:-./airflow/plugins}:/opt/airflow/plugins
  - ${AIRFLOW_CONFIG_PATH:-./airflow/config}:/opt/airflow/config
  - ${BACKEND_PATH:-./backend}:/opt/airflow/backend:ro
```

## Usage

### Run from project root (Recommended)

```bash
cd /path/to/gov-contracts-ai
docker compose up -d
```

Ensure `.env` has absolute paths for your machine:
```bash
AIRFLOW_DAGS_PATH=/path/to/gov-contracts-ai/airflow/dags
# ... other paths
```

### Run from anywhere

With absolute paths configured, you can run from any directory:

```bash
cd /anywhere
docker compose -f /var/app/gov-contracts-ai/docker-compose.yml up -d
```

### Override at runtime

```bash
AIRFLOW_DAGS_PATH=/custom/path/airflow/dags docker compose up -d
```

## Benefits

✅ **Portable**: Works on any machine with any project location
✅ **Flexible**: Can run from any directory
✅ **Documented**: Clear configuration in `.env`
✅ **Fallback**: Defaults to `./airflow/dags` if not set
✅ **Version Control**: `.env.example` shows the structure

## Migration from Old Setup

If you're upgrading from the old hardcoded paths:

1. Update your `.env` file with the new variables (see `.env.example`)
2. Set `PROJECT_ROOT` to your project path or use `.` for current directory
3. Restart Airflow services:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Troubleshooting

### DAGs not loading

Check that paths are correct:
```bash
# Print resolved paths
docker compose config | grep -A 5 "airflow-volumes"

# Verify DAGs directory exists
ls -la ${PROJECT_ROOT}/airflow/dags
```

### Permission issues

Ensure the `AIRFLOW_UID` has access to the directories:
```bash
# From project root
sudo chown -R ${AIRFLOW_UID:-50000}:0 airflow/dags airflow/logs airflow/plugins
```

### Variables not expanding

Make sure you're using Docker Compose v2.20+:
```bash
docker compose version
```

## Related Files

- `.env` - Your local configuration
- `.env.example` - Template with documentation
- `infrastructure/docker/airflow/compose.yml` - Airflow service definition
- `docker-compose.yml` - Main compose file
