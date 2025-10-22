# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gov Contracts AI** - AI-powered fraud detection system for Brazilian government procurement contracts. The system combines:
- **ML (XGBoost)**: Quantitative overpricing detection
- **AI Generative (Claude/GPT-4)**: Qualitative analysis and explainability
- **NLP (BERT)**: Analysis of restrictive clauses in procurement documents
- **RAG (Pinecone)**: Semantic search across procurement records

**Tech Stack**: Python 3.11+, FastAPI, Next.js 14, PostgreSQL, Redis, AWS (ECS Fargate)

## Repository Structure

```
gov-contracts-ai/
├── backend/           # FastAPI application
│   ├── app/          # API endpoints, ML inference, LLM integration
│   └── tests/        # Unit + integration tests
├── ml/               # ML development (notebooks, training, pipelines)
│   ├── data/         # Raw, processed, features (DVC tracked)
│   ├── notebooks/    # EDA and experimentation
│   ├── src/          # Training code
│   └── pipelines/    # Prefect orchestration flows
├── frontend/         # Next.js 14 application
│   ├── app/          # Pages (App Router)
│   ├── components/   # React components
│   └── lib/          # Utils, API client
├── infrastructure/   # Terraform IaC & Docker configs
├── docs/             # Technical documentation
└── scripts/          # Utility scripts
```

## Development Commands

### Backend (FastAPI)

**Setup:**
```bash
cd backend
poetry install
poetry shell
```

**Run locally:**
```bash
# With hot reload
uvicorn app.main:app --reload --port 8000

# Run tests
pytest
pytest --cov=app tests/
pytest -v tests/unit/
pytest -v tests/integration/

# Code quality
ruff check .
ruff format .
mypy app/
```

**Database:**
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Seed data
python scripts/seed_data.py
```

### ML Development

**Training pipeline:**
```bash
cd ml

# Run full pipeline with DVC
dvc repro

# Train model manually
python src/models/train.py

# Hyperparameter tuning
python src/models/tune.py

# Export to ONNX
python src/models/export.py
```

**Data pipeline:**
```bash
# Ingest new data
python src/data/ingestion.py

# Run data quality checks
python src/data/validation.py

# Build features
python src/features/build_features.py
```

**MLflow:**
```bash
# Start MLflow UI
mlflow ui --port 5000

# Track experiment
python src/models/train.py  # automatically logs to MLflow
```

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build
npm start

# Linting & formatting
npm run lint
npm run format

# Type checking
npm run type-check

# Tests
npm test
npm run test:watch
```

### Infrastructure

**Local development:**
```bash
# Start all services (Note: Use 'docker compose' not 'docker-compose')
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f [service]

# Rebuild specific service
docker compose up -d --build backend

# Use Makefile shortcuts
make up      # Start all services
make down    # Stop all services
make logs    # View logs
make setup   # First-time setup
```

**Service Endpoints:**
- PostgreSQL: `localhost:5432` (user: admin, pass: dev123, db: govcontracts)
- Redis: `localhost:6381` (Note: 6379 may be in use by other services)
- MLflow UI: `http://localhost:5000`
- MinIO Console: `http://localhost:9101` (credentials: minioadmin/minioadmin)
- MinIO API: `http://localhost:9100`

**Terraform:**
```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan changes
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply changes
terraform apply -var-file=environments/dev/terraform.tfvars

# Destroy resources
terraform destroy -var-file=environments/dev/terraform.tfvars
```

## Architecture Patterns

### Backend Structure

- **Clean Architecture**: Separation of concerns (API → Services → ML/AI → Data)
- **Dependency Injection**: Use FastAPI's `Depends()` for DB sessions, Redis, configs
- **Pydantic Models**: All API I/O uses Pydantic schemas for validation
- **Singleton Pattern**: ML models loaded once at startup, reused across requests
- **Caching Strategy**: Redis with 24h TTL for predictions
- **Async Workers**: Celery for background tasks (batch processing, retraining)

