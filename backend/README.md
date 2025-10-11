# Gov Contracts AI - Backend API

FastAPI backend for the Gov Contracts AI fraud detection system.

## Setup

```bash
poetry install
poetry shell
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
pytest --cov=app
```
