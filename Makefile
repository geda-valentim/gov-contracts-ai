# Makefile
.PHONY: help setup up down logs test test-cov test-html lint format clean backend-shell
.PHONY: airflow-ui airflow-logs airflow-list-dags airflow-bash
.PHONY: airflow-test-hourly airflow-trigger-hourly airflow-test-daily airflow-trigger-daily
.PHONY: check-minio check-services up-smart fix-minio-network init-buckets

help:
	@echo "Gov Contracts AI - Available commands:"
	@echo ""
	@echo "🐳 Docker Services:"
	@echo "  make setup      - First time setup"
	@echo "  make up         - Start all services"
	@echo "  make up-smart   - Smart startup (checks MinIO availability first)"
	@echo "  make up-dev     - Start all services + dev tools (Adminer, RedisInsight)"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs"
	@echo "  make check-services    - Check all services availability"
	@echo "  make check-minio       - Check if MinIO is available"
	@echo "  make init-buckets      - Initialize MinIO buckets (works with local or shared MinIO)"
	@echo "  make fix-minio-network - Fix Airflow-MinIO network connectivity (for shared-minio)"
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

# Check all services availability
check-services:
	@echo "🔍 Checking services availability..."
	@echo ""
	@echo "MinIO:"
	@ENDPOINT=$$(grep "^MINIO_ENDPOINT=" .env 2>/dev/null | cut -d= -f2 || echo "localhost:9000"); \
	HOST=$$(echo $$ENDPOINT | cut -d: -f1); \
	PORT=$$(echo $$ENDPOINT | cut -d: -f2); \
	if nc -z -w2 $$HOST $$PORT 2>/dev/null; then \
		echo "  ✅ Available at $$ENDPOINT"; \
	else \
		echo "  ❌ Not available at $$ENDPOINT"; \
	fi
	@echo ""
	@echo "PostgreSQL:"
	@PG_URL=$$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d= -f2 || echo "postgresql://admin:dev123@localhost:5433/govcontracts"); \
	PG_PORT=$$(echo $$PG_URL | grep -oP ':\d+/' | tr -d ':/' || echo "5433"); \
	if nc -z -w2 localhost $$PG_PORT 2>/dev/null; then \
		echo "  ✅ Available at localhost:$$PG_PORT"; \
	else \
		echo "  ❌ Not available at localhost:$$PG_PORT"; \
	fi
	@echo ""
	@echo "Redis:"
	@REDIS_URL=$$(grep "^REDIS_URL=" .env 2>/dev/null | cut -d= -f2 || echo "redis://localhost:6380"); \
	REDIS_PORT=$$(echo $$REDIS_URL | grep -oP ':\d+' | tail -1 | tr -d ':' || echo "6380"); \
	if nc -z -w2 localhost $$REDIS_PORT 2>/dev/null; then \
		echo "  ✅ Available at localhost:$$REDIS_PORT"; \
	else \
		echo "  ❌ Not available at localhost:$$REDIS_PORT"; \
	fi

check-minio:
	@echo "🔍 Checking MinIO availability..."
	@ENDPOINT=$$(grep "^MINIO_ENDPOINT=" .env 2>/dev/null | cut -d= -f2 || echo "localhost:9000"); \
	HOST=$$(echo $$ENDPOINT | cut -d: -f1); \
	PORT=$$(echo $$ENDPOINT | cut -d: -f2); \
	echo "Testing $$HOST:$$PORT..."; \
	if nc -z -w2 $$HOST $$PORT 2>/dev/null; then \
		echo "✅ MinIO is available at $$ENDPOINT"; \
	else \
		echo "❌ MinIO not available at $$ENDPOINT"; \
	fi

fix-minio-network:
	@echo "🔧 Fixing Airflow-MinIO network connectivity..."
	@echo ""
	@# Check if shared-minio exists
	@if ! docker ps --format '{{.Names}}' | grep -q "^shared-minio$$"; then \
		echo "⚠️  shared-minio container not found. Skipping network fix."; \
		echo "   If you want to use the local MinIO, run: make up-smart"; \
		exit 0; \
	fi
	@# Check if shared-dev-network exists
	@if ! docker network ls --format '{{.Name}}' | grep -q "^shared-dev-network$$"; then \
		echo "❌ shared-dev-network not found. Creating it..."; \
		docker network create shared-dev-network; \
	fi
	@# Ensure shared-minio has 'minio' alias in shared-dev-network
	@echo "🔗 Configuring MinIO network alias..."
	@docker network disconnect shared-dev-network shared-minio 2>/dev/null || true
	@docker network connect --alias minio shared-dev-network shared-minio
	@echo "✅ MinIO configured with alias 'minio'"
	@echo ""
	@# Connect Airflow services to shared-dev-network
	@echo "🔗 Connecting Airflow services to shared-dev-network..."
	@for service in airflow-worker airflow-scheduler airflow-dag-processor airflow-webserver airflow-triggerer; do \
		if docker ps --format '{{.Names}}' | grep -q "govcontracts-$$service"; then \
			if docker inspect govcontracts-$$service --format '{{range $$key, $$value := .NetworkSettings.Networks}}{{$$key}} {{end}}' | grep -q "shared-dev-network"; then \
				echo "  ✅ govcontracts-$$service already connected"; \
			else \
				docker network connect shared-dev-network govcontracts-$$service 2>/dev/null && \
					echo "  ✅ Connected govcontracts-$$service" || \
					echo "  ⚠️  Could not connect govcontracts-$$service"; \
			fi; \
		fi; \
	done
	@echo ""
	@echo "🧪 Testing connectivity..."
	@docker exec govcontracts-airflow-worker curl -sf http://minio:9000/minio/health/live >/dev/null && \
		echo "✅ Airflow can reach MinIO!" || \
		echo "❌ Airflow cannot reach MinIO. Check docker logs."
	@echo ""
	@echo "✅ Network fix complete!"