**Key modules:**
- `app/api/v1/endpoints/` - API route handlers
- `app/ml/` - ML inference and model loading
- `app/ai/` - LLM clients, prompts, RAG pipeline
- `app/services/` - Business logic layer
- `app/core/` - Configuration, logging, metrics

### ML Pipeline

**Data Lake Structure (S3):**
- `bronze/` - Raw data partitioned by date
- `silver/` - Cleaned and validated data
- `gold/` - Feature engineered datasets

**Training Flow:**
1. Data ingestion → Great Expectations validation
2. Feature engineering (30+ features)
3. Model training with MLflow tracking
4. Hyperparameter tuning with Optuna
5. Model export to ONNX for production
6. SHAP explainer training

**DVC Usage:**
- All datasets tracked with DVC
- Models versioned and stored in S3
- `dvc.yaml` defines the pipeline DAG
- `params.yaml` contains hyperparameters

### Frontend Patterns

- **Server Components**: Default for data fetching
- **TanStack Query**: Client-side caching and revalidation
- **Streaming**: Server-Sent Events for LLM explanations
- **shadcn/ui**: Accessible, customizable components
- **Type Safety**: Full TypeScript coverage

## Key Features Implementation

### ML Model Inference

Models are loaded at startup as singletons and cached in memory:
```python
# app/ml/model_loader.py pattern
class ModelLoader:
    _instance = None

    def load_model(self) -> onnxruntime.InferenceSession:
        # Load ONNX model
        # Apply preprocessing pipeline
        # Return inference session
```

Predictions use the preprocessing pipeline:
```python
# app/ml/inference.py pattern
async def predict(features: dict) -> Prediction:
    # Validate input
    # Preprocess features
    # Run ONNX inference
    # Post-process output
    # Cache result (Redis)
```

### LLM Integration

**Prompt Templates** (`app/ai/prompts.py`):
- Versioned templates for consistent outputs
- Include SHAP values in context
- Citizen-friendly language for explanations

**Streaming Responses**:
```python
# app/api/v1/endpoints/explanations.py pattern
@router.post("/explain-stream")
async def explain_stream(licitacao_id: str):
    # Server-Sent Events
    async def generate():
        async for chunk in llm_client.stream(...):
            yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### RAG System

**Pipeline** (`app/ai/rag.py`):
1. Document chunking (editais)
2. Generate embeddings (OpenAI ada-002)
3. Store in Pinecone with metadata
4. Retrieve top-k similar chunks
5. Generate response with LLM + context

**Optimization:**
- Cache embeddings for repeat queries
- Hybrid search (semantic + keyword)
- Relevance scoring and reranking

## Testing Strategy

### Backend Tests

**Structure:**
- `tests/unit/` - Pure functions, no external deps
- `tests/integration/` - Database, Redis, API endpoints
- `tests/e2e/` - Full pipeline tests

**Fixtures** (`tests/conftest.py`):
- `db_session` - Test database session
- `redis_client` - Test Redis instance
- `mock_model` - Mock ML model for fast tests
- `api_client` - TestClient for endpoint testing

**Target:** >85% code coverage

### Frontend Tests

- Vitest for unit tests
- React Testing Library for component tests
- MSW for API mocking
- Visual regression tests for critical flows

## Monitoring & Observability

### Metrics (Prometheus)

**Application metrics:**
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Model inference time
- Cache hit/miss rates
- LLM token usage and costs

**ML metrics:**
- Prediction distribution
- Data drift (Evidently AI)
- Model confidence scores
- SHAP value distributions

### Logging (Loguru)

Structured JSON logs with context:
```python
logger.info("prediction_made",
    licitacao_id=id,
    score=score,
    latency_ms=latency,
    model_version=version
)
```

### Error Tracking (Sentry)

- Automatic error capture
- Performance monitoring
- Release tracking
- User feedback integration

## Data Quality

### Great Expectations Suites

Located in `ml/configs/data_quality_config.yaml`:
- Schema validation (column types, names)
- Range checks (prices > 0, dates valid)
- Null value thresholds
- Distribution checks (detect drift)
- Referential integrity

Run before any training:
```bash
python src/data/validation.py --suite bronze_validation
```

## Deployment

### CI/CD Pipeline (.github/workflows/)

**On Pull Request:**
1. Linting (ruff, mypy, eslint)
2. Unit tests
3. Integration tests
4. Build Docker images

**On Merge to Main:**
1. Run full test suite
2. Build production images
3. Push to ECR
4. Deploy to staging (ECS)
5. Run smoke tests
6. Manual approval for prod
7. Blue-green deployment to prod

### Environment Variables

**Backend** (`.env` pattern):
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...
MLFLOW_TRACKING_URI=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SENTRY_DSN=...
```

