# Makefile
.PHONY: help setup up down logs test test-cov test-html lint format clean backend-shell

help:
	@echo "Gov Contracts AI - Available commands:"
	@echo ""
	@echo "🐳 Docker Services:"
	@echo "  make setup      - First time setup"
	@echo "  make up         - Start all services"
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
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6381"
	@echo "  - MLflow: http://localhost:5000"
	@echo "  - MinIO: http://localhost:9101"

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