init-buckets:
	@echo "🪣 Initializing MinIO buckets..."
	@echo ""
	@# Check if MinIO is available
	@ENDPOINT=$$(grep "^MINIO_ENDPOINT=" .env 2>/dev/null | cut -d= -f2 || echo "localhost:9000"); \
	HOST=$$(echo $$ENDPOINT | cut -d: -f1); \
	PORT=$$(echo $$ENDPOINT | cut -d: -f2); \
	if ! nc -z -w2 $$HOST $$PORT 2>/dev/null; then \
		echo "❌ MinIO not available at $$ENDPOINT"; \
		echo "   Run 'make up-smart' first to start services."; \
		exit 1; \
	fi; \
	echo "✅ MinIO is available at $$ENDPOINT"
	@echo ""
	@# Determine which network to use
	@NETWORK=""; \
	if docker ps --format '{{.Names}}' | grep -q "^shared-minio$$"; then \
		echo "📡 Detected shared-minio - using shared-dev-network"; \
		NETWORK="shared-dev-network"; \
	elif docker ps --format '{{.Names}}' | grep -q "^govcontracts-minio$$"; then \
		echo "📡 Detected local MinIO - using govcontracts-network"; \
		NETWORK="gov-contracts-ai_govcontracts-network"; \
	else \
		echo "❌ No MinIO container found"; \
		exit 1; \
	fi; \
	\
	echo "🚀 Running bucket initialization script..."; \
	echo ""; \
	docker run --rm \
		--network $$NETWORK \
		--env-file .env \
		-v $$(pwd)/infrastructure/docker/minio/init-buckets.sh:/init-buckets.sh:ro \
		--entrypoint /bin/sh \
		minio/mc:latest \
		/init-buckets.sh
	@echo ""
	@echo "✅ Bucket initialization complete!"

