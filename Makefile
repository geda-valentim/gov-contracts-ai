# Makefile
.PHONY: help setup up down logs test test-cov test-html lint format clean backend-shell
.PHONY: airflow-ui airflow-logs airflow-list-dags airflow-bash
.PHONY: airflow-test-hourly airflow-trigger-hourly airflow-test-daily airflow-trigger-daily

help:
	@echo "Gov Contracts AI - Available commands:"
	@echo ""
	@echo "🐳 Docker Services:"
	@echo "  make setup      - First time setup"
	@echo "  make up         - Start all services"
	@echo "  make up-dev     - Start all services + dev tools (Adminer, RedisInsight)"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo "  make test-html  - Generate HTML coverage report"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code"
	@echo ""
	@echo "✈️  Airflow DAGs:"
	@echo "  make airflow-ui            - Open Airflow UI (http://localhost:8081)"
	@echo "  make airflow-list-dags     - List all DAGs"
	@echo "  make airflow-test-hourly   - Test hourly ingestion DAG"
	@echo "  make airflow-trigger-hourly - Trigger hourly ingestion DAG"
	@echo "  make airflow-test-daily    - Test daily ingestion DAG"
	@echo "  make airflow-trigger-daily - Trigger daily ingestion DAG"
	@echo "  make airflow-logs          - View Airflow logs"
	@echo "  make airflow-bash          - Enter Airflow container"
	@echo ""
	@echo "🧪 Development Testing:"
	@echo "  make test-dag-direct   - Test DAG functions directly (no Airflow)"
	@echo "  make test-pncp-client  - Test PNCP API client"
	@echo "  make test-minio-client - Test MinIO client"
	@echo ""
	@echo "🚀 Standalone Services (No Airflow):"
	@echo "  make run-ingestion-test    - Test ingestion (5 pages, 3 modalidades)"
	@echo "  make run-ingestion-hourly  - Run hourly ingestion (20 pages)"
	@echo "  make run-ingestion-daily   - Run daily ingestion (all pages)"
	@echo "  make run-ingestion-custom  - Run custom ingestion with DATE=YYYYMMDD PAGES=N"
	@echo ""
	@echo "🛠️ Development:"
	@echo "  make backend-shell - Open Poetry shell"
	@echo "  make clean         - Clean up containers and caches"

setup:
	@echo "Setting up Gov Contracts AI..."
	docker compose up -d postgres redis minio
	@echo "⏳ Waiting for PostgreSQL to be ready..."
	@sleep 5
	docker exec govcontracts-postgres psql -U admin -d govcontracts -c "CREATE DATABASE IF NOT EXISTS mlflow;" || true
	docker compose up -d mlflow
	cd backend && poetry install || echo "⚠️  Poetry not installed. Run: curl -sSL https://install.python-poetry.org | python3 -"
	@echo "✅ Setup complete!"

up:
	docker compose up -d
	@echo "✅ Services running on:"
	@echo "  - PostgreSQL: localhost:5433"
	@echo "  - Redis: localhost:6380"
	@echo "  - MLflow: http://localhost:5000"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "  - MinIO API: http://localhost:9000"
	@echo "  - Airflow: http://localhost:8081"
	@echo "  - OpenSearch: http://localhost:9201"
	@echo "  - OpenSearch Dashboards: http://localhost:5602"

up-dev:
	docker compose --profile dev up -d
	@echo "✅ Services running on:"
	@echo "  - PostgreSQL: localhost:5433"
	@echo "  - Redis: localhost:6380"
	@echo "  - MLflow: http://localhost:5000"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "  - MinIO API: http://localhost:9000"
	@echo "  - Airflow: http://localhost:8081"
	@echo "  - OpenSearch: http://localhost:9201"
	@echo "  - OpenSearch Dashboards: http://localhost:5602"
	@echo "  🛠️  Dev Tools:"
	@echo "  - Adminer: http://localhost:8080"
	@echo "  - RedisInsight: http://localhost:5540"

down:
	docker compose down

logs:
	docker compose logs -f

test:
	@echo "🧪 Running tests..."
	cd backend && poetry run pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	cd backend && poetry run pytest tests/ -v --cov=app --cov-report=term-missing