**Frontend** (`.env.local` pattern):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENV=development
```

## Performance Requirements

- **API Latency**: p99 < 100ms (excluding LLM calls)
- **LLM Response**: First token < 500ms
- **Model Inference**: < 50ms
- **Database Queries**: < 20ms
- **Cache Hit Rate**: > 80%
- **Test Coverage**: > 85%

## Common Development Tasks

### Adding a New ML Feature

1. Define feature in `ml/src/features/build_features.py`
2. Update feature config `ml/configs/feature_config.yaml`
3. Add to DVC pipeline `ml/dvc.yaml`
4. Update preprocessing pipeline `backend/app/ml/preprocessing.py`
5. Retrain model and log to MLflow
6. Update API schema if needed

### Adding a New API Endpoint

1. Create endpoint in `backend/app/api/v1/endpoints/`
2. Define Pydantic schemas in `app/models/schemas.py`
3. Implement business logic in `app/services/`
4. Add tests in `tests/integration/test_api_*.py`
5. Update OpenAPI docs with examples
6. Add monitoring metrics

### Adding a New Frontend Page

1. Create page in `frontend/app/[route]/page.tsx`
2. Build components in `frontend/components/`
3. Create API hooks in `frontend/hooks/`
4. Add TypeScript types in `frontend/lib/types.ts`
5. Add to navigation if needed
6. Write component tests

## Important Conventions

### Python Code Style

- Use **ruff** for linting and formatting (configured in `pyproject.toml`)
- Type hints required for all functions
- Docstrings: Google style for public functions
- Async/await for I/O operations
- Pydantic for data validation

### TypeScript Code Style

- Strict mode enabled
- ESLint + Prettier for consistency
- Prefer functional components
- Custom hooks for reusable logic
- Explicit return types for functions

### Naming Conventions

**Python:**
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**TypeScript:**
- Files: `kebab-case.tsx`
- Components: `PascalCase`
- Functions/variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Types/Interfaces: `PascalCase`

### Git Workflow

- Branch naming: `feature/description`, `fix/description`, `chore/description`
- Commit messages: Conventional Commits format
- PR descriptions: Include context, testing done, screenshots if UI
- Squash merge to main

## Data Sources

### Government APIs

- **PNCP API**: Primary source for procurement data
- **Compras.gov.br**: Supplementary data
- **TCU datasets**: Historical reference data

### Market Prices

- **SINAPI**: Construction price index
- Ethical web scraping with rate limits
- Normalize categories for accurate comparison

## Security Considerations

- API keys in AWS Secrets Manager (production)
- Rate limiting on all endpoints
- Input validation with Pydantic
- SQL injection prevention via SQLAlchemy ORM
- CORS configured for frontend domain only
- HTTPS enforced in production

## Project Status

This is a portfolio/MVP project in **active development**. Current phase focuses on:
1. Setting up data pipeline
2. Building ML models
3. Implementing API and frontend
4. Deploying to AWS

Timeline: 5-month development roadmap (see README.md for details)