# Smart startup - checks all services
up-smart:
	@echo "🚀 Smart startup - checking dependencies..."
	@echo ""
	@# Check PostgreSQL
	@PG_URL=$$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d= -f2 || echo "postgresql://admin:dev123@localhost:5433/govcontracts"); \
	PG_PORT=$$(echo $$PG_URL | grep -oP ':\d+/' | tr -d ':/' || echo "5433"); \
	PG_AVAILABLE=false; \
	PG_SCALE=""; \
	if nc -z -w2 localhost $$PG_PORT 2>/dev/null; then \
		if docker ps --format '{{.Names}}' | grep -q "govcontracts-postgres"; then \
			echo "✅ PostgreSQL: Using govcontracts-postgres (localhost:$$PG_PORT)"; \
			PG_AVAILABLE=true; \
		else \
			echo "✅ PostgreSQL: External service available (localhost:$$PG_PORT) - will skip local"; \
			PG_AVAILABLE=true; \
			PG_SCALE="--scale postgres=0"; \
		fi; \
	else \
		echo "❌ PostgreSQL: Not available - will start local"; \
	fi; \
	\
	REDIS_URL=$$(grep "^REDIS_URL=" .env 2>/dev/null | cut -d= -f2 || echo "redis://localhost:6380"); \
	REDIS_PORT=$$(echo $$REDIS_URL | grep -oP ':\d+' | tail -1 | tr -d ':' || echo "6380"); \
	REDIS_AVAILABLE=false; \
	REDIS_SCALE=""; \
	if nc -z -w2 localhost $$REDIS_PORT 2>/dev/null; then \
		if docker ps --format '{{.Names}}' | grep -q "govcontracts-redis"; then \
			echo "✅ Redis: Using govcontracts-redis (localhost:$$REDIS_PORT)"; \
			REDIS_AVAILABLE=true; \
		else \
			echo "✅ Redis: External service available (localhost:$$REDIS_PORT) - will skip local"; \
			REDIS_AVAILABLE=true; \
			REDIS_SCALE="--scale redis=0"; \
		fi; \
	else \
		echo "❌ Redis: Not available - will start local"; \
	fi; \
	\
	MINIO_ENDPOINT=$$(grep "^MINIO_ENDPOINT=" .env 2>/dev/null | cut -d= -f2 || echo "localhost:9000"); \
	MINIO_HOST=$$(echo $$MINIO_ENDPOINT | cut -d: -f1); \
	MINIO_PORT=$$(echo $$MINIO_ENDPOINT | cut -d: -f2); \
	MINIO_AVAILABLE=false; \
	MINIO_SCALE=""; \
	if nc -z -w2 $$MINIO_HOST $$MINIO_PORT 2>/dev/null; then \
		if docker ps --format '{{.Names}}' | grep -q "govcontracts-minio"; then \
			echo "✅ MinIO: Using govcontracts-minio ($$MINIO_ENDPOINT)"; \
			MINIO_AVAILABLE=true; \
		else \
			echo "✅ MinIO: External service available ($$MINIO_ENDPOINT) - will skip local"; \
			MINIO_AVAILABLE=true; \
			MINIO_SCALE="--scale minio=0 --scale minio-init=0"; \
		fi; \
	else \
		echo "❌ MinIO: Not available - will start local"; \
	fi; \
	\
	OPENSEARCH_AVAILABLE=false; \
	OPENSEARCH_SCALE=""; \
	if nc -z -w2 localhost 9201 2>/dev/null; then \
		if docker ps --format '{{.Names}}' | grep -q "govcontracts-opensearch"; then \
			echo "✅ OpenSearch: Using govcontracts-opensearch (localhost:9201)"; \
			OPENSEARCH_AVAILABLE=true; \
		else \
			echo "✅ OpenSearch: External service available (localhost:9201) - will skip local"; \
			OPENSEARCH_AVAILABLE=true; \
			OPENSEARCH_SCALE="--scale opensearch=0 --scale opensearch-dashboards=0"; \
		fi; \
	else \
		echo "❌ OpenSearch: Not available - will start local"; \
	fi; \
	\
	echo ""; \
	echo "🐳 Starting services..."; \
	SCALE_ARGS="$$PG_SCALE $$REDIS_SCALE $$MINIO_SCALE $$OPENSEARCH_SCALE"; \
	if [ -n "$$SCALE_ARGS" ]; then \
		echo "   Scale options: $$SCALE_ARGS"; \
		docker compose up -d $$SCALE_ARGS; \
	else \
		docker compose up -d; \
	fi
	@echo ""
	@echo "✅ Services running:"
	@if nc -z -w2 localhost 5433 2>/dev/null; then echo "  - PostgreSQL: localhost:5433"; fi
	@if nc -z -w2 localhost 6380 2>/dev/null; then echo "  - Redis: localhost:6380"; fi
	@if nc -z -w2 localhost 5000 2>/dev/null; then echo "  - MLflow: http://localhost:5000"; fi
	@if nc -z -w2 localhost 9000 2>/dev/null; then echo "  - MinIO API: http://localhost:9000"; fi
	@if nc -z -w2 localhost 9001 2>/dev/null; then echo "  - MinIO Console: http://localhost:9001"; fi
	@if nc -z -w2 localhost 8081 2>/dev/null; then echo "  - Airflow: http://localhost:8081"; fi
	@if nc -z -w2 localhost 9201 2>/dev/null; then echo "  - OpenSearch: http://localhost:9201"; fi
	@if nc -z -w2 localhost 5602 2>/dev/null; then echo "  - OpenSearch Dashboards: http://localhost:5602"; fi
	@echo ""
	@echo "🪣 Checking MinIO buckets..."
	@if ./scripts/check-buckets.sh 2>/dev/null; then \
		echo "  ✅ All buckets already exist"; \
	else \
		echo "  🔧 Initializing missing buckets..."; \
		$(MAKE) init-buckets > /dev/null 2>&1 && echo "  ✅ Buckets initialized!" || echo "  ⚠️  Failed to initialize buckets (run 'make init-buckets' manually)"; \
	fi

setup:
	@echo "Setting up Gov Contracts AI..."
	@ENDPOINT=$$(grep "^MINIO_ENDPOINT=" .env 2>/dev/null | cut -d= -f2 || echo "localhost:9000"); \
	HOST=$$(echo $$ENDPOINT | cut -d: -f1); \
	PORT=$$(echo $$ENDPOINT | cut -d: -f2); \
	if nc -z -w2 $$HOST $$PORT 2>/dev/null; then \
		echo "✅ MinIO already available - skipping"; \
		docker compose up -d postgres redis; \
	else \
		echo "Starting with local MinIO..."; \
		docker compose --profile minio up -d postgres redis minio; \
	fi
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
	@echo "  - MinIO API: http://minio:9000"
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
	@echo "  - MinIO API: http://minio:9000"
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
