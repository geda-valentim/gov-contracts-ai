# 🏛️ Gov Contracts AI

> **Sistema Open Source de Auditoria em Licitações Governamentais Brasileiras**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-black)]()
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)]()
[![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-brightgreen)]()

**Gerando achados de auditoria automatizados em licitações públicas** usando **Machine Learning** (XGBoost) + **IA Generativa** (Llama 3.1) + **NLP** (BERT).

---

## 💡 Proposta de Valor

**Problema:** Bilhões perdidos anualmente em irregularidades em licitações (TCU)

**Solução:** Análise automatizada de 50k+ licitações com 85%+ de precisão
**Impacto:** Auditoria proativa antes da homologação, explicações em português, 100% auditável

---

## 🌟 Diferenciais

| Aspecto | Soluções Existentes | Gov Contracts AI |
|---------|---------------------|------------------|
| **Open Source** | ❌ Proprietário | ✅ GPL v3.0 |
| **Soberania** | ❌ Cloud externas | ✅ On-premises |
| **IA Generativa** | ❌ Apenas ML | ✅ LLM + ML híbrido |
| **Editais PDF** | ❌ Não analisa | ✅ NLP avançado |
| **Preços Mercado** | ❌ Sem referência | ✅ Web scraping |
| **Explicabilidade** | ⚠️ Básica | ✅ SHAP + LLM |

---

