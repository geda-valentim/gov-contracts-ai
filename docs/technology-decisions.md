# Technology Decisions & Justifications

This document explains the key technology choices made for the Gov Contracts AI project and the reasoning behind each decision.

---

## Table of Contents

1. [MLflow](#mlflow)
2. [Make](#make)
3. [Poetry](#poetry)
4. [Pydantic](#pydantic)
5. [FastAPI](#fastapi)
6. [Pre-commit](#pre-commit)
7. [Additional Technologies](#additional-technologies)

---

## MLflow

### What is MLflow?

MLflow is an open-source platform for managing the end-to-end machine learning lifecycle, including experimentation, reproducibility, deployment, and a central model registry.

### Why We Chose MLflow

#### ✅ Experiment Tracking
- **Problem**: ML experiments are hard to track - hyperparameters, metrics, artifacts scattered across notebooks
- **Solution**: MLflow automatically logs every experiment with parameters, metrics, and artifacts
- **Benefit**: Easy comparison of models to find the best performer

```python
# Example usage in our training pipeline
import mlflow

with mlflow.start_run():
    mlflow.log_params({"max_depth": 10, "learning_rate": 0.1})
    mlflow.log_metrics({"accuracy": 0.92, "precision": 0.89})
    mlflow.sklearn.log_model(model, "xgboost_model")
```

#### ✅ Model Registry
- **Problem**: Which model version is in production? Where is the trained model stored?
- **Solution**: Centralized model registry with versioning and staging (dev → staging → production)
- **Benefit**: Clear model lineage and easy rollback if needed

#### ✅ Reproducibility
- **Problem**: "It worked on my machine" - can't reproduce results from 3 months ago
- **Solution**: MLflow tracks code version, data version, dependencies, and environment
- **Benefit**: Any experiment can be reproduced exactly

#### ✅ Open Source & Self-Hosted
- **Alternative Considered**: Weights & Biases, Neptune.ai
- **Why MLflow**:
  - Free and open source (no vendor lock-in)
  - Self-hosted (data stays in our infrastructure)
  - Industry standard (widely adopted, good documentation)
  - Integrates with our PostgreSQL database

### Our MLflow Architecture

```yaml
MLflow Components:
  - Tracking Server: Runs at http://localhost:5000
  - Backend Store: PostgreSQL (metrics, parameters, tags)
  - Artifact Store: MinIO/S3 (models, plots, datasets)
  - Model Registry: Centralized model versioning
```

### Trade-offs

**Pros:**
- Complete ML lifecycle management
- Great UI for experiment comparison
- Easy model deployment
- Free and open source

**Cons:**
- Requires infrastructure setup (we solved with Docker)
- UI can be slow with thousands of runs (acceptable for our scale)
- Less features than commercial alternatives (but sufficient for our needs)

---

## Make

### What is Make?

Make is a build automation tool that uses Makefiles to define tasks and their dependencies. Originally created for compiling C programs, it's now widely used for any task automation.

### Why We Chose Make

#### ✅ Simple Task Automation
- **Problem**: Developers need to remember complex Docker and development commands
- **Solution**: One simple command: `make up`, `make test`, `make deploy`
- **Benefit**: Reduced cognitive load, faster onboarding

```makefile
# Our Makefile commands
make up      # docker compose up -d
make down    # docker compose down
make test    # cd backend && poetry run pytest
make lint    # Run code quality checks
```

#### ✅ Cross-Platform Compatibility
- **Alternative Considered**: Shell scripts (`.sh`), Task runners (npm scripts)
- **Why Make**:
  - Available on all Unix systems (Linux, macOS, WSL)
  - Simple syntax that anyone can read
  - Self-documenting (`make help` shows all commands)
  - Handles dependencies between tasks

#### ✅ Developer Experience
- **Problem**: New developers spend hours setting up the project
- **Solution**: `make setup` does everything automatically
- **Benefit**: From zero to running app in one command

### Our Make Commands

```makefile
make help     # Show all available commands
make setup    # First-time environment setup
make up       # Start all Docker services
make down     # Stop all services
make logs     # View service logs
make test     # Run all tests with coverage
make lint     # Check code quality
make format   # Auto-format code
make clean    # Clean up containers and caches
```

### Trade-offs

**Pros:**
- Universal tool (installed everywhere)
- Easy to learn and maintain
- Self-documenting
- Efficient (only runs what changed)

**Cons:**
- Tab-sensitive syntax (can be annoying)
- Limited Windows support (solved by WSL)
- Not as powerful as specialized task runners (sufficient for our needs)

---

## Poetry

### What is Poetry?

Poetry is a modern dependency management and packaging tool for Python, designed to replace pip, virtualenv, and setup.py with a single tool.

### Why We Chose Poetry

#### ✅ Deterministic Dependency Resolution
- **Problem**: `pip install` can install different versions on different machines → "works on my machine"
- **Solution**: Poetry creates a `poetry.lock` file with exact versions
- **Benefit**: Everyone on the team uses identical dependencies

```toml
# pyproject.toml - high-level dependencies
[dependencies]
fastapi = ">=0.109.0,<0.110.0"
pydantic = ">=2.5.0,<3.0.0"

# poetry.lock - exact resolved versions (auto-generated)
# fastapi==0.109.2
# pydantic==2.5.3
# ... and all transitive dependencies
```

#### ✅ Modern Dependency Management
- **Alternative Considered**: pip + requirements.txt, pipenv, conda
- **Why Poetry**:
  - Resolves dependency conflicts automatically
  - Separates dev and production dependencies
  - Faster than pip (parallel downloads, caching)
  - Single `pyproject.toml` file (PEP 518 standard)

#### ✅ Virtual Environment Management
- **Problem**: Manually creating and activating virtualenvs is error-prone
- **Solution**: Poetry handles virtualenvs automatically
- **Benefit**: `poetry install` creates env, `poetry shell` activates it

```bash
# Old way (pip)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Poetry way
poetry install  # Creates venv + installs all deps
poetry shell    # Activates venv
```

#### ✅ Dependency Groups
- **Problem**: Don't want to install test/dev dependencies in production
- **Solution**: Poetry's dependency groups
- **Benefit**: Smaller production images, faster deploys

```toml
[dependency-groups]
dev = [
    "pytest",
    "ruff",
    "mypy",
    "pre-commit"
]

# Install production only
poetry install --only main

# Install with dev tools
poetry install --with dev
```

### Our Poetry Workflow

```bash
# Initial setup
poetry install              # Install all dependencies

# Add new dependency
poetry add fastapi          # Production dependency
poetry add --group dev pytest  # Dev dependency

# Update dependencies
poetry update               # Update all
poetry update fastapi       # Update specific package

# Run commands in poetry env
poetry run python script.py
poetry run pytest
poetry shell                # Activate virtualenv
```

### Trade-offs

**Pros:**
- Deterministic builds (same deps everywhere)
- Fast and modern
- Great dependency resolution
- Single configuration file
- Industry trend (replacing pip)

**Cons:**
- Learning curve for pip users (acceptable)
- Slower initial install than pip (cached after first run)
- Extra tool to install (one-time setup)

---

## Pydantic

### What is Pydantic?

Pydantic is a data validation library that uses Python type hints to validate data at runtime. It's the most widely used data validation library for Python.

### Why We Chose Pydantic

#### ✅ Automatic Data Validation
- **Problem**: API receives invalid data → crashes in production
- **Solution**: Pydantic validates all inputs automatically
- **Benefit**: Catch errors early with clear error messages

```python
from pydantic import BaseModel, Field, validator

class LicitacaoRequest(BaseModel):
    cnpj: str = Field(..., pattern=r'^\d{14}$')
    valor: float = Field(..., gt=0)
    categoria: str

    @validator('cnpj')
    def validate_cnpj(cls, v):
        # Custom validation logic
        if not is_valid_cnpj(v):
            raise ValueError('CNPJ inválido')
        return v

# Usage - automatic validation
request = LicitacaoRequest(
    cnpj="12345678901234",
    valor=1000.50,
    categoria="construção"
)
# ✅ Valid - proceeds

request = LicitacaoRequest(
    cnpj="invalid",
    valor=-100,
    categoria="construção"
)
# ❌ Raises ValidationError with detailed message
```

#### ✅ Type Safety
- **Problem**: Python is dynamically typed → runtime type errors
- **Solution**: Pydantic enforces types at runtime
- **Benefit**: Catch type errors before they cause bugs

```python
class Prediction(BaseModel):
    score: float
    is_fraud: bool
    confidence: float

# Type coercion (when safe)
pred = Prediction(score="0.85", is_fraud="true", confidence=0.92)
# Converts to: score=0.85 (float), is_fraud=True (bool)

# Type error (when unsafe)
pred = Prediction(score="invalid", is_fraud=True, confidence=0.92)
# ❌ ValidationError: score must be float
```

#### ✅ FastAPI Integration
- **Problem**: Need to validate API requests/responses and generate docs
- **Solution**: FastAPI is built on Pydantic
- **Benefit**: Automatic API docs + validation in one schema

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class PredictRequest(BaseModel):
    licitacao_id: str
    features: dict

class PredictResponse(BaseModel):
    score: float
    is_fraud: bool

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    # Request automatically validated
    # Response automatically validated
    # OpenAPI docs automatically generated
    return PredictResponse(score=0.85, is_fraud=True)
```

#### ✅ Settings Management
- **Problem**: Environment variables are strings, need type conversion and validation
- **Solution**: Pydantic Settings
- **Benefit**: Type-safe, validated configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    mlflow_tracking_uri: str
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

# Auto-loads from environment or .env file
settings = Settings()
# ✅ All values validated and typed correctly
```

### Our Pydantic Use Cases

1. **API Schemas**: Request/response validation
2. **Database Models**: SQLAlchemy model validation
3. **Configuration**: Type-safe settings from env vars
4. **ML Pipelines**: Validate feature inputs before prediction
5. **Data Quality**: Validate data ingestion

### Trade-offs

**Pros:**
- Automatic validation with clear errors
- Type safety at runtime
- Perfect FastAPI integration
- Excellent documentation
- Very fast (Rust backend in v2)

**Cons:**
- Slight learning curve for advanced features (acceptable)
- Runtime overhead for validation (negligible, ~microseconds)
- Pydantic v2 breaking changes (we use v2 from start)

---

## FastAPI

### What is FastAPI?

FastAPI is a modern, high-performance web framework for building APIs with Python, based on standard Python type hints.

### Why We Chose FastAPI

#### ✅ Automatic API Documentation
- **Problem**: Writing and maintaining API docs is tedious and often outdated
- **Solution**: FastAPI auto-generates interactive docs from code
- **Benefit**: Always up-to-date docs, can test API in browser

```python
@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict if a government contract has overpricing.

    - **licitacao_id**: Unique identifier of the procurement
    - **features**: Dictionary of features for prediction
    """
    return {"score": 0.85, "is_fraud": True}

# Generates:
# - Swagger UI at /docs
# - ReDoc at /redoc
# - OpenAPI JSON at /openapi.json
```

#### ✅ High Performance
- **Alternative Considered**: Flask, Django, Sanic
- **Why FastAPI**:
  - **Speed**: One of the fastest Python frameworks (comparable to Node.js)
  - **Async**: Native async/await support (handles many concurrent requests)
  - **Efficiency**: Lower latency, higher throughput

**Benchmark Results** (requests/second):
- FastAPI: ~25,000 req/s
- Flask: ~3,000 req/s
- Django: ~1,500 req/s

#### ✅ Built on Modern Standards
- **ASGI**: Asynchronous Server Gateway Interface (vs old WSGI)
- **Type Hints**: Uses Python 3.10+ features
- **Pydantic**: Automatic validation
- **Starlette**: Battle-tested ASGI toolkit underneath

```python
# Async endpoints for I/O operations
@app.get("/licitacoes/{id}")
async def get_licitacao(id: str, db: Session = Depends(get_db)):
    # Can handle many concurrent requests
    licitacao = await db.query(Licitacao).filter_by(id=id).first()
    return licitacao

# Background tasks
from fastapi import BackgroundTasks

@app.post("/predict")
async def predict(request: PredictRequest, background: BackgroundTasks):
    # Return immediately
    background.add_task(log_prediction, request)
    return {"status": "processing"}
```

#### ✅ Developer Experience
- **Problem**: Slow development with repetitive boilerplate
- **Solution**: FastAPI reduces boilerplate by 40%
- **Benefit**: Faster development, fewer bugs

**Example - Parameter Validation:**
```python
# Flask - manual validation
@app.route('/items/<int:item_id>')
def get_item(item_id):
    if not isinstance(item_id, int):
        return {"error": "Invalid ID"}, 400
    if item_id < 0:
        return {"error": "ID must be positive"}, 400
    # ... actual logic

# FastAPI - automatic validation
@app.get("/items/{item_id}")
async def get_item(item_id: int = Path(..., gt=0)):
    # Validation automatic, just write logic
    return {"item_id": item_id}
```

#### ✅ Dependency Injection
- **Problem**: Managing database connections, auth, config across endpoints
- **Solution**: FastAPI's dependency injection system
- **Benefit**: Clean, testable, reusable code

```python
# Define dependencies
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    return decode_token(token)

# Use in endpoints
@app.get("/predictions")
async def get_predictions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return await db.query(Prediction).filter_by(user_id=user.id).all()
```

### Our FastAPI Architecture

```
FastAPI Application Structure:
├── app/
│   ├── main.py              # FastAPI app instance
│   ├── api/                 # API routes
│   │   ├── deps.py          # Dependencies (DB, auth)
│   │   └── v1/
│   │       └── endpoints/   # API endpoints
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   └── security.py      # Auth logic
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── ml/
│   │   └── inference.py     # ML model serving
│   └── ai/
│       └── llm_client.py    # LLM integration
```

### Trade-offs

**Pros:**
- Blazing fast performance
- Automatic API docs (always current)
- Modern async support
- Excellent type safety
- Great developer experience
- Production-ready (Uber, Netflix use it)

**Cons:**
- Newer than Flask/Django (less Stack Overflow answers)
- Async requires understanding (we provide training)
- Breaking changes in early versions (stable now at 0.109+)

---

## Pre-commit

### What is Pre-commit?

Pre-commit is a framework for managing git hooks that run before each commit, automatically checking and fixing code issues.

### Why We Chose Pre-commit

#### ✅ Automated Code Quality
- **Problem**: Developers forget to run linters, formatters, tests before committing
- **Solution**: Pre-commit runs checks automatically on `git commit`
- **Benefit**: Bad code never enters the repository

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff           # Linting
      - id: ruff-format    # Formatting

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy           # Type checking
```

**What happens on commit:**
```bash
$ git commit -m "Add new feature"

ruff.....................................Failed
- hook id: ruff
- exit code: 1

Found 3 errors (3 fixed, 0 remaining).

# Auto-fixed! Just commit again:
$ git commit -m "Add new feature"

ruff.....................................Passed ✅
ruff-format..............................Passed ✅
mypy.....................................Passed ✅

[main abc123] Add new feature
```

#### ✅ Consistent Code Style Across Team
- **Problem**: Each developer has different code style preferences
- **Solution**: Pre-commit enforces the same style for everyone
- **Benefit**: No style debates in code reviews, clean git history

**Checks we run:**
1. **Ruff** - Linting (catches bugs, bad patterns)
2. **Ruff Format** - Code formatting (consistent style)
3. **Mypy** - Type checking (catch type errors)
4. **Trailing whitespace** - Remove extra spaces
5. **End-of-file** - Ensure files end with newline
6. **YAML validation** - Check config files
7. **Large files** - Prevent committing huge files

#### ✅ Fast Feedback Loop
- **Problem**: CI fails after push → waste time waiting
- **Solution**: Catch issues locally before push
- **Benefit**: Faster development, less CI failures

```
Without pre-commit:
  Write code → Commit → Push → Wait 5min → CI fails → Fix → Repeat

With pre-commit:
  Write code → Commit (auto-fixed) → Push → CI passes ✅
```

#### ✅ Language Agnostic
- **Alternative Considered**: Custom git hooks, Husky (JS-only)
- **Why Pre-commit**:
  - Works with any language (Python, JS, Go, etc.)
  - Easy to share across team (`.pre-commit-config.yaml`)
  - Automatic hook installation
  - Large ecosystem of hooks

### Our Pre-commit Setup

```bash
# Installation (one-time per developer)
cd backend
poetry add --group dev pre-commit
poetry run pre-commit install

# Manual run (optional)
poetry run pre-commit run --all-files

# Automatic run (on every commit)
git commit -m "message"  # Hooks run automatically!

# Update hooks to latest versions
poetry run pre-commit autoupdate
```

### What Gets Checked

| Hook | What it does | Auto-fix? |
|------|--------------|-----------|
| **ruff** | Finds bugs, code smells, unused imports | ✅ Yes |
| **ruff-format** | Formats code (like Black) | ✅ Yes |
| **mypy** | Type checking | ❌ No (shows errors) |
| **trailing-whitespace** | Removes trailing spaces | ✅ Yes |
| **end-of-file-fixer** | Adds newline at end of files | ✅ Yes |
| **check-yaml** | Validates YAML syntax | ❌ No (shows errors) |
| **check-merge-conflict** | Detects merge conflict markers | ❌ No (shows errors) |
| **check-added-large-files** | Prevents files >1MB | ❌ No (blocks commit) |

### Trade-offs

**Pros:**
- Automated quality enforcement
- Catches issues before CI
- Team-wide consistency
- Easy to set up and maintain
- Saves code review time

**Cons:**
- Slightly slower commits (adds ~2 seconds)
- Can be bypassed with `--no-verify` (we discourage this)
- Initial setup required per developer (one command)

---

## Additional Technologies

### Why These Technologies?

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Docker Compose** | Local development environment | Consistent dev environment across team |
| **PostgreSQL** | Primary database | ACID compliance, JSON support, battle-tested |
| **Redis** | Caching & message broker | Fast caching, Pub/Sub for async tasks |
| **MinIO** | Local S3 storage | S3-compatible local development |
| **Ruff** | Linting + formatting | 100x faster than Pylint, all-in-one tool |
| **Mypy** | Static type checking | Catch type errors before runtime |
| **Pytest** | Testing framework | Industry standard, powerful fixtures |
| **XGBoost** | ML model | Best for tabular data, interpretable |
| **Anthropic Claude** | LLM for explanations | Best Portuguese support, less censored |
| **Pinecone** | Vector database | Easy to use, generous free tier |

---

## Technology Decision Matrix

### How We Evaluate Technologies

We use these criteria to evaluate any technology:

1. **Developer Experience** (30%)
   - Easy to learn and use?
   - Good documentation?
   - Active community?

2. **Performance** (25%)
   - Fast enough for our scale?
   - Handles expected load?

3. **Maintainability** (20%)
   - Easy to debug?
   - Good error messages?
   - Long-term support?

4. **Cost** (15%)
   - Open source preferred
   - Avoid vendor lock-in
   - Total cost of ownership

5. **Team Fit** (10%)
   - Matches team expertise?
   - Good for portfolio/resume?

### Example: Why FastAPI over Flask?

| Criteria | FastAPI | Flask | Winner |
|----------|---------|-------|--------|
| **Developer Experience** | 9/10 (auto docs, type hints) | 7/10 (manual docs) | FastAPI |
| **Performance** | 10/10 (async, fast) | 6/10 (sync, slower) | FastAPI |
| **Maintainability** | 9/10 (type safety) | 7/10 (less validation) | FastAPI |
| **Cost** | 10/10 (open source) | 10/10 (open source) | Tie |
| **Team Fit** | 9/10 (modern, resume-worthy) | 8/10 (traditional) | FastAPI |
| **Total** | **47/50** | **38/50** | **FastAPI** |

---

## Learning Resources

### For New Developers

**MLflow:**
- Official Docs: https://mlflow.org/docs/latest/index.html
- Tutorial: MLflow in 5 minutes

**Poetry:**
- Official Docs: https://python-poetry.org/docs/
- Quick start: `poetry install && poetry shell`

**Pydantic:**
- Official Docs: https://docs.pydantic.dev/
- Try it: https://docs.pydantic.dev/playground/

**FastAPI:**
- Official Tutorial: https://fastapi.tiangolo.com/tutorial/
- Interactive docs at: http://localhost:8000/docs

**Pre-commit:**
- Official Docs: https://pre-commit.com/
- Available hooks: https://pre-commit.com/hooks.html

---

## Contributing

When proposing a new technology, please:

1. Explain the problem it solves
2. Compare with alternatives
3. Show proof of concept
4. Document trade-offs
5. Get team approval

**Template for Technology Proposals:**
```markdown
## Proposed Technology: [Name]

### Problem
[What problem does this solve?]

### Solution
[How does this technology solve it?]

### Alternatives Considered
- Option 1: [Pros/Cons]
- Option 2: [Pros/Cons]

### Proof of Concept
[Link to working example]

### Trade-offs
**Pros:**
- ...

**Cons:**
- ...

### Decision
[Approved/Rejected + reasoning]
```

---

## Questions?

For questions about technology decisions:
1. Check this document first
2. Ask in team chat
3. Create a GitHub discussion
4. Update this doc with the answer (so others benefit)

---

*Last Updated: October 2025*
*Maintained by: Dev Team*
