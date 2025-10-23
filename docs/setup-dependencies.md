# Setup Dependencies Guide

## Installing Dependencies for Gov Contracts AI

This project uses **Poetry** for Python dependency management. Each module has its own `pyproject.toml`.

### Prerequisites

```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
poetry --version
```

### Installation by Module

#### 1. Backend (FastAPI + Services)

```bash
cd backend
poetry install
```

This installs:
- FastAPI, Uvicorn
- SQLAlchemy, Alembic
- Pandas, PyArrow
- Boto3, MinIO client
- Requests, Tenacity
- Testing: pytest, pytest-cov

#### 2. ML Module

```bash
cd ml
poetry install
```

This installs:
- scikit-learn, XGBoost
- PyTorch, Transformers
- MLflow, DVC
- Feature engineering tools

#### 3. Airflow (DAGs)

```bash
cd airflow
poetry install
```

This installs:
- Apache Airflow 2.7.3
- Pandas, PyArrow
- Boto3, S3FS
- Great Expectations

### Quick Setup (All Modules)

```bash
# Use Makefile
make setup
```

This will:
1. Start Docker services (PostgreSQL, Redis, MinIO)
2. Install backend dependencies
3. Create databases

### Running Scripts

#### Option 1: Using Poetry (Recommended)

```bash
cd backend
poetry run python ../scripts/run_pncp_ingestion.py --mode custom --pages 5 --modalidades 3
```

#### Option 2: Using Poetry Shell

```bash
cd backend
poetry shell  # Activates virtual environment
python ../scripts/run_pncp_ingestion.py --mode custom --pages 5 --modalidades 3
```

#### Option 3: Using Makefile

```bash
make run-ingestion-test
```

### Troubleshooting

#### Poetry not found

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Or using pip
pip install poetry
```

#### Module not found errors

```bash
# Ensure you're in the correct directory
cd backend

# Install dependencies
poetry install

# Verify installation
poetry show
```

#### tenacity module not found

```bash
cd backend
poetry add tenacity  # If missing from pyproject.toml
```

#### Permission errors with Docker volumes

```bash
# Fix Airflow folder permissions
sudo chown -R $(id -u):$(id -g) airflow/dags airflow/logs airflow/plugins
```

### Development Workflow

```bash
# 1. Install dependencies
cd backend && poetry install

# 2. Activate environment
poetry shell

# 3. Run tests
pytest

# 4. Run standalone services
python ../scripts/run_pncp_ingestion.py --mode custom --pages 1 --modalidades 1

# 5. Exit environment
exit
```

### Docker Environment (Alternative)

If you prefer to use Docker instead of local Poetry:

```bash
# Start all services including Airflow
docker compose up -d

# Enter Airflow container
docker compose exec airflow-webserver bash

# Inside container, dependencies are already installed
python /opt/airflow/scripts/run_pncp_ingestion.py --mode custom --pages 1 --modalidades 1
```

### Dependency Updates

```bash
cd backend

# Update a specific package
poetry update requests

# Update all packages
poetry update

# Add new dependency
poetry add new-package

# Add dev dependency
poetry add --group dev pytest
```

### Checking Installed Packages

```bash
cd backend

# List all packages
poetry show

# Show dependency tree
poetry show --tree

# Check for outdated packages
poetry show --outdated
```

## See Also

- [Project Structure](project-structure.md)
- [Standalone Services Guide](standalone-services-guide.md)
- [QUICKSTART-AIRFLOW.md](../QUICKSTART-AIRFLOW.md)
