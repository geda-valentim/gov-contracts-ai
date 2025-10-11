# Makefile
.PHONY: help setup up down logs test lint format clean

help:
	@echo "Gov Contracts AI - Available commands:"
	@echo "  make setup    - First time setup"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linting"
	@echo "  make format   - Format code"

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
	@echo "  - MinIO: http://localhost:9001"

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && poetry run pytest tests/ -v --cov=app

lint:
	cd backend && poetry run ruff check app/ tests/

format:
	cd backend && poetry run ruff format app/ tests/

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