test-html:
	@echo "🧪 Generating HTML coverage report..."
	cd backend && poetry run pytest tests/ --cov=app --cov-report=html
	@echo "✅ Open backend/htmlcov/index.html in your browser"

lint:
	@echo "🔍 Running linter..."
	cd backend && poetry run ruff check app/ tests/

format:
	@echo "✨ Formatting code..."
	cd backend && poetry run ruff format app/ tests/

backend-shell:
	@echo "🐚 Opening Poetry shell..."
	cd backend && poetry shell

clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cd backend && rm -rf htmlcov .coverage coverage.xml .pytest_cache
	@echo "✅ Cleanup complete!"

# ==========================================
# Airflow Commands
# ==========================================

airflow-ui:
	@echo "🌐 Opening Airflow UI..."
	@echo "URL: http://localhost:8081"
	@echo "Login: airflow / airflow"
	@command -v xdg-open > /dev/null && xdg-open http://localhost:8081 || \
	 command -v open > /dev/null && open http://localhost:8081 || \
	 echo "Open manually: http://localhost:8081"

airflow-list-dags:
	@echo "📋 Listing all DAGs..."
	docker compose exec airflow-webserver airflow dags list

airflow-test-hourly:
	@echo "🧪 Testing hourly ingestion DAG..."
	docker compose exec airflow-webserver airflow dags test bronze_pncp_hourly_ingestion $$(date +%Y-%m-%d)

airflow-trigger-hourly:
	@echo "▶️  Triggering hourly ingestion DAG..."
	docker compose exec airflow-webserver airflow dags trigger bronze_pncp_hourly_ingestion
	@echo "✅ DAG triggered! Check http://localhost:8081 for progress"

airflow-test-daily:
	@echo "🧪 Testing daily ingestion DAG..."
	docker compose exec airflow-webserver airflow dags test bronze_pncp_daily_ingestion $$(date +%Y-%m-%d)

airflow-trigger-daily:
	@echo "▶️  Triggering daily ingestion DAG..."
	docker compose exec airflow-webserver airflow dags trigger bronze_pncp_daily_ingestion
	@echo "✅ DAG triggered! Check http://localhost:8081 for progress"

airflow-logs:
	@echo "📜 Viewing Airflow logs..."
	docker compose logs -f airflow-scheduler airflow-worker

airflow-bash:
	@echo "🐚 Entering Airflow container..."
	docker compose exec airflow-webserver bash

# ==========================================
# Development / Testing
# ==========================================

.PHONY: test-dag-direct test-pncp-client test-minio-client

test-dag-direct:
	@echo "🧪 Testing DAG functions directly (without Airflow)..."
	cd backend && poetry run python ../scripts/test_dag_directly.py --task full --pages 5 --modalidades 3

test-pncp-client:
	@echo "🧪 Testing PNCP client..."
	cd backend && poetry run python ../scripts/test_dag_directly.py --task pncp

test-minio-client:
	@echo "🧪 Testing MinIO client..."
	cd backend && poetry run python ../scripts/test_dag_directly.py --task minio

# ==========================================
# Standalone Services (No Airflow)
# ==========================================

.PHONY: run-ingestion-test run-ingestion-hourly run-ingestion-daily run-ingestion-custom

run-ingestion-test:
	@echo "🚀 Running test ingestion (5 pages, 3 modalidades)..."
	cd backend && poetry run python ../scripts/run_pncp_ingestion.py --mode custom --pages 5 --modalidades 3

run-ingestion-hourly:
	@echo "🚀 Running hourly ingestion (20 pages, all modalidades)..."
	cd backend && poetry run python ../scripts/run_pncp_ingestion.py --mode hourly

run-ingestion-daily:
	@echo "🚀 Running daily ingestion (all pages, all modalidades)..."
	cd backend && poetry run python ../scripts/run_pncp_ingestion.py --mode daily

run-ingestion-custom:
	@echo "🚀 Running custom ingestion..."
	@echo "Usage: make run-ingestion-custom DATE=20241022 PAGES=10 MODALIDADES=5"
	cd backend && poetry run python ../scripts/run_pncp_ingestion.py --mode custom $(if $(DATE),--date $(DATE)) $(if $(PAGES),--pages $(PAGES)) $(if $(MODALIDADES),--modalidades $(MODALIDADES))