## 📊 Portfolio Project - ML/AI Engineer

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Objetivos e Justificativas](#objetivos-e-justificativas)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Stack Tecnológica Completa](#stack-tecnológica-completa)
5. [Estrutura do Projeto](#estrutura-do-projeto)
6. [Roadmap Detalhado - 5 Meses](#roadmap-detalhado)
7. [Guia de Implementação Fase por Fase](#guia-de-implementação)
8. [Critérios de Sucesso](#critérios-de-sucesso)
9. [Documentação e Apresentação](#documentação-e-apresentação)
10. [Próximos Passos Imediatos](#próximos-passos-imediatos)

---

## 🎯 Visão Geral

### Problema de Negócio

O Brasil gasta anualmente mais de **R$ 500 bilhões** em licitações públicas. Estudos do TCU (Tribunal de Contas da União) indicam que até **15% dos contratos** apresentam indícios de sobrepreço, representando bilhões em desperdício de recursos públicos.

### Solução Proposta

Sistema end-to-end que combina:
- **ML Clássico** (XGBoost) para detecção quantitativa de anomalias de preço
- **AI Generativa** (LLMs) para análise qualitativa de editais e explicabilidade
- **NLP** para identificar cláusulas restritivas e padrões textuais suspeitos
- **RAG** para busca semântica e análise comparativa

### Valor para Portfolio

Este projeto demonstra proficiência em:
- ✅ **ML Engineering**: pipelines, feature engineering, deploy, MLOps
- ✅ **AI Engineering**: LLMs, RAG, vector databases, prompt engineering
- ✅ **Data Engineering**: ETL, data quality, orquestração
- ✅ **Full Stack**: API REST, frontend moderno, UX
- ✅ **DevOps**: Docker, CI/CD, cloud, monitoring

---

## 🎯 Objetivos e Justificativas

### Objetivo Principal
**Conseguir primeiro emprego como ML Engineer ou AI Engineer** em empresas que valorizam:
- Projetos end-to-end completos
- Código production-ready
- Conhecimento híbrido (ML clássico + AI generativa)
- Impacto social mensurável

### Por que este projeto?

#### ✅ Problema Real e Relevante
- **Impacto social**: combate à corrupção e desperdício público
- **Dados acessíveis**: APIs governamentais abertas (PNCP, Compras.gov.br)
- **Mensurável**: métricas claras de sucesso (economia estimada)

#### ✅ Complexidade Adequada
- **Não é trivial**: requer feature engineering sofisticado
- **Não é impossível**: escopo realizável em 5 meses
- **Escalável**: pode adicionar features progressivamente

#### ✅ Diferenciação no Mercado
- **Maioria dos portfolios**: projetos Kaggle ou tutoriais genéricos
- **Seu projeto**: problema único, dados brasileiros, impacto real
- **Híbrido ML+AI**: 95% dos júniores focam em apenas uma área

#### ✅ Demonstra Maturidade Técnica
- **MLOps**: não é "notebook sujo", é sistema em produção
- **Testes**: coverage >85%
- **Documentação**: nível profissional
- **Deploy**: aplicação rodando em cloud pública

---

## 🏗️ Arquitetura do Sistema

### Diagrama de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA DE INGESTÃO                           │
├─────────────────────────────────────────────────────────────────┤
│  Data Sources:                                                  │
│  • PNCP API (licitações oficiais)                               │
│  • Compras.gov.br API                                           │
│  • Web scraping (preços de mercado - ético)                     │
│  • TCU datasets (históricos)                                    │
│                                                                 │
│  Schedulers:                                                    │
│  • Prefect Flows (orquestração)                                 │
│  • Daily ingestion (licitações novas)                           │
│  • Weekly refresh (preços mercado)                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  CAMADA DE ARMAZENAMENTO                        │
├─────────────────────────────────────────────────────────────────┤
│  Data Lake (AWS S3):                                            │
│  ├── bronze/ (raw data, particionado por data)                  │
│  ├── silver/ (cleaned, validated)                               │
│  └── gold/ (features, aggregations)                             │
│                                                                 │
│  Data Warehouse (PostgreSQL):                                   │
│  ├── staging (dados brutos)                                     │
│  ├── dwh (schema estrela otimizado)                             │
│  └── ml_features (tabelas desnormalizadas)                      │
│                                                                 │
│  Vector Store (Pinecone):                                       │
│  └── editais embeddings (busca semântica)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              CAMADA DE PROCESSAMENTO                            │
├─────────────────────────────────────────────────────────────────┤
│  ETL Pipelines:                                                 │
│  • Data validation (Great Expectations)                         │
│  • Data cleaning (Pandas/Polars)                                │
│  • Feature engineering (30+ features)                           │
│  • DVC tracking (versionamento)                                 │
│                                                                 │
│  Data Quality:                                                  │
│  • Schema validation                                            │
│  • Null checks                                                  │
│  • Outlier detection                                            │
│  • Drift monitoring                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAMADA ML TRADICIONAL                           │
├─────────────────────────────────────────────────────────────────┤
│  Training Pipeline:                                             │
│  • Baseline models (Logistic Reg, Random Forest)                │
│  • Production models (XGBoost, LightGBM)                        │
│  • Hyperparameter tuning (Optuna)                               │
│  • Cross-validation (stratified)                                │
│                                                                 │
│  Experiment Tracking:                                           │
│  • MLflow (metrics, params, artifacts)                          │
│  • Model registry (staging/production)                          │
│  • Model versioning                                             │
│                                                                 │
│  Model Artifacts:                                               │
│  • Trained models (pickle/ONNX)                                 │
│  • Feature transformers                                         │
│  • SHAP explainer                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAMADA AI GENERATIVA                            │
├─────────────────────────────────────────────────────────────────┤
│  LLM Services:                                                  │
│  • Claude API (explicações para cidadãos)                       │
│  • GPT-4 (análise complexa de editais)                          │
│  • Prompt templates versionados                                 │
│  • Token usage tracking                                         │
│                                                                 │
│  NLP Pipeline:                                                  │
│  • BERT Portuguese (classificação cláusulas)                    │
│  • Named Entity Recognition (empresas, valores)                 │
│  • Sentiment analysis (linguagem vaga/específica)               │
│                                                                 │
│  RAG System:                                                    │
│  • Document chunking (editais)                                  │
│  • Embeddings (OpenAI ada-002)                                  │
│  • Vector search (Pinecone)                                     │
│  • Context retrieval + LLM generation                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA DE SERVIÇO                            │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application:                                           │
│  ├── /v1/predict (ML model inference)                           │
│  ├── /v1/explain (SHAP values + LLM explanation)                │
│  ├── /v1/search (RAG - busca semântica)                         │
│  ├── /v1/analyze-edital (NLP analysis)                          │
│  ├── /v1/batch (processamento em lote)                          │
│  └── /v1/health (healthcheck + metrics)                         │
│                                                                 │
│  Background Workers:                                            │
│  • Celery (async tasks)                                         │
│  • Redis (message broker + cache)                               │
│  • Scheduled jobs (retraining, reports)                         │
│                                                                 │
│  Caching Layer:                                                 │
│  • Redis (predictions cache - 24h TTL)                          │
│  • Model loading (in-memory)                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND                                   │
├─────────────────────────────────────────────────────────────────┤
│  Next.js 14 Application:                                        │
│  • Server Components (performance)                              │
│  • Streaming responses (LLM real-time)                          │
│  • shadcn/ui (componentes modernos)                             │
│  • Tailwind CSS (styling)                                       │
│                                                                 │
│  Features:                                                      │
│  ├── Dashboard (KPIs, alertas)                                  │
│  ├── Busca/Filtros (licitações)                                 │
│  ├── Análise Individual (detalhes + explicação)                 │
│  ├── Comparativo (licitação vs mercado)                         │
│  ├── Explicabilidade Visual (SHAP plots)                        │
│  ├── Busca Semântica (RAG interface)                            │
│  └── Relatórios (PDF export)                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAMADA DE OBSERVABILIDADE                       │
├─────────────────────────────────────────────────────────────────┤
│  Application Monitoring:                                        │
│  • Prometheus (métricas)                                        │
│  • Grafana (dashboards)                                         │
│  • Sentry (error tracking)                                      │
│  • CloudWatch Logs                                              │
│                                                                 │
│  ML Monitoring:                                                 │
│  • Evidently AI (data/concept drift)                            │
│  • Custom metrics (precision, recall por categoria)             │
│  • Model performance tracking                                   │
│  • A/B test analytics (se aplicável)                            │
│                                                                 │
│  Cost Tracking:                                                 │
│  • AWS costs por serviço                                        │
│  • LLM API costs (tokens)                                       │
│  • Alert thresholds                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  INFRAESTRUTURA                                 │
├─────────────────────────────────────────────────────────────────┤
│  AWS Services:                                                  │
│  • ECS Fargate (containers serverless)                          │
│  • RDS PostgreSQL (managed database)                            │
│  • S3 (data lake + static assets)                               │
│  • ElastiCache Redis (cache + queue)                            │
│  • Application Load Balancer                                    │
│  • CloudWatch (logs + metrics)                                  │
│  • Secrets Manager (API keys)                                   │
│                                                                 │
│  Infrastructure as Code:                                        │
│  • Terraform (provisionamento)                                  │
│  • Docker (containerização)                                     │
│  • Docker Compose (dev local)                                   │
│                                                                 │
│  CI/CD:                                                         │
│  • GitHub Actions (pipelines)                                   │
│  • Automated testing                                            │
│  • Linting + type checking                                      │
│  • Auto-deploy (staging/prod)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Justificativas Arquiteturais

#### Por que esta arquitetura?

**1. Separação de Camadas (Clean Architecture)**
- **Maintainability**: cada camada pode evoluir independentemente
- **Testability**: fácil mockar dependências
- **Scalability**: escala horizontalmente quando necessário

**2. Data Lake (Bronze/Silver/Gold)**
- **Bronze**: dados brutos preservados (audit trail)
- **Silver**: dados limpos (90% dos casos de uso)
- **Gold**: features agregadas (performance otimizada)
- **Justificativa**: padrão industry para data pipelines modernos

**3. Dual ML + AI**
- **ML Tradicional**: alta precisão em detecção quantitativa
- **AI Generativa**: explicabilidade e análise qualitativa
- **Justificativa**: combina o melhor dos dois mundos

**4. Microserviços Leves**
- **FastAPI**: único backend (não overengineering)
- **Celery**: tarefas async sem criar serviços separados
- **Justificativa**: simplicidade para projeto solo, fácil evoluir depois

**5. Cloud-Native**
- **ECS Fargate**: sem gerenciar servidores
- **RDS**: database managed (backups automáticos)
- **Justificativa**: foco no código, não na infra

---

## 🛠️ Stack Tecnológica Completa

### Backend & ML (Python 3.11+)

```toml
[tool.poetry.dependencies]
python = "^3.11"

# ===== CORE WEB FRAMEWORK =====
fastapi = "^0.109.0"              # API REST moderna
uvicorn = {extras = ["standard"], version = "^0.27.0"}  # ASGI server
pydantic = "^2.5.0"               # Validação de dados
pydantic-settings = "^2.1.0"      # Configuração via env vars

# ===== DATA PROCESSING =====
pandas = "^2.2.0"                 # Manipulação de dados
polars = "^0.20.0"                # Alternativa rápida ao pandas
pyarrow = "^15.0.0"               # Formato columnar eficiente
numpy = "^1.26.0"                 # Computação numérica

# ===== ML TRADICIONAL =====
scikit-learn = "^1.4.0"           # Algoritmos baseline
xgboost = "^2.0.3"                # Modelo principal (gradient boosting)
lightgbm = "^4.3.0"               # Alternativa rápida ao XGBoost
optuna = "^3.5.0"                 # Hyperparameter tuning automático
imbalanced-learn = "^0.12.0"      # Lidar com classes desbalanceadas

# ===== MLOPS =====
mlflow = "^2.10.0"                # Tracking + model registry
dvc = {extras = ["s3"], version = "^3.45.0"}  # Versionamento dados/modelos
great-expectations = "^0.18.0"     # Data quality checks

# ===== EXPLICABILIDADE =====
shap = "^0.44.0"                  # SHAP values (model explainability)
lime = "^0.2.0.1"                 # Alternativa ao SHAP

# ===== MODEL SERVING =====
onnx = "^1.15.0"                  # Formato otimizado
onnxruntime = "^1.17.0"           # Inferência rápida

# ===== AI GENERATIVA =====
anthropic = "^0.18.0"             # Claude API
openai = "^1.12.0"                # GPT-4 + embeddings
langchain = "^0.1.0"              # Framework LLM
langchain-community = "^0.0.20"   # Integrações community
pinecone-client = "^3.0.0"        # Vector database

# ===== NLP =====
transformers = "^4.37.0"          # Hugging Face models
sentence-transformers = "^2.3.0"   # Embeddings otimizados
torch = "^2.2.0"                  # PyTorch (backend)
spacy = "^3.7.0"                  # NLP industrial

# ===== DATABASE & CACHE =====
sqlalchemy = "^2.0.25"            # ORM
psycopg2-binary = "^2.9.9"        # PostgreSQL driver
alembic = "^1.13.0"               # Migrations
redis = "^5.0.1"                  # Cache + message broker

# ===== ASYNC TASKS =====
celery = "^5.3.6"                 # Distributed task queue
flower = "^2.0.1"                 # Celery monitoring UI

# ===== WEB SCRAPING =====
httpx = "^0.26.0"                 # HTTP client async
beautifulsoup4 = "^4.12.0"        # HTML parsing
scrapy = "^2.11.0"                # Web scraping framework (se necessário)

# ===== ORCHESTRATION =====
prefect = "^2.14.0"               # Workflow orchestration
prefect-aws = "^0.4.0"            # AWS integrations

# ===== MONITORING =====
prometheus-client = "^0.19.0"     # Metrics
sentry-sdk = "^1.40.0"            # Error tracking
evidently = "^0.4.15"             # ML monitoring (drift)

# ===== UTILS =====
python-dotenv = "^1.0.0"          # Env vars
tenacity = "^8.2.3"               # Retry logic
loguru = "^0.7.2"                 # Logging melhorado
python-multipart = "^0.0.6"       # File uploads
jinja2 = "^3.1.3"                 # Templates (reports)

[tool.poetry.group.dev.dependencies]
# ===== TESTING =====
pytest = "^8.0.0"                 # Framework de testes
pytest-cov = "^4.1.0"             # Coverage
pytest-asyncio = "^0.23.0"        # Testes async
pytest-mock = "^3.12.0"           # Mocking
faker = "^22.0.0"                 # Dados fake para testes
httpx = "^0.26.0"                 # Cliente HTTP para testes

# ===== CODE QUALITY =====
ruff = "^0.1.15"                  # Linting + formatting (rápido!)
mypy = "^1.8.0"                   # Type checking
pre-commit = "^3.6.0"             # Git hooks
black = "^24.0.0"                 # Code formatter (backup)
isort = "^5.13.0"                 # Import sorting

# ===== NOTEBOOKS =====
jupyter = "^1.0.0"                # Jupyter notebooks
ipykernel = "^6.28.0"             # Kernel
matplotlib = "^3.8.0"             # Visualizações
seaborn = "^0.13.0"               # Plots estatísticos
plotly = "^5.18.0"                # Plots interativos
```

**Justificativas das Escolhas:**

| Tecnologia | Alternativa | Por que escolhemos |
|------------|-------------|-------------------|
| **FastAPI** | Flask, Django | Async nativo, validação automática, docs gerado |
| **Polars** | Só Pandas | 10x mais rápido, syntax moderna |
| **XGBoost** | Random Forest | State-of-art para tabular, explicável |
| **MLflow** | W&B, Neptune | Open-source, self-hosted, industry standard |
| **Prefect** | Airflow | Mais moderno, Pythonic, cloud gratuito |
| **Anthropic** | Só OpenAI | Claude é melhor em português, menos censura |
| **Pinecone** | Weaviate, Qdrant | Free tier generoso, docs excelentes |
| **Ruff** | Pylint, Flake8 | 100x mais rápido, all-in-one |

---

### Frontend (Next.js 14)

```json
{
  "name": "licitacoes-frontend",
  "version": "1.0.0",
  "dependencies": {
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",

    // State & Data Fetching
    "@tanstack/react-query": "^5.17.0",
    "axios": "^1.6.5",
    "swr": "^2.2.4",

    // UI Components
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-toast": "^1.1.5",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",

    // Charts & Visualizations
    "recharts": "^2.10.0",
    "d3": "^7.8.5",
    "@visx/visx": "^3.10.0",

    // Forms & Validation
    "react-hook-form": "^7.49.0",
    "zod": "^3.22.4",

    // Utils
    "date-fns": "^3.2.0",
    "lodash": "^4.17.21",

    // PDF Generation
    "jspdf": "^2.5.1",
    "html2canvas": "^1.4.1",

    // Markdown (para explicações LLM)
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@types/node": "^20.11.0",
    "@types/d3": "^7.4.3",

    // Linting & Formatting
    "eslint": "^8.56.0",
    "eslint-config-next": "14.1.0",
    "prettier": "^3.2.0",
    "prettier-plugin-tailwindcss": "^0.5.11",

    // Testing
    "vitest": "^1.2.0",
    "@testing-library/react": "^14.1.2",
    "@testing-library/jest-dom": "^6.2.0",

    // Tailwind
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33"
  }
}
```

**Justificativas:**

- **Next.js 14**: App Router, Server Components (performance), streaming
- **shadcn/ui**: Componentes modernos, acessíveis, customizáveis
- **TanStack Query**: Cache inteligente, refetch automático
- **Recharts**: Simples para 80% dos casos, performático
- **D3**: Visualizações custom quando Recharts não serve

---

### Infrastructure & DevOps

```yaml
# Docker
docker: ^24.0.0
docker-compose: ^2.23.0

# Terraform
terraform: ^1.6.0
aws-provider: ^5.0.0

# CI/CD
github-actions: latest

# Cloud (AWS)
aws-cli: ^2.0.0
```

---

## 📁 Estrutura do Projeto

```
licitacoes-ml/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Tests + linting
│       ├── cd-backend.yml                  # Deploy backend to AWS
│       ├── cd-frontend.yml                 # Deploy frontend
│       └── model-retrain.yml               # Weekly retraining
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                         # FastAPI app entry
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                     # Dependencies (DB, Redis)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py               # Main router
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── predictions.py      # ML predictions
│   │   │           ├── explanations.py     # SHAP + LLM
│   │   │           ├── search.py           # RAG search
│   │   │           ├── edital_analysis.py  # NLP analysis
│   │   │           ├── analytics.py        # Dashboards data
│   │   │           └── health.py           # Health checks
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                   # Pydantic Settings
│   │   │   ├── security.py                 # Auth (se necessário)
│   │   │   ├── logging.py                  # Loguru config
│   │   │   └── metrics.py                  # Prometheus metrics
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py                 # SQLAlchemy models
│   │   │   └── schemas.py                  # Pydantic schemas (API)
│   │   │
│   │   ├── ml/
│   │   │   ├── __init__.py
│   │   │   ├── model_loader.py             # Load ONNX/pickle
│   │   │   ├── inference.py                # Prediction logic
│   │   │   ├── explainer.py                # SHAP values
│   │   │   ├── preprocessing.py            # Feature transforms
│   │   │   └── monitoring.py               # Drift detection
│   │   │
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py               # Claude/GPT wrappers
│   │   │   ├── prompts.py                  # Prompt templates
│   │   │   ├── rag.py                      # RAG pipeline
│   │   │   ├── nlp_analyzer.py             # BERT for editais
│   │   │   └── embeddings.py               # Vector operations
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── licitacao_service.py        # Business logic
│   │   │   ├── market_price_service.py
│   │   │   └── cache_service.py            # Redis operations
│   │   │
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py               # Celery config
│   │   │   └── tasks.py                    # Async tasks
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── database.py                 # DB session
│   │       ├── s3.py                       # S3 operations
│   │       └── validators.py               # Custom validators
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                     # Pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_ml_inference.py
│   │   │   ├── test_preprocessing.py
│   │   │   └── test_services.py
│   │   ├── integration/
│   │   │   ├── test_api_predictions.py
│   │   │   ├── test_rag_pipeline.py
│   │   │   └── test_database.py
│   │   └── e2e/
│   │       └── test_full_pipeline.py
│   │
│   ├── alembic/                            # DB migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── scripts/
│   │   ├── init_db.py                      # Setup database
│   │   ├── seed_data.py                    # Sample data
│   │   └── health_check.sh                 # Deployment health
│   │
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── pyproject.toml                      # Poetry dependencies
│   ├── poetry.lock
│   ├── .env.example
│   ├── .coveragerc
│   ├── pytest.ini
│   └── README.md
│
├── ml/
│   ├── data/
│   │   ├── raw/                            # DVC tracked
│   │   ├── processed/                      # DVC tracked
│   │   ├── features/                       # DVC tracked
│   │   └── external/                       # Reference data
│   │
│   ├── notebooks/
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   ├── 03_baseline_models.ipynb
│   │   ├── 04_model_tuning.ipynb
│   │   ├── 05_model_evaluation.ipynb
│   │   └── 06_explainability.ipynb
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   │
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py                # Fetch from APIs
│   │   │   ├── validation.py               # Great Expectations
│   │   │   ├── cleaning.py                 # Data cleaning
│   │   │   └── transforms.py               # ETL transforms
│   │   │
│   │   ├── features/
│   │   │   ├── __init__.py
│   │   │   ├── build_features.py           # Feature engineering
│   │   │   ├── feature_selection.py        # Select best features
│   │   │   └── encoders.py                 # Custom encoders
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── train.py                    # Training script
│   │   │   ├── evaluate.py                 # Evaluation metrics
│   │   │   ├── tune.py                     # Optuna tuning
│   │   │   ├── explain.py                  # SHAP generation
│   │   │   └── export.py                   # Export to ONNX
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── mlflow_utils.py             # MLflow helpers
│   │       ├── data_loader.py              # Load datasets
│   │       └── metrics.py                  # Custom metrics
│   │
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── ingestion_flow.py               # Prefect flow
│   │   ├── training_flow.py                # Training pipeline
│   │   └── deployment_flow.py              # Model deployment
│   │
│   ├── configs/
│   │   ├── model_config.yaml               # Model hyperparams
│   │   ├── feature_config.yaml             # Feature definitions
│   │   └── data_quality_config.yaml        # GE expectations
│   │
│   ├── mlruns/                             # MLflow tracking (gitignore)
│   ├── models/                             # Trained models (DVC)
│   │
│   ├── dvc.yaml                            # DVC pipeline
│   ├── dvc.lock
│   ├── params.yaml                         # DVC parameters
│   ├── .dvc/
│   ├── .dvcignore
│   │
│   ├── requirements.txt
│   ├── setup.py
│   └── README.md
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                      # Root layout
│   │   ├── page.tsx                        # Home page
│   │   ├── globals.css
│   │   │
│   │   ├── dashboard/
│   │   │   ├── page.tsx                    # Main dashboard
│   │   │   └── layout.tsx
│   │   │
│   │   ├── licitacoes/
│   │   │   ├── page.tsx                    # List view
│   │   │   └── [id]/
│   │   │       └── page.tsx                # Detail view
│   │   │
│   │   ├── busca/
│   │   │   └── page.tsx                    # RAG search interface
│   │   │
│   │   └── analytics/
│   │       └── page.tsx                    # Analytics dashboard
│   │
│   ├── components/
│   │   ├── ui/                             # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   │
│   │   ├── charts/
│   │   │   ├── PriceComparisonChart.tsx
│   │   │   ├── ShapPlot.tsx
│   │   │   └── TimeSeriesChart.tsx
│   │   │
│   │   ├── licitacao/
│   │   │   ├── LicitacaoCard.tsx
│   │   │   ├── LicitacaoFilters.tsx
│   │   │   └── ExplanationPanel.tsx
│   │   │
│   │   └── shared/
│   │       ├── Header.tsx
│   │       ├── Footer.tsx
│   │       └── Loading.tsx
│   │
│   ├── lib/
│   │   ├── api-client.ts                   # Axios instance
│   │   ├── utils.ts                        # Utility functions
│   │   ├── types.ts                        # TypeScript types
│   │   └── constants.ts
│   │
│   ├── hooks/
│   │   ├── useLicitacoes.ts
│   │   ├── usePrediction.ts
│   │   └── useSearch.ts
│   │
│   ├── public/
│   │   ├── images/
│   │   └── icons/
│   │
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .eslintrc.json
│   ├── .prettierrc
│   └── README.md
│
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   │
│   │   ├── modules/
│   │   │   ├── ecs/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   ├── rds/
│   │   │   ├── s3/
│   │   │   ├── elasticache/
│   │   │   └── networking/
│   │   │
│   │   └── environments/
│   │       ├── dev/
│   │       │   └── terraform.tfvars
│   │       └── prod/
│   │           └── terraform.tfvars
│   │
│   ├── docker-compose.yml                  # Local development
│   ├── docker-compose.prod.yml             # Production-like
│   │
│   └── monitoring/
│       ├── prometheus.yml
│       ├── grafana-dashboards/
│       │   ├── ml-metrics.json
│       │   └── api-performance.json
│       └── alertmanager.yml
│
├── docs/
│   ├── architecture.md
│   ├── api-documentation.md
│   ├── ml-methodology.md
│   ├── deployment-guide.md
│   ├── data-dictionary.md
│   ├── contributing.md
│   └── images/
│       ├── architecture-diagram.png
│       └── screenshots/
│
├── scripts/
│   ├── setup_local.sh                      # Setup dev environment
│   ├── run_tests.sh                        # Run all tests
│   ├── deploy_dev.sh                       # Deploy to dev
│   ├── deploy_prod.sh                      # Deploy to prod
│   └── backup_db.sh                        # Database backup
│
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml
├── Makefile                                # Common commands
├── docker-compose.yml
├── README.md                               # Main documentation
├── LICENSE
└── CHANGELOG.md
```

---

## 📅 Roadmap Detalhado - 5 Meses

### **Mês 1: Fundação e Data Pipeline** (Semanas 1-4)

#### **Semana 1: Setup & Arquitetura**
**Objetivo**: Ambiente de desenvolvimento funcionando

**Tarefas:**
- [ ] Criar repositório GitHub (público)
- [ ] Setup estrutura de pastas completa
- [ ] Configurar Poetry + pyproject.toml
- [ ] Docker Compose: PostgreSQL + Redis + MLflow
- [ ] Setup DVC com S3 local (MinIO)
- [ ] Configurar pre-commit hooks
- [ ] GitHub Actions: CI básico (linting)
- [ ] README inicial com instruções setup

**Deliverables:**
- ✅ Projeto roda com `docker-compose up`
- ✅ CI passando (mesmo sem código)
- ✅ Documentação de setup

**Tempo estimado**: 35-40 horas

---

#### **Semana 2: Schema de Dados & Ingestão**
**Objetivo**: Primeiros dados no sistema

**Tarefas:**
- [ ] Pesquisar APIs disponíveis (PNCP, Compras.gov)
- [ ] Definir schema PostgreSQL (staging + dwh)
- [ ] Criar models SQLAlchemy
- [ ] Implementar cliente API PNCP
- [ ] Script de ingestão inicial
- [ ] Great Expectations: data quality suite
- [ ] Coletar 10k+ licitações

**Deliverables:**
- ✅ Schema documentado (data dictionary)
- ✅ 10k licitações no PostgreSQL
- ✅ Data quality checks passando

**Tempo estimado**: 40-45 horas

---

#### **Semana 3: ETL Pipeline**
**Objetivo**: Pipeline automatizado de dados

**Tarefas:**
- [ ] Setup Prefect Cloud (free tier)
- [ ] Criar flow de ingestão diária
- [ ] Implementar data cleaning
- [ ] Criar camadas bronze/silver/gold no S3
- [ ] Tracking DVC dos datasets
- [ ] Scheduler: rodar diariamente
- [ ] Monitoramento básico (logs)

**Deliverables:**
- ✅ Pipeline rodando automaticamente
- ✅ Dados versionados (DVC)
- ✅ 50k+ licitações coletadas

**Tempo estimado**: 35-40 horas

---

#### **Semana 4: Coleta de Preços de Mercado**
**Objetivo**: Baseline para comparação

**Tarefas:**
- [ ] Identificar fontes de preços (SINAPI, scraping)
- [ ] Implementar scraping ético (rate limit)
- [ ] Normalizar categorias de produtos
- [ ] Join licitações ↔ preços mercado
- [ ] Análise de cobertura (% com preço)
- [ ] Documentar fontes e metodologia

**Deliverables:**
- ✅ Tabela `market_prices` populada
- ✅ 70%+ licitações com preço de referência
- ✅ Metodologia documentada

**Tempo estimado**: 35-40 horas

**Total Mês 1**: ~150 horas (37.5h/semana)

---

### **Mês 2: Feature Engineering & EDA** (Semanas 5-8)

#### **Semana 5: Análise Exploratória**
**Objetivo**: Entender profundamente os dados

**Tarefas:**
- [ ] Setup Jupyter Lab
- [ ] Notebook: distribuições de preços
- [ ] Análise por categoria, região, órgão
- [ ] Identificar outliers óbvios
- [ ] Análise temporal (sazonalidade?)
- [ ] Correlações entre variáveis
- [ ] Pandas Profiling report

**Deliverables:**
- ✅ Notebook `01_data_exploration.ipynb`
- ✅ Relatório de insights (3-5 páginas)
- ✅ Hipóteses para features

**Tempo estimado**: 35-40 horas

---

#### **Semana 6: Feature Engineering - Parte 1**
**Objetivo**: Features numéricas e agregações

**Tarefas:**
- [ ] Feature: desvio do preço médio
- [ ] Feature: percentil por categoria
- [ ] Feature: histórico do fornecedor
- [ ] Feature: tempo desde última licitação
- [ ] Feature: valor per capita (população)
- [ ] Feature: sazonalidade (mês, trimestre)
- [ ] Feature: complexidade do edital (tamanho)
- [ ] Pipeline de transformação

**Deliverables:**
- ✅ 15+ features numéricas
- ✅ Pipeline reproduzível
- ✅ Notebook documentado

**Tempo estimado**: 40-45 horas

---

#### **Semana 7: Feature Engineering - Parte 2**
**Objetivo**: Features categóricas e interações

**Tarefas:**
- [ ] Encoding de categorias (target encoding)
- [ ] Features de interação (categoria × região)
- [ ] Features de texto (editais)
- [ ] TF-IDF de descrições (se houver)
- [ ] Feature selection (correlação, importância)
- [ ] Validação de features (não vazam futuro)
- [ ] Documentar cada feature

**Deliverables:**
- ✅ 30+ features totais
- ✅ Feature importance analysis
- ✅ Dicionário de features completo

**Tempo estimado**: 40-45 horas

---

#### **Semana 8: Target Definition & Dataset Final**
**Objetivo**: Dataset pronto para ML

**Tarefas:**
- [ ] Definir target: sobrepreço (binário? regressão?)
- [ ] Estratégia de labeling (threshold? manual?)
- [ ] Train/validation/test split (temporal)
- [ ] Análise de desbalanceamento
- [ ] Estratificar splits
- [ ] Salvar datasets finais (DVC)
- [ ] Dataset quality checks

**Deliverables:**
- ✅ Dataset ML-ready (train/val/test)
- ✅ Target bem definido e documentado
- ✅ Análise de desbalanceamento

**Tempo estimado**: 30-35 horas

**Total Mês 2**: ~150 horas

---

### **Mês 3: Machine Learning** (Semanas 9-12)

#### **Semana 9: Baseline Models**
**Objetivo**: Estabelecer baseline de performance

**Tarefas:**
- [ ] Setup MLflow tracking
- [ ] Dummy classifier (baseline ingênuo)
- [ ] Logistic Regression
- [ ] Random Forest
- [ ] XGBoost (default params)
- [ ] Cross-validation (5-fold)
- [ ] Definir métricas primárias (precision, recall)
- [ ] Análise de erros

**Deliverables:**
- ✅ 4-5 modelos baseline
- ✅ MLflow com experimentos
- ✅ Baseline performance report

**Tempo estimado**: 35-40 horas

---

#### **Semana 10: Model Tuning**
**Objetivo**: Otimizar modelo de produção

**Tarefas:**
- [ ] Setup Optuna
- [ ] Hyperparameter tuning XGBoost (100+ trials)
- [ ] Tuning LightGBM
- [ ] Ensemble (XGBoost + LightGBM)
- [ ] Threshold tuning (precision/recall tradeoff)
- [ ] Calibração de probabilidades
- [ ] Validação no test set

**Deliverables:**
- ✅ Modelo otimizado (>85% precision)
- ✅ Optuna study salvo
- ✅ Métricas finais documentadas

**Tempo estimado**: 40-45 horas

---

#### **Semana 11: Explainability**
**Objetivo**: Entender e explicar predições

**Tarefas:**
- [ ] SHAP values (global + local)
- [ ] Feature importance (gain, cover, freq)
- [ ] Partial dependence plots
- [ ] LIME (alternativa ao SHAP)
- [ ] Análise de casos extremos
- [ ] Criar explainer reutilizável
- [ ] Notebook de explicabilidade

**Deliverables:**
- ✅ SHAP explainer treinado
- ✅ Visualizações de explicabilidade
- ✅ Notebook `05_explainability.ipynb`

**Tempo estimado**: 30-35 horas

---

#### **Semana 12: Model Registry & Export**
**Objetivo**: Modelo pronto para produção

**Tarefas:**
- [ ] Registrar modelo no MLflow
- [ ] Export para ONNX
- [ ] Validar ONNX (mesmas predições)
- [ ] Benchmark de latência
- [ ] Model card (documentação)
- [ ] Criar inference pipeline
- [ ] Testes unitários do modelo

**Deliverables:**
- ✅ Modelo em ONNX otimizado
- ✅ Latência <100ms (p99)
- ✅ Model card completo

**Tempo estimado**: 35-40 horas

**Total Mês 3**: ~145 horas

---

### **Mês 4: Backend API & AI Layer** (Semanas 13-16)

#### **Semana 13: FastAPI Core**
**Objetivo**: API básica funcionando

**Tarefas:**
- [ ] Setup FastAPI + estrutura
- [ ] Config (Pydantic Settings)
- [ ] Database connection pool
- [ ] Redis connection
- [ ] Model loading (singleton)
- [ ] Endpoint: POST /v1/predict
- [ ] Endpoint: GET /v1/health
- [ ] Swagger docs configurado

**Deliverables:**
- ✅ API rodando localmente
- ✅ Endpoint de predição funcional
- ✅ Swagger UI acessível

**Tempo estimado**: 35-40 horas

---

#### **Semana 14: API Features & Testing**
**Objetivo**: API production-ready

**Tarefas:**
- [ ] Endpoint: POST /v1/explain (SHAP)
- [ ] Endpoint: POST /v1/batch (lote)
- [ ] Rate limiting (SlowAPI)
- [ ] Caching (Redis - 24h TTL)
- [ ] Error handling robusto
- [ ] Logging estruturado (Loguru)
- [ ] Testes unitários (pytest)
- [ ] Testes de integração
- [ ] Coverage >85%

**Deliverables:**
- ✅ API completa (CRUD)
- ✅ Testes passando (>85% coverage)
- ✅ Performance benchmarks

**Tempo estimado**: 40-45 horas

---

#### **Semana 15: AI Layer - LLM Integration**
**Objetivo**: Adicionar inteligência generativa

**Tarefas:**
- [ ] Setup Anthropic SDK
- [ ] Criar prompt templates
- [ ] Função: explain_to_citizen()
- [ ] Endpoint: POST /v1/explain-llm
- [ ] Streaming responses (Server-Sent Events)
- [ ] Token usage tracking
- [ ] Cost monitoring
- [ ] Fallback (se API falhar)
- [ ] Testes com mocks

**Deliverables:**
- ✅ Explicações em linguagem natural
- ✅ Streaming funcionando
- ✅ Cost tracking implementado

**Tempo estimado**: 35-40 horas

---

#### **Semana 16: RAG System**
**Objetivo**: Busca semântica de editais

**Tarefas:**
- [ ] Setup Pinecone (free tier)
- [ ] Indexar editais (embeddings)
- [ ] Implementar chunking strategy
- [ ] RAG pipeline (retrieve + generate)
- [ ] Endpoint: POST /v1/search
- [ ] Relevance scoring
- [ ] Cache de embeddings
- [ ] Testes de relevância

**Deliverables:**
- ✅ RAG funcional
- ✅ Busca semântica precisa
- ✅ Endpoint documentado

**Tempo estimado**: 40-45 horas

**Total Mês 4**: ~155 horas

---

### **Mês 5: Frontend, Deploy & Polish** (Semanas 17-20)

#### **Semana 17: Frontend - Core**
**Objetivo**: Dashboard básico funcionando

**Tarefas:**
- [ ] Setup Next.js 14 + TypeScript
- [ ] Configurar shadcn/ui
- [ ] API client (Axios + TanStack Query)
- [ ] Layout base (Header, Footer)
- [ ] Página: Dashboard (KPIs)
- [ ] Página: Lista de licitações
- [ ] Página: Detalhe de licitação
- [ ] Responsivo (mobile-first)

**Deliverables:**
- ✅ Frontend rodando localmente
- ✅ 3 páginas principais
- ✅ UX polido

**Tempo estimado**: 40-45 horas

---

#### **Semana 18: Frontend - Features Avançadas**
**Objetivo**: Diferenciais visuais

**Tarefas:**
- [ ] Gráfico: comparação preço (Recharts)
- [ ] Gráfico: SHAP waterfall (D3.js)
- [ ] Streaming de explicações LLM
- [ ] Busca semântica (interface RAG)
- [ ] Exportação PDF (jsPDF)
- [ ] Filtros avançados
- [ ] Loading states + errors
- [ ] Dark mode (opcional)

**Deliverables:**
- ✅ Visualizações impressionantes
- ✅ Explicabilidade visual
- ✅ Relatórios exportáveis

**Tempo estimado**: 40-45 horas

---

#### **Semana 19: Deploy & Infrastructure**
**Objetivo**: Sistema em produção

**Tarefas:**
- [ ] Dockerfile backend (multi-stage)
- [ ] Dockerfile frontend
- [ ] Terraform: ECS Fargate
- [ ] Terraform: RDS PostgreSQL
- [ ] Terraform: ElastiCache Redis
- [ ] Terraform: S3
- [ ] Terraform: ALB + HTTPS
- [ ] GitHub Actions: CD pipeline
- [ ] Secrets management (AWS Secrets Manager)
- [ ] Deploy staging + prod

**Deliverables:**
- ✅ App rodando em AWS
- ✅ URL pública (HTTPS)
- ✅ CI/CD automatizado

**Tempo estimado**: 45-50 horas

---

#### **Semana 20: Monitoring, Docs & Launch**
**Objetivo**: Projeto pronto para apresentar

**Tarefas:**
- [ ] Prometheus + Grafana dashboards
- [ ] Evidently AI (drift detection)
- [ ] Sentry error tracking
- [ ] README de nível mundial
- [ ] docs/ completo (arquitetura, API, ML)
- [ ] Video demo (5 minutos)
- [ ] LinkedIn post
- [ ] Medium article (opcional)
- [ ] Portfolio update

**Deliverables:**
- ✅ Monitoring completo
- ✅ Documentação impecável
- ✅ Video demo no YouTube
- ✅ Presença online

**Tempo estimado**: 40-45 horas

**Total Mês 5**: ~170 horas

---

## **TOTAL PROJETO: ~770 horas (~38h/semana)**


## ✅ RESUMO DO PROJETO COMPLETO

### O que você vai construir:

**Sistema Híbrido de Detecção de Sobrepreço em Licitações**
- **ML Tradicional** (XGBoost) → detecção quantitativa de anomalias
- **AI Generativa** (Claude/GPT) → explicabilidade e análise qualitativa
- **NLP** (BERT) → análise de cláusulas em editais
- **RAG** (Pinecone) → busca semântica de licitações similares

---

## 📊 ENTREGAS FINAIS (5 meses)

### **Produto Final:**

1. **Backend API (FastAPI)**
   - `/predict` - detecção ML tradicional
   - `/explain` - explicações LLM + SHAP
   - `/search` - busca semântica (RAG)
   - `/analyze-edital` - NLP de cláusulas
   - Latência <100ms, 90%+ coverage de testes

2. **Frontend (Next.js 14)**
   - Dashboard com KPIs e alertas
   - Análise individual de licitações
   - Visualização de explicabilidade (SHAP plots)
   - Comparativos preço licitação vs mercado
   - Exportação de relatórios PDF

3. **Infraestrutura (AWS)**
   - ECS Fargate (backend)
   - RDS PostgreSQL (dados)
   - S3 (data lake)
   - ElastiCache Redis (cache)
   - Terraform (IaC)
   - CI/CD completo (GitHub Actions)

4. **MLOps Pipeline**
   - Prefect (orquestração)
   - MLflow (tracking)
   - DVC (versionamento)
   - Great Expectations (data quality)
   - Evidently AI (drift detection)

5. **Documentação**
   - README nível mundial
   - Architecture docs
   - API documentation
   - ML methodology paper
   - Video demo (5 min)

---

## 🎯 CRONOGRAMA FINAL - 5 MESES

| Mês | Foco | Horas | Entregas Principais |
|-----|------|-------|---------------------|
| **1** | Data Pipeline | 150h | 50k+ licitações coletadas, pipeline automatizado |
| **2** | Feature Engineering | 150h | 30+ features, dataset ML-ready |
| **3** | ML Models | 145h | Modelo XGBoost (87%+ precision), SHAP explainer |
| **4** | Backend + AI | 155h | API completa, LLM integration, RAG system |
| **5** | Frontend + Deploy | 170h | Dashboard, app em produção (AWS), monitoring |
| **TOTAL** | | **770h** | **Sistema completo end-to-end** |

**Dedicação:** ~38h/semana (7-8h/dia, 5 dias/semana)

---

## 🏆 DIFERENCIAIS PARA VAGAS

### **Para ML Engineer:**
✅ Pipeline completo de dados (ETL, quality, versionamento)
✅ Feature engineering sofisticado (30+ features)
✅ MLOps production-ready (MLflow, DVC, monitoring)
✅ Model serving otimizado (ONNX, <100ms)
✅ Testes automatizados (>85% coverage)

### **Para AI Engineer:**
✅ LLM integration (Claude API, prompt engineering)
✅ RAG system (Pinecone, embeddings, semantic search)
✅ NLP aplicado (BERT, análise de editais)
✅ Explicabilidade (SHAP visual + narrativa LLM)
✅ Multi-modal (dados tabulares + texto)

---

## 📈 MÉTRICAS DE SUCESSO

### **Técnicas:**
- ✅ Modelo: Precision >85%, Recall >80%
- ✅ API: Latência p99 <100ms
- ✅ Testes: Coverage >85%
- ✅ Uptime: >99% (após deploy)
- ✅ Data Quality: 100% de validações passando

### **Portfolio:**
- ✅ GitHub: >1000 linhas de código bem estruturado
- ✅ README: >2000 palavras, diagramas, screenshots
- ✅ Video Demo: 5 minutos, profissional
- ✅ Documentação: 5+ docs técnicos completos
- ✅ App Live: URL pública funcionando

### **Carreira:**
- ✅ **Objetivo:** Primeiro emprego ML/AI Engineer
- ✅ **Timeline:** Começar aplicar no mês 4-5
- ✅ **Meta:** 3-5 entrevistas técnicas até mês 6

---

## 🛠️ STACK FINAL

### **Core Technologies:**

**Backend/ML:**
```
Python 3.11 + FastAPI + SQLAlchemy
XGBoost + LightGBM + MLflow
Anthropic (Claude) + OpenAI (GPT-4)
Pinecone + BERT + SHAP
PostgreSQL + Redis + S3
Prefect + DVC + Great Expectations
```

**Frontend:**
```
Next.js 14 + TypeScript
shadcn/ui + Tailwind CSS
TanStack Query + Recharts + D3.js
```

**Infrastructure:**
```
Docker + Terraform
AWS ECS Fargate + RDS + S3
GitHub Actions (CI/CD)
Prometheus + Grafana + Sentry
```

---

## 📋 CHECKLIST FINAL DE ENTREGA

### **Antes de Aplicar para Vagas:**

**Código:**
- [ ] >85% test coverage
- [ ] Zero warnings de linting
- [ ] Type hints em 100% do código
- [ ] Documentação inline (docstrings)

**Deploy:**
- [ ] App rodando em produção (URL pública)
- [ ] HTTPS configurado
- [ ] Monitoring ativo (Grafana)
- [ ] CI/CD funcionando

**Documentação:**
- [ ] README impressionante
- [ ] 5+ docs técnicos completos
- [ ] Diagramas visuais
- [ ] Screenshots/GIFs

**Presença:**
- [ ] Video demo no YouTube
- [ ] LinkedIn post sobre o projeto
- [ ] Portfolio atualizado
- [ ] GitHub profile polido

**Preparação:**
- [ ] Consegue explicar TODAS as decisões técnicas
- [ ] Conhece limitações do projeto (seja honesto)
- [ ] Sabe dizer "o que faria diferente"
- [ ] Preparado para live coding (refactor de alguma parte)

---
