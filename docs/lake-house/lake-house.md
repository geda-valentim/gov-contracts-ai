# Gov Contracts AI - Lakehouse Architecture
## Documento Técnico de Arquitetura de Dados v1.1

**Data:** 21 de Outubro de 2025
**Versão:** 1.1
**Status:** Aprovado para Implementação
**Licença:** GPL v3.0 (Software Livre)

---

## 📋 Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Padrão Lakehouse](#2-padrão-lakehouse)
3. [Camadas de Dados (Medallion)](#3-camadas-de-dados-medallion)
4. [Fontes de Dados](#4-fontes-de-dados)
5. [Stack Tecnológica](#5-stack-tecnológica)
6. [Integração Ingestify.ai](#6-integração-ingestifyai)
7. [Fluxo de Dados Completo](#7-fluxo-de-dados-completo)
8. [Storage Strategy](#8-storage-strategy)
9. [Decisões Técnicas](#9-decisões-técnicas)
10. [Schemas de Dados](#10-schemas-de-dados)
11. [Performance & Scalability](#11-performance--scalability)

---

## 1. Visão Geral da Arquitetura

### 1.1 Conceito

O **Gov Contracts AI** implementa uma arquitetura **Lakehouse** que combina:
- **Data Lake** (flexibilidade, baixo custo, schema-on-read)
- **Data Warehouse** (performance, estrutura, queries rápidas)
- **Search Engine** (full-text, semantic search, logs)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    LAKEHOUSE ARCHITECTURE                              │
│                                                                        │
│  Data Lake (MinIO S3)  +  Data Warehouse (PostgreSQL)  +  Search (OpenSearch) │
│   Object Storage              SSD                              SSD      │
│  S3-Compatible            Structured                       Searchable   │
│   ML Training            API Queries                     Semantic Search│
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Objetivo

Detectar fraudes em licitações governamentais através da análise integrada de:
1. **Dados estruturados** (licitações, empresas, CNPJ)
2. **Documentos não estruturados** (editais em PDF)
3. **Dados de mercado** (preços web scraping)

### 1.3 Princípios Arquiteturais

✅ **100% Open Source** - Zero vendor lock-in
✅ **On-premises** - Dados não saem do servidor
✅ **Soberania tecnológica** - Controle total
✅ **Custo-efetivo** - Hardware consumer-grade
✅ **Escalável** - De 50k a 500k+ licitações
✅ **Auditável** - Código e dados transparentes

---

## 2. Padrão Lakehouse

### 2.1 Definição

**Lakehouse** = Data Lake + Data Warehouse + Search Engine

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📦 DATA LAKE (MinIO S3 - Object Storage)                          │
│  ├─ Propósito: Armazenamento flexível de todos os dados           │
│  ├─ Formato: Parquet (columnar, comprimido) em buckets S3         │
│  ├─ Schema: Schema-on-read (flexível)                             │
│  ├─ Buckets: bronze/, silver/, gold/, mlflow/, backups/           │
│  ├─ API: S3-compatible (boto3, AWS SDK, s3fs)                     │
│  ├─ Versioning: Habilitado (imutabilidade, auditoria)             │
│  ├─ Uso: ML training, feature engineering, model artifacts        │
│  └─ Storage: HDD 1.81TB (montado como volumes MinIO)              │
│                                                                     │
│  🗄️ DATA WAREHOUSE (PostgreSQL - SSD 480GB)                       │
│  ├─ Propósito: Queries rápidas, ACID transactions                 │
│  ├─ Formato: Relacional (tabelas, índices)                        │
│  ├─ Schema: Schema-on-write (estruturado)                         │
│  ├─ Uso: API REST, dashboards, BI tools                          │
│  └─ Custo: Médio (SSD)                                           │
│                                                                     │
│  🔍 SEARCH ENGINE (OpenSearch - SSD 480GB)                        │
│  ├─ Propósito: Full-text search, semantic search, logs           │
│  ├─ Formato: Inverted index + vector index                       │
│  ├─ Schema: Flexível (JSON documents)                            │
│  ├─ Uso: Busca de editais, contratos similares, monitoring       │
│  └─ Custo: Médio (SSD)                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Por Que Lakehouse?

| Pergunta | Resposta |
|----------|----------|
| Por que não só Data Lake? | Queries lentas, sem estrutura para APIs |
| Por que não só Data Warehouse? | Caro, inflexível, ruim para ML |
| Por que não só Search Engine? | Não é transacional, difícil para analytics |
| **Por que Lakehouse?** | **Melhor dos 3 mundos para este caso de uso** |

### 2.3 Workloads por Storage

```
┌─────────────────────────────────────────────────────────────────┐
│  WORKLOAD                    →    STORAGE IDEAL                 │
├─────────────────────────────────────────────────────────────────┤
│  ML Training (XGBoost)       →    MinIO S3 (s3://gold/)         │
│  Feature Engineering         →    MinIO S3 (s3://silver/)       │
│  API Queries (GET /contracts)→    Data Warehouse (PostgreSQL)   │
│  Busca Editais (search)      →    Search Engine (OpenSearch)    │
│  Análise Ad-hoc (Pandas)     →    MinIO S3 (s3://gold/) + s3fs  │
│  Dashboard BI (Grafana)      →    Data Warehouse (PostgreSQL)   │
│  Logs & Monitoring           →    Search Engine (OpenSearch)    │
│  Embeddings & RAG            →    Search Engine (OpenSearch)    │
│  Model Artifacts (MLflow)    →    MinIO S3 (s3://mlflow/)       │
│  Backups                     →    MinIO S3 (s3://backups/)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Camadas de Dados (Medallion)

### 3.1 Arquitetura Medallion (Bronze → Silver → Gold)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDALLION ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

         ┌──────────────────────────────────────────┐
         │      FONTES EXTERNAS                     │
         │  • APIs Governamentais                   │
         │  • PDFs (Editais)                        │
         │  • Web Scraping (Preços)                 │
         │  • Datasets Estáticos (CNPJ)             │
         └──────────────┬───────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────────────┐
         │  🥉 BRONZE LAYER (Raw Data)              │
         │  Storage: MinIO S3 (s3://bronze/)        │
         │  Format: Parquet (snappy)                │
         ├──────────────────────────────────────────┤
         │  Características:                        │
         │  • Dados como recebidos (as-is)          │
         │  • Sem validação                         │
         │  • Particionado por data (S3 prefixes)   │
         │  • Imutável (append-only)                │
         │  • Versioning S3 habilitado              │
         │  • Retenção: Permanente                  │
         │                                          │
         │  Buckets/Prefixes:                       │
         │  ├─ s3://bronze/licitacoes/              │
         │  ├─ s3://bronze/editais_raw/             │
         │  ├─ s3://bronze/editais_text/            │
         │  ├─ s3://bronze/precos_mercado/          │
         │  └─ s3://bronze/cnpj/                    │
         └──────────────┬───────────────────────────┘
                        │ Cleaning & Validation
                        ▼
         ┌──────────────────────────────────────────┐
         │  🥈 SILVER LAYER (Clean Data)            │
         │  Storage: MinIO S3 (s3://silver/)        │
         │  Format: Parquet (snappy)                │
         ├──────────────────────────────────────────┤
         │  Características:                        │
         │  • Validado (Great Expectations)         │
         │  • Deduplicado                           │
         │  • Normalizado (tipos, formatos)         │
         │  • Joined (múltiplas fontes)             │
         │  • Enriquecido (CNPJ, CEIS, CNEP)        │
         │  • Particionado (data + categoria)       │
         │  • Retenção: Permanente                  │
         │                                          │
         │  Buckets/Prefixes:                       │
         │  ├─ s3://silver/licitacoes_clean/        │
         │  ├─ s3://silver/editais_parsed/          │
         │  ├─ s3://silver/editais_analysis/        │
         │  ├─ s3://silver/precos_normalized/       │
         │  └─ s3://silver/joined_full/             │
         └──────────────┬───────────────────────────┘
                        │ Feature Engineering
                        ▼
         ┌──────────────────────────────────────────┐
         │  🥇 GOLD LAYER (ML-Ready)                │
         │  Storage: Multi-target                   │
         ├──────────────────────────────────────────┤
         │  📊 Analytics (MinIO S3)                 │
         │  ├─ s3://gold/features_ml/               │
         │  ├─ s3://gold/embeddings/                │
         │  ├─ s3://gold/agregados/                 │
         │  └─ Cache local SSD para hot data        │
         │                                          │
         │  🗄️ Query Layer (PostgreSQL/SSD)        │
         │  ├─ licitacoes_gold                      │
         │  ├─ editais_metadata                     │
         │  ├─ precos_referencia                    │
         │  └─ predictions                          │
         │                                          │
         │  🔍 Search Layer (OpenSearch/SSD)        │
         │  ├─ contratos_index (text+embeddings)    │
         │  ├─ editais_index (full-text+semantic)   │
         │  └─ produtos_index (preços)              │
         └──────────────────────────────────────────┘
```

### 3.2 Características por Camada

| Aspecto | Bronze | Silver | Gold |
|---------|--------|--------|------|
| **Qualidade** | Raw (as-is) | Validado | Curado |
| **Schema** | Original | Normalizado | ML-ready |
| **Validação** | ❌ Nenhuma | ✅ Great Expectations | ✅ Completa |
| **Duplicatas** | ⚠️ Possível | ❌ Removidas | ❌ N/A |
| **Joins** | ❌ Separado | ✅ Integrado | ✅ Completo |
| **Features** | ❌ N/A | ⚠️ Básicas | ✅ 30+ engineered |
| **Uso** | Archive, replay | Processing | ML, API, Search |
| **Storage** | MinIO S3 (s3://bronze/) | MinIO S3 (s3://silver/) | MinIO S3 (s3://gold/) + PostgreSQL + OpenSearch |
| **Backend Storage** | HDD 1.81TB | HDD 1.81TB | HDD + Cache SSD |
| **Formato** | Parquet (snappy) | Parquet (snappy) | Parquet (zstd) + PostgreSQL + OpenSearch |
| **Versioning** | ✅ S3 versioning | ✅ S3 versioning | ✅ S3 versioning |
| **Retenção** | Permanente | Permanente | Permanente |

---

## 4. Fontes de Dados

### 4.1 Overview das Fontes

```
┌─────────────────────────────────────────────────────────────────┐
│                    FONTES DE DADOS (4 tipos)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣ APIs ESTRUTURADAS                                          │
│  ├─ Portal da Transparência                                    │
│  │  └─ https://api.portaldatransparencia.gov.br/              │
│  ├─ PNCP (Plataforma Nacional de Contratações Públicas)        │
│  │  └─ https://pncp.gov.br/api/                               │
│  └─ Receita Federal (CNPJ)                                     │
│     └─ https://receitaws.com.br/v1/ (ou bulk download)        │
│                                                                 │
│  2️⃣ PDFs SEMI-ESTRUTURADOS                                     │
│  ├─ Editais de Licitação                                       │
│  │  ├─ Source: PNCP, portais municipais/estaduais            │
│  │  ├─ Formato: PDF (50-200 páginas)                         │
│  │  └─ Processamento: Ingestify.ai → Docling                 │
│  └─ Características:                                           │
│     ├─ Estrutura formal (seções padronizadas)                 │
│     ├─ Tabelas (itens, valores, requisitos)                   │
│     └─ Cláusulas (objeto, habilitação, julgamento)            │
│                                                                 │
│  3️⃣ WEB SCRAPING (Preços de Mercado)                          │
│  ├─ Mercado Livre (API oficial)                               │
│  ├─ Magazine Luiza (API)                                       │
│  ├─ Amazon Brasil (scraping)                                   │
│  ├─ B2W (Americanas, Submarino)                               │
│  └─ Fornecedores específicos (Kalunga, Dell, etc)             │
│                                                                 │
│  4️⃣ DATASETS ESTÁTICOS                                         │
│  ├─ CEIS (Cadastro de Empresas Inidôneas)                     │
│  ├─ CNEP (Cadastro Nacional de Empresas Punidas)              │
│  ├─ TCU (Datasets de auditorias)                              │
│  └─ IBGE (dados demográficos, geográficos)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Volume Estimado (50k licitações)

| Fonte | Frequência | Volume/Dia | Volume/Mês | Storage Bronze |
|-------|------------|------------|------------|----------------|
| **Licitações** | Diário | ~500 | ~15k | ~100MB |
| **Editais PDF** | Diário | ~500 PDFs | ~15k PDFs | ~500MB |
| **Editais Texto** | Diário | ~500 | ~15k | ~200MB |
| **Preços Mercado** | Semanal | ~10k produtos | ~40k | ~300MB |
| **CNPJ** | Mensal | - | ~5M empresas | ~2GB |
| **CEIS/CNEP** | Mensal | - | ~10k | ~10MB |
| **TOTAL** | | | | **~3.1GB/mês** |

---

## 5. Stack Tecnológica

### 5.1 Stack Completa

```
┌─────────────────────────────────────────────────────────────────┐
│                    TECH STACK (100% Open Source)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 DATA LAYER                                                  │
│  ├─ MinIO (🆓 AGPL v3)                                         │
│  │  ├─ S3-compatible object storage                            │
│  │  ├─ Buckets: bronze/, silver/, gold/, mlflow/, backups/     │
│  │  ├─ Versioning habilitado                                   │
│  │  ├─ Backend: HDD 1.81TB (volumes montados)                  │
│  │  └─ API: boto3, s3fs, AWS SDK                               │
│  ├─ PostgreSQL 16 (🆓 PostgreSQL License)                      │
│  │  └─ Structured data, ACID, queries rápidas                  │
│  ├─ OpenSearch 2.11+ (🆓 Apache 2.0)                           │
│  │  └─ Full-text + semantic search + logs                      │
│  ├─ Redis 7 (🆓 BSD 3-Clause)                                  │
│  │  └─ Cache, sessions, pub/sub                                │
│  └─ Parquet Files (🆓 Apache 2.0)                              │
│     └─ Formato columnar armazenado no MinIO S3                 │
│                                                                 │
│  🔄 ORCHESTRATION                                               │
│  ├─ Apache Airflow 2.8+ (🆓 Apache 2.0)                        │
│  │  └─ DAGs: Bronze→Silver→Gold pipelines                      │
│  └─ Celery (🆓 BSD)                                            │
│     └─ Async tasks, distributed workers                        │
│                                                                 │
│  📄 PDF PROCESSING (Microserviço)                              │
│  ├─ Ingestify.ai (Custom)                                      │
│  │  ├─ FastAPI endpoints                                       │
│  │  ├─ Celery workers                                          │
│  │  ├─ Docling (🆓 MIT) - rule-based extraction               │
│  │  └─ Tesseract OCR (🆓 Apache 2.0)                          │
│  └─ Storage: MinIO S3 (s3://bronze/editais_*)                 │
│                                                                 │
│  🤖 MACHINE LEARNING                                            │
│  ├─ XGBoost 2.0+ (🆓 Apache 2.0)                               │
│  │  └─ Fraud detection (CPU-optimized)                         │
│  ├─ Scikit-learn 1.4+ (🆓 BSD)                                 │
│  │  └─ Preprocessing, metrics, baselines                       │
│  ├─ SHAP 0.44+ (🆓 MIT)                                        │
│  │  └─ Model explainability                                    │
│  ├─ MLflow 2.10+ (🆓 Apache 2.0)                               │
│  │  ├─ Experiment tracking, model registry                     │
│  │  └─ Artifact store: MinIO S3 (s3://mlflow/)                 │
│  ├─ DVC 3.0+ (🆓 Apache 2.0)                                   │
│  │  ├─ Data versioning                                         │
│  │  └─ Remote storage: MinIO S3                                │
│  └─ Great Expectations 0.18+ (🆓 Apache 2.0)                   │
│     └─ Data quality validation                                 │
│                                                                 │
│  🧠 AI GENERATIVA (Local)                                       │
│  ├─ Ollama (🆓 MIT)                                            │
│  │  └─ LLM server (CPU inference)                              │
│  ├─ Llama 3.1 8B Instruct Q4 (🆓 Meta License)                │
│  │  └─ Explicações em português                                │
│  ├─ multilingual-e5-small (🆓 MIT)                             │
│  │  └─ Embeddings (384 dims)                                   │
│  └─ spaCy pt_core_news_lg (🆓 MIT)                            │
│     └─ NER, parsing editais                                    │
│                                                                 │
│  🌐 BACKEND                                                     │
│  ├─ FastAPI 0.109+ (🆓 MIT)                                    │
│  │  └─ REST API                                                │
│  ├─ SQLAlchemy 2.0 (🆓 MIT)                                    │
│  │  └─ ORM async                                               │
│  └─ Pydantic V2 (🆓 MIT)                                       │
│     └─ Validation                                              │
│                                                                 │
│  🎨 FRONTEND                                                    │
│  ├─ Next.js 14 (🆓 MIT)                                        │
│  │  └─ App Router, SSR                                         │
│  ├─ TypeScript 5+ (🆓 Apache 2.0)                             │
│  ├─ Tailwind CSS 3.4+ (🆓 MIT)                                │
│  ├─ Radix UI (🆓 MIT)                                          │
│  │  └─ Primitives acessíveis                                   │
│  └─ Recharts (🆓 MIT)                                          │
│     └─ Visualizações                                           │
│                                                                 │
│  📊 MONITORING                                                  │
│  ├─ Prometheus 2.48+ (🆓 Apache 2.0)                           │
│  │  └─ Metrics collection                                      │
│  ├─ Grafana 10+ (🆓 AGPL v3)                                   │
│  │  └─ Dashboards                                              │
│  └─ OpenSearch (🆓 Apache 2.0)                                 │
│     └─ Logs (ELK pattern)                                      │
│                                                                 │
│  🐳 INFRASTRUCTURE                                              │
│  ├─ Docker 24+ (🆓 Apache 2.0)                                 │
│  ├─ Docker Compose (🆓 Apache 2.0)                             │
│  └─ Nginx 1.24+ (🆓 BSD 2-Clause)                             │
│     └─ Reverse proxy                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Decisões Tecnológicas Críticas

| Decisão | Escolhido | Alternativa Rejeitada | Por Quê |
|---------|-----------|----------------------|---------|
| **Search Engine** | OpenSearch | Elasticsearch | License (Apache vs Elastic) |
| | | Qdrant | Redundância (já tem ES para logs) |
| **Vector DB** | OpenSearch (built-in) | Pinecone | Vendor lock-in, custo |
| | | Qdrant standalone | Redundância com OpenSearch |
| **Embeddings** | multilingual-e5-small | BERTimbau | Balance: qualidade + velocidade |
| | 384 dims | e5-base (768) | Metade storage, 2x mais rápido |
| **PDF Processing** | Docling (rule-based) | Granite-Docling-258M | CPU-friendly, 10x mais rápido |
| **Data Lake Format** | Parquet | Delta Lake | Append-only (não precisa ACID) |
| | | CSV/JSON | Compressão, performance |
| **Object Storage** | MinIO (S3-compatible) | Filesystem local | S3 API, versioning, escalabilidade, flexibilidade I/O |
| **LLM** | Llama 3.1 8B Q4 | Claude/GPT API | Zero custo, soberania |
| **ML Model** | XGBoost (CPU) | Neural Networks (GPU) | Sem GPU, XGBoost é SOTA tabular |

---

## 6. Integração Ingestify.ai

### 6.1 Arquitetura Ingestify.ai

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTIFY.AI (Microserviço)                  │
│                    PDF Processing Service                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📤 API Layer                                                   │
│  ├─ POST /upload (recebe PDF + metadata)                       │
│  ├─ GET /status/{job_id} (polling status)                      │
│  ├─ GET /document/{job_id} (resultado final)                   │
│  └─ Webhook: POST {callback_url} (notifica conclusão)          │
│                                                                 │
│  🔄 Processing Pipeline                                         │
│  ├─ Step 1: Enqueue (Redis)                                    │
│  ├─ Step 2: PageSplit (1 PDF → N páginas)                     │
│  │   └─ Paralelo via Celery (6-12 workers)                    │
│  ├─ Step 3: Docling Extraction (por página)                    │
│  │   ├─ Texto completo                                         │
│  │   ├─ Estrutura (seções, headers, hierarquia)               │
│  │   ├─ Tabelas (rows, columns, cells)                        │
│  │   ├─ Metadata (fontes, layout)                             │
│  │   └─ OCR se necessário (Tesseract)                         │
│  ├─ Step 4: Aggregate Results                                  │
│  │   └─ N páginas → 1 documento JSON                          │
│  └─ Step 5: Store & Index                                      │
│     ├─ Storage: MinIO S3 (s3://bronze/editais_raw/)           │
│     └─ OpenSearch: editais_index (full-text)                  │
│                                                                 │
│  💾 Storage (MinIO S3-compatible)                              │
│  ├─ PDFs originais: s3://bronze/editais_raw/                  │
│  ├─ JSON extraído: s3://bronze/editais_text/                  │
│  ├─ API: boto3 (S3 SDK)                                        │
│  └─ Versioning: Habilitado (auditoria)                        │
│                                                                 │
│  🔍 Indexação                                                   │
│  └─ OpenSearch (compartilhado com Gov Contracts)               │
│     └─ editais_index:                                          │
│        ├─ job_id (keyword)                                     │
│        ├─ licitacao_id (keyword)                               │
│        ├─ texto_completo (text, analyzed)                      │
│        ├─ secoes (nested)                                      │
│        ├─ tabelas (nested)                                     │
│        └─ metadata                                             │
│                                                                 │
│  ⚙️ Configuration                                               │
│  ├─ Docling: rule-based (não Granite)                          │
│  ├─ OCR: Tesseract (português)                                 │
│  ├─ Workers: 6-12 (i5 cores)                                   │
│  ├─ Timeout: 10 min/edital                                     │
│  └─ Storage: MinIO S3 (buckets bronze/editais_*)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Fluxo de Integração

```
┌─────────────────────────────────────────────────────────────────┐
│  AIRFLOW (Gov Contracts AI)                                     │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ 1. Trigger edital processing
         ▼
    ┌────────────────────────────────┐
    │ DAG: process_edital            │
    │                                │
    │ Task 1: Download PDF from PNCP │
    │ └─ Save: /bronze/editais_raw/  │
    │                                │
    │ Task 2: Send to Ingestify.ai   │
    │ ├─ POST /upload                │
    │ │  Body: {                     │
    │ │    file: <PDF binary>,       │
    │ │    metadata: {               │
    │ │      licitacao_id: "123456", │
    │ │      source: "gov-contracts",│
    │ │      callback_url: "..."     │
    │ │    }                         │
    │ │  }                           │
    │ └─ Response: {                 │
    │      job_id: "ingest-abc123"   │
    │    }                           │
    └────────────┬───────────────────┘
                 │
                 │ 2. Async processing
                 ▼
    ┌────────────────────────────────┐
    │ INGESTIFY.AI                   │
    │                                │
    │ Celery Worker Pool:            │
    │ ├─ PageSplit (1→150 pages)    │
    │ ├─ Docling Extraction (//12)   │
    │ ├─ Aggregate                   │
    │ ├─ Store JSON                  │
    │ └─ Index OpenSearch            │
    │                                │
    │ Duration: ~5-10 min            │
    └────────────┬───────────────────┘
                 │
                 │ 3. Completion notification
                 ▼
    ┌────────────────────────────────┐
    │ AIRFLOW (Sensor ou Webhook)    │
    │                                │
    │ Option A: ExternalTaskSensor   │
    │ └─ Poll /status/{job_id}       │
    │                                │
    │ Option B: HTTP Sensor          │
    │ └─ Poll até status="completed" │
    │                                │
    │ Option C: Webhook Trigger      │
    │ └─ POST airflow/api/dags/...   │
    └────────────┬───────────────────┘
                 │
                 │ 4. Retrieve results
                 ▼
    ┌────────────────────────────────┐
    │ Task 3: Process Extracted Data │
    │ ├─ GET /document/{job_id}      │
    │ └─ Recebe JSON:                │
    │    {                           │
    │      job_id: "...",            │
    │      licitacao_id: "123456",   │
    │      content: {                │
    │        texto_completo: "...",  │
    │        secoes: {...},          │
    │        tabelas: [...],         │
    │        entidades: {            │
    │          valores: [...],       │
    │          datas: [...],         │
    │          empresas: [...]       │
    │        }                       │
    │      },                        │
    │      storage: {                │
    │        pdf_path: "...",        │
    │        json_path: "..."        │
    │      }                         │
    │    }                           │
    └────────────┬───────────────────┘
                 │
                 │ 5. Analysis & enrichment
                 ▼
    ┌────────────────────────────────┐
    │ Task 4: Analyze Edital         │
    │ ├─ NER: extrair entidades      │
    │ ├─ Regras: cláusulas restritivas│
    │ ├─ LLM: análise semântica      │
    │ └─ Score: 0-1 (restritivo)     │
    │                                │
    │ Task 5: Generate Embeddings    │
    │ ├─ e5-small.encode(texto)      │
    │ └─ Update OpenSearch (add vec) │
    │                                │
    │ Task 6: Save to Gold           │
    │ ├─ Parquet: /gold/editais/     │
    │ └─ PostgreSQL: editais_metadata│
    └────────────────────────────────┘
```

### 6.3 API Contract

```json
// POST /upload
{
  "file": "<binary PDF>",
  "metadata": {
    "licitacao_id": "123456",
    "source": "gov-contracts-ai",
    "priority": "high",
    "callback_url": "http://airflow:8080/api/v1/dags/edital_processed/dagRuns"
  }
}

// Response
{
  "job_id": "ingest-abc123",
  "status": "queued",
  "estimated_time_seconds": 600,
  "created_at": "2024-10-21T10:00:00Z"
}

// GET /status/{job_id}
{
  "job_id": "ingest-abc123",
  "status": "processing",  // queued|processing|completed|failed
  "progress": 0.65,  // 0-1
  "pages_processed": 98,
  "pages_total": 150,
  "elapsed_seconds": 300
}

// GET /document/{job_id}
{
  "job_id": "ingest-abc123",
  "licitacao_id": "123456",
  "status": "completed",
  "pages": 150,
  "content": {
    "texto_completo": "EDITAL DE LICITAÇÃO...",
    "secoes": {
      "objeto": "Contratação de serviços...",
      "habilitacao": "...",
      "julgamento": "..."
    },
    "tabelas": [
      {
        "secao": "itens",
        "headers": ["Item", "Descrição", "Qtd", "Valor Unit"],
        "rows": [
          ["1", "Notebook i5 8GB", "50", "3500.00"],
          ["2", "Mouse USB", "50", "25.00"]
        ]
      }
    ],
    "entidades": {
      "valores": [1200000.00, 3500.00, 25.00],
      "datas": ["2024-11-01", "2024-11-15"],
      "empresas_citadas": [],
      "cnpjs": []
    }
  },
  "storage": {
    "pdf_path": "/mnt/d/data/bronze/editais_raw/123456.pdf",
    "json_path": "/mnt/d/data/bronze/editais_text/123456.json"
  },
  "processing_time_seconds": 580,
  "created_at": "2024-10-21T10:00:00Z",
  "completed_at": "2024-10-21T10:09:40Z"
}

// Webhook callback (quando completed)
POST {callback_url}
{
  "job_id": "ingest-abc123",
  "licitacao_id": "123456",
  "status": "completed",
  "document_url": "http://ingestify.ai/document/ingest-abc123"
}
```

### 6.4 Configuração Ingestify.ai

```yaml
# ingestify.ai config.yaml

service:
  name: "ingestify.ai"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8001

docling:
  engine: "default"  # NOT "granite" (rule-based, faster)
  extract_tables: true
  extract_images: false
  ocr_enabled: true
  ocr_engine: "tesseract"
  languages: ["por"]

storage:
  type: "filesystem"  # or "minio" (future)
  filesystem:
    base_path: "/mnt/d/data/bronze/editais_raw"
  minio:
    enabled: false
    endpoint: "minio:9000"
    bucket: "gov-contracts-pdfs"

opensearch:
  hosts: ["http://opensearch:9200"]
  index_name: "editais_index"
  auth:
    username: "admin"
    password: "${OPENSEARCH_PASSWORD}"

celery:
  broker_url: "redis://redis:6379/0"
  result_backend: "redis://redis:6379/1"
  workers: 12  # i5 has 12 threads
  concurrency: 12
  task_timeout: 600  # 10 minutes

performance:
  max_pages_parallel: 12
  page_split_timeout: 60
  extraction_timeout: 30
  ocr_timeout: 60
```

---

## 7. Fluxo de Dados Completo

### 7.1 Fluxo End-to-End (Nova Licitação)

```
┌─────────────────────────────────────────────────────────────────┐
│  DIA 0: Licitação Publicada                                     │
│  ├─ PNCP publica nova licitação                                 │
│  ├─ Edital PDF disponível                                       │
│  └─ Dados estruturados via API                                  │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Cron trigger (2 AM daily)
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 02:00: BRONZE INGESTION (Airflow DAG 1)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task 1.1: Fetch Licitações (Portal Transparência + PNCP)      │
│  ├─ GET /api/licitacoes?data_abertura=2024-10-20               │
│  ├─ Pagination: loop até vazio                                 │
│  ├─ Parse JSON → DataFrame                                     │
│  └─ Save: /bronze/licitacoes/year=2024/month=10/day=20.parquet │
│     Duration: ~10 min (500 licitações)                         │
│                                                                 │
│  Task 1.2: Download Editais PDFs (parallel)                    │
│  ├─ Para cada licitacao.edital_url:                            │
│  │  └─ Download PDF                                            │
│  └─ Save: /bronze/editais_raw/{licitacao_id}.pdf               │
│     Duration: ~15 min (500 PDFs, 1MB avg)                      │
│                                                                 │
│  Task 1.3: Scrape Preços Mercado (weekly, not daily)           │
│  ├─ Mercado Livre API: notebooks, servidores, etc              │
│  ├─ Magazine Luiza API                                          │
│  └─ Save: /bronze/precos_mercado/marketplace/2024/10/20.parquet│
│     Duration: ~20 min (10k produtos)                            │
│                                                                 │
│  Task 1.4: Fetch CNPJ Updates (monthly)                        │
│  └─ Download bulk CSV → Save as Parquet                        │
│                                                                 │
│  Total Bronze Duration: ~30 minutes                            │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Sensor: wait bronze success
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 02:35: EDITAL PROCESSING (Ingestify.ai)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Trigger: Airflow DAG 1.5 (parallel com DAG 2)                 │
│  ├─ Para cada PDF novo em /bronze/editais_raw/:                │
│  │  ├─ POST ingestify.ai/upload                                │
│  │  └─ Celery queue: 500 jobs                                  │
│  └─ Workers: 12 parallel                                        │
│                                                                 │
│  Processing per PDF (avg 150 páginas):                         │
│  ├─ PageSplit: 1 PDF → 150 pages (1s)                         │
│  ├─ Docling: 150 pages // 12 workers (~2s/page)                │
│  │  └─ 150/12 = 13 pages/worker × 2s = 26s                    │
│  ├─ Aggregate: 150 → 1 JSON (2s)                              │
│  ├─ Store: Save JSON (1s)                                      │
│  └─ Index OpenSearch: Full-text (2s)                           │
│  Total per PDF: ~32 seconds                                    │
│                                                                 │
│  All 500 PDFs: 500/12 = 42 batches × 32s = ~22 minutes         │
│                                                                 │
│  Output:                                                        │
│  ├─ /bronze/editais_text/{licitacao_id}.json (500 arquivos)    │
│  └─ OpenSearch editais_index (500 documentos indexed)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Sensor: wait bronze + ingestify
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 03:00: SILVER CLEANING (Airflow DAG 2)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task 2.1: Clean Licitações                                    │
│  ├─ Read: /bronze/licitacoes/2024/10/20.parquet                │
│  ├─ Dedup: drop_duplicates(subset=['numero_licitacao', 'ano']) │
│  ├─ Nulls: dropna(subset=['valor_total', 'cnpj'])              │
│  ├─ Types: cast float, parse dates, normalize strings          │
│  ├─ Validate: Great Expectations (26 checks)                   │
│  └─ Save: /silver/licitacoes_clean/2024/10/20.parquet          │
│     Duration: ~5 min                                            │
│                                                                 │
│  Task 2.2: Parse Editais (from Ingestify.ai results)           │
│  ├─ Read: /bronze/editais_text/*.json (500 files)              │
│  ├─ Extract entidades:                                          │
│  │  ├─ Valores (regex + NER)                                   │
│  │  ├─ Datas (regex)                                           │
│  │  ├─ CNPJs (regex)                                           │
│  │  └─ Empresas (NER)                                          │
│  ├─ Structure seções:                                           │
│  │  ├─ Objeto                                                   │
│  │  ├─ Habilitação                                             │
│  │  └─ Julgamento                                              │
│  └─ Save: /silver/editais_parsed/{id}.json                     │
│     Duration: ~10 min (spaCy NER)                              │
│                                                                 │
│  Task 2.3: Analyze Cláusulas (Rules + LLM)                     │
│  ├─ Rule-based detection:                                       │
│  │  ├─ Prazo < 5 dias → flag_prazo_curto                      │
│  │  ├─ Marca específica citada → flag_marca_especifica         │
│  │  ├─ Requisitos raros → flag_requisitos_excessivos          │
│  │  └─ Score regras: 0-1                                       │
│  ├─ LLM analysis (Llama 3, batch):                             │
│  │  ├─ Prompt: "Analise este edital..."                        │
│  │  ├─ Output: Lista de problemas + severidade                 │
│  │  └─ Score LLM: 0-1                                          │
│  ├─ Combine: score_final = 0.7×regras + 0.3×LLM               │
│  └─ Save: /silver/editais_analysis/{id}.json                   │
│     Duration: ~30 min (LLM é lento, mas batch)                 │
│                                                                 │
│  Task 2.4: Normalize Preços Mercado                            │
│  ├─ Read: /bronze/precos_mercado/2024/10/20.parquet            │
│  ├─ Unify categories                                            │
│  ├─ Remove outliers (Z-score > 3)                              │
│  ├─ Dedup produtos idênticos                                   │
│  └─ Save: /silver/precos_normalized/2024-10.parquet            │
│     Duration: ~5 min                                            │
│                                                                 │
│  Task 2.5: Join All Data                                       │
│  ├─ licitacoes_clean                                            │
│  │  .merge(empresas, on='cnpj')                                │
│  │  .merge(ceis/cnep, on='cnpj')                               │
│  │  .merge(editais_parsed, on='licitacao_id')                  │
│  │  .merge(editais_analysis, on='licitacao_id')                │
│  └─ Save: /silver/joined/2024-10-20.parquet                    │
│     Duration: ~5 min                                            │
│                                                                 │
│  Total Silver Duration: ~55 minutes                            │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Sensor: wait silver
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 04:00: GOLD FEATURES (Airflow DAG 3)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task 3.1: Feature Engineering (Tabular)                       │
│  ├─ Read: /silver/joined/2024-10-20.parquet                    │
│  ├─ Engineer 30+ features:                                      │
│  │  ├─ Preço (8): log_valor, zscore, vs_media, percentile     │
│  │  ├─ Temporal (6): dia_semana, mes, dias_duracao            │
│  │  ├─ Empresa (8): num_licitacoes, taxa_vitoria, tempo_fund  │
│  │  ├─ Órgão (5): num_licitacoes_orgao, valor_medio          │
│  │  └─ Modalidade (3): one-hot encoding                       │
│  ├─ Match com Preços Mercado:                                  │
│  │  ├─ Categoria licitação → Categoria marketplace            │
│  │  ├─ Lookup: preco_medio, preco_mediano, p95               │
│  │  └─ Feature: preco_vs_mercado = valor/preco_medio         │
│  └─ Save: /gold/features/2024-10-20.parquet (SSD)              │
│     Duration: ~20 min (CPU intensive)                          │
│                                                                 │
│  Task 3.2: Generate Embeddings (NLP)                           │
│  ├─ Load: multilingual-e5-small                                │
│  ├─ Encode editais:                                             │
│  │  └─ embedding = model.encode(texto_completo)               │
│  ├─ Batch: 32 editais/batch                                    │
│  │  └─ 500 editais / 32 = 16 batches × 2s = 32s              │
│  └─ Save: /gold/embeddings/2024-10-20.npy                      │
│     Duration: ~2 min                                            │
│                                                                 │
│  Task 3.3: Save to PostgreSQL                                  │
│  ├─ licitacoes_gold: estrutura + features + scores             │
│  ├─ editais_metadata: flags, analysis, has_pdf                 │
│  ├─ precos_referencia: categoria, preco_medio, p95            │
│  └─ Create indexes: fraud_score, data_abertura, valor         │
│     Duration: ~10 min (bulk insert + indexes)                  │
│                                                                 │
│  Task 3.4: Update OpenSearch (Add Embeddings)                  │
│  ├─ Para cada documento em editais_index:                      │
│  │  └─ UPDATE: adicionar campo "embedding"                    │
│  └─ Agora: full-text + semantic search habilitado              │
│     Duration: ~5 min                                            │
│                                                                 │
│  Total Gold Duration: ~37 minutes                              │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Sensor: wait gold
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 04:40: ML INFERENCE (Airflow DAG 4)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task 4.1: Load Model                                          │
│  ├─ MLflow: load production model (XGBoost v2.0)               │
│  └─ SHAP explainer: load from artifacts                        │
│                                                                 │
│  Task 4.2: Batch Prediction                                    │
│  ├─ Read: /gold/features/2024-10-20.parquet                    │
│  ├─ Predict: fraud_score = model.predict_proba(X)              │
│  ├─ SHAP: explain top 100 suspeitas                            │
│  └─ Duration: ~5 min (500 licitações)                          │
│                                                                 │
│  Task 4.3: LLM Explanations (High Priority Only)               │
│  ├─ Filter: fraud_score > 0.8 (top suspeitas)                  │
│  ├─ Para cada (top 20):                                         │
│  │  ├─ Context:                                                 │
│  │  │  ├─ Licitação data                                       │
│  │  │  ├─ Edital analysis                                      │
│  │  │  ├─ SHAP values                                          │
│  │  │  └─ Similar contracts (RAG from OpenSearch)             │
│  │  ├─ Llama 3 generate (10s/explanation)                      │
│  │  └─ Output: 2-3 parágrafos em português                    │
│  └─ Duration: ~5 min (20 × 10s = 200s, paralelo)              │
│                                                                 │
│  Task 4.4: Save Predictions                                    │
│  ├─ PostgreSQL: UPDATE licitacoes_gold SET fraud_score=...     │
│  └─ OpenSearch: UPDATE contratos_index (add prediction)        │
│     Duration: ~2 min                                            │
│                                                                 │
│  Total Inference Duration: ~12 minutes                         │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  DIA 1 - 05:00: DISPONÍVEL PARA CONSULTA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ Dashboard: Lista 20 licitações suspeitas                    │
│  ✅ API: GET /contracts?fraud_score>0.8                         │
│  ✅ OpenSearch: Busca editais, semantic search                 │
│  ✅ PostgreSQL: Queries rápidas (<100ms)                        │
│                                                                 │
│  Usuário pode:                                                  │
│  ├─ Ver análise completa (edital + preços + explicação)        │
│  ├─ Buscar contratos similares (embeddings)                    │
│  ├─ Comparar com preços de mercado                             │
│  └─ Exportar relatórios                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

TIMELINE TOTAL: ~3 horas (02:00 → 05:00)
```

### 7.2 Duração por DAG

| DAG | Início | Duração | Tarefas Principais |
|-----|--------|---------|-------------------|
| **DAG 1: Bronze** | 02:00 | 30 min | Fetch APIs, Download PDFs, Scraping |
| **Ingestify.ai** | 02:35 | 22 min | PageSplit, Docling (parallel) |
| **DAG 2: Silver** | 03:00 | 55 min | Clean, Parse, Analyze, Join |
| **DAG 3: Gold** | 04:00 | 37 min | Features, Embeddings, DBs |
| **DAG 4: Inference** | 04:40 | 12 min | XGBoost, SHAP, LLM, Save |
| **TOTAL** | | **156 min** | **~2h 36min** |

---

## 8. Storage Strategy

### 8.1 Hardware Disponível

```
┌─────────────────────────────────────────────────────────────────┐
│                    HARDWARE SPECIFICATION                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🖥️ CPU: Intel i5-11600KF (Rocket Lake, 11ª Gen)              │
│  ├─ Cores: 6 físicos                                           │
│  ├─ Threads: 12 (Hyper-Threading)                              │
│  ├─ Clock: 3.9 GHz base, 4.9 GHz turbo                         │
│  ├─ Cache L3: 12 MB                                            │
│  ├─ TDP: 125W                                                   │
│  └─ Performance ML: Excelente (multi-threading)                │
│                                                                 │
│  🧠 RAM: 48 GB DDR4                                            │
│  ├─ Configuração: Provavelmente 2×16GB + 2×8GB                │
│  ├─ Velocidade: 2666-3200 MHz                                  │
│  ├─ Canais: Dual/Triple Channel                                │
│  └─ Performance ML: Excelente (datasets inteiros na RAM)       │
│                                                                 │
│  💾 SSD NVMe: 480 GB (WDC WDS480G2G0C)                         │
│  ├─ Interface: PCIe 3.0 x4                                     │
│  ├─ Leitura: ~3000-3500 MB/s                                   │
│  ├─ Escrita: ~2500-3000 MB/s                                   │
│  ├─ Mount: /mnt/c/ (WSL2)                                      │
│  └─ Uso: Sistema, código, Gold layer, DBs                     │
│                                                                 │
│  💿 HDD: 1.81 TB (WDC WD120G1G0A)                             │
│  ├─ RPM: 7200                                                   │
│  ├─ Interface: SATA III                                         │
│  ├─ Velocidade: ~120-150 MB/s (sequencial)                     │
│  ├─ Mount: /mnt/d/ (WSL2)                                      │
│  └─ Uso: Bronze, Silver layers, backups                       │
│                                                                 │
│  🎮 GPU: AMD Radeon RX 570 (4GB GDDR5)                        │
│  └─ Uso: Não (sem CUDA, ROCm complexo)                        │
│                                                                 │
│  🖧 OS: Windows 11 + WSL 2 (Ubuntu 22.04)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Alocação de Storage

```
┌─────────────────────────────────────────────────────────────────┐
│  SSD NVMe 480GB (/mnt/c/) - TRABALHO ATIVO                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /home/user/gov-contracts-ai/             5 GB                 │
│  ├─ Código fonte, configs                                      │
│  └─ Git repo                                                    │
│                                                                 │
│  /data/gold/                               50 GB               │
│  ├─ features/ (Parquet, zstd)                                  │
│  │  ├─ features_train.parquet              30 GB               │
│  │  ├─ features_val.parquet                7 GB                │
│  │  ├─ features_test.parquet               7 GB                │
│  │  └─ features_full.parquet               45 GB               │
│  ├─ embeddings/                            5 GB                │
│  │  └─ editais_embeddings.npy (50k × 384 × 4 bytes)           │
│  └─ agregados/                             5 GB                │
│                                                                 │
│  /var/lib/postgresql/                      30 GB               │
│  ├─ licitacoes_gold                        15 GB               │
│  ├─ editais_metadata                       5 GB                │
│  ├─ precos_referencia                      3 GB                │
│  ├─ predictions                            5 GB                │
│  └─ indexes                                2 GB                │
│                                                                 │
│  /var/lib/opensearch/                      40 GB               │
│  ├─ contratos_index                        15 GB               │
│  ├─ editais_index                          20 GB               │
│  ├─ produtos_index                         3 GB                │
│  └─ logs_index                             2 GB                │
│                                                                 │
│  /var/lib/redis/                           2 GB                │
│  └─ Cache, sessions                                            │
│                                                                 │
│  /opt/mlflow/                              20 GB               │
│  ├─ Experiments, models, artifacts                             │
│  └─ Model registry                                             │
│                                                                 │
│  /opt/ollama/models/                       15 GB               │
│  ├─ llama3.1:8b-instruct-q4_K_M           5 GB                │
│  └─ multilingual-e5-small                 500 MB              │
│                                                                 │
│  /tmp/ e /var/log/                         10 GB               │
│  └─ Temporários, logs                                          │
│                                                                 │
│  ─────────────────────────────────────────────                 │
│  TOTAL USADO:                              ~172 GB ✅          │
│  DISPONÍVEL:                               ~274 GB             │
│  UTILIZAÇÃO:                               38%                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  HDD 1.81TB (/mnt/d/) - ARMAZENAMENTO BULK                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /data/bronze/                             600 GB              │
│  ├─ licitacoes/ (Parquet, particionado)                        │
│  │  └─ year=YYYY/month=MM/day=DD/          100 MB/dia         │
│  │     Total 50k: ~100 GB                                      │
│  ├─ editais_raw/ (PDFs originais)                              │
│  │  └─ {licitacao_id}.pdf                  500 GB              │
│  │     50k × 1MB avg = 50 GB                                   │
│  │     (mas alguns chegam a 10MB)                              │
│  ├─ editais_text/ (JSON extraído)                              │
│  │  └─ {licitacao_id}.json                 200 GB              │
│  │     50k × 200KB avg = 10 GB                                 │
│  ├─ precos_mercado/ (scraping)                                 │
│  │  └─ marketplace/YYYY/MM/DD.parquet      300 GB              │
│  │     ~1M produtos/ano × 3 anos = 300 GB                      │
│  └─ cnpj/ (bulk)                                               │
│     └─ receita_YYYY-MM.parquet             50 GB               │
│        5M empresas = 50 GB                                      │
│                                                                 │
│  /data/silver/                             500 GB              │
│  ├─ licitacoes_clean/                      80 GB               │
│  ├─ editais_parsed/                        50 GB               │
│  ├─ editais_analysis/                      20 GB               │
│  ├─ precos_normalized/                     200 GB              │
│  └─ joined/                                150 GB              │
│                                                                 │
│  /backups/                                 200 GB              │
│  ├─ postgres_daily/                        100 GB              │
│  │  └─ Backup PostgreSQL (30 dias)                             │
│  ├─ gold_weekly/                           50 GB               │
│  │  └─ Backup Gold layer (4 semanas)                           │
│  └─ bronze_monthly/                        50 GB               │
│     └─ Snapshots mensais                                       │
│                                                                 │
│  ─────────────────────────────────────────────                 │
│  TOTAL USADO:                              ~1.3 TB ✅          │
│  DISPONÍVEL:                               ~510 GB             │
│  UTILIZAÇÃO:                               72%                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Estratégia de I/O

```
┌─────────────────────────────────────────────────────────────────┐
│                    I/O OPTIMIZATION STRATEGY                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  HDD (Sequencial 150 MB/s):                                     │
│  ✅ Bronze ingestion (append-only, write sequencial)            │
│  ✅ Silver processing (read sequencial, write sequencial)       │
│  ✅ Backups (grandes arquivos, não frequente)                   │
│  ✅ PDFs originais (acesso raro, storage barato)                │
│  ❌ Random reads (lento, evitar)                                │
│                                                                 │
│  SSD (Random 3000+ MB/s):                                       │
│  ✅ Gold features (ML training, random access)                  │
│  ✅ PostgreSQL (queries complexas, índices)                     │
│  ✅ OpenSearch (inverted index, vectors)                        │
│  ✅ Redis (cache sub-millisecond)                               │
│  ✅ Código, binários, modelos                                   │
│                                                                 │
│  Workflow:                                                      │
│  1. Ingest → HDD bronze (sequencial, OK)                       │
│  2. Clean → HDD silver (sequencial, OK)                        │
│  3. Features → SSD gold (random, necessário)                   │
│  4. Train → Read SSD gold (aleatório rápido)                   │
│  5. Inference → Read SSD gold + PostgreSQL                     │
│  6. API → PostgreSQL + OpenSearch (SSD)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Decisões Técnicas

### 9.1 Resumo de Decisões

| # | Decisão | Escolha | Alternativa Rejeitada | Justificativa |
|---|---------|---------|----------------------|---------------|
| **D1** | Search Engine | OpenSearch | Elasticsearch | Licença (Apache 2.0 vs Elastic License) |
| **D2** | Vector DB | OpenSearch (built-in) | Qdrant standalone | Elimina redundância com search |
| **D3** | Embeddings Model | multilingual-e5-small (384) | BERTimbau (768) | 2x mais rápido, metade storage, 95% qualidade |
| | | | e5-base (768) | Mais rápido que base, suficiente |
| **D4** | PDF Extraction | Docling (rule-based) | Granite-Docling-258M | 10x mais rápido, CPU-friendly |
| **D5** | Data Lake Format | Parquet | Delta Lake | Append-only workload (não precisa ACID) |
| | | | CSV/JSON | Compressão, performance |
| **D6** | Object Storage | Filesystem local | MinIO | Simplicidade para v1.0 |
| **D7** | LLM | Llama 3.1 8B Q4 | Claude/GPT API | Zero custo, soberania, privacidade |
| | | | Granite-Docling | Quantização melhor, português |
| **D8** | ML Algorithm | XGBoost (CPU) | Neural Networks (GPU) | Sem GPU, SOTA para tabular |
| | | | LightGBM | XGBoost mais maduro |
| **D9** | Parquet Compression | Snappy (Bronze/Silver) | Gzip | Balance speed/size |
| | | Zstd (Gold) | Snappy | Máxima compressão para SSD |
| **D10** | Database | PostgreSQL | MongoDB | Dados estruturados, ACID |
| | | | MySQL | Recursos avançados (JSONB, GIN) |
| **D11** | Microservice (PDF) | Ingestify.ai | Integrado no Airflow | Desacoplamento, reutilização |
| **D12** | Lakehouse Pattern | Multi-storage | Only Data Lake | Queries rápidas necessárias |
| | | | Only Data Warehouse | ML precisa flexibilidade |

### 9.2 Detalhamento de Decisões Críticas

#### **D1: OpenSearch vs Elasticsearch vs Qdrant**

```
REQUISITOS:
- Full-text search em editais (milhões de palavras)
- Semantic search (embeddings 384 dims)
- Logs e monitoring (ELK pattern)
- 100% open source

OPÇÕES:
┌─────────────────────────────────────────────────────────────────┐
│ Elasticsearch                                                   │
│ ✅ Maduro, comunidade enorme                                    │
│ ✅ Full-text excelente                                          │
│ ✅ Vectors suportados (dense_vector)                            │
│ ❌ Elastic License 2.0 (não open source real)                  │
│ ❌ Restrições: não pode oferecer como SaaS                      │
│ DECISÃO: ❌ Rejeitado por licença                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ OpenSearch (fork do ES 7.10)                                    │
│ ✅ Apache 2.0 (verdadeiro open source)                          │
│ ✅ API 99% compatível com Elasticsearch                         │
│ ✅ Full-text excelente (herança ES)                             │
│ ✅ Vectors suportados (k-NN plugin)                             │
│ ✅ Logs (OpenSearch Dashboards = Kibana)                        │
│ ✅ Comunidade ativa (AWS mantém)                                │
│ DECISÃO: ✅ ESCOLHIDO                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Qdrant (+ Elasticsearch para logs)                              │
│ ✅ Apache 2.0                                                    │
│ ✅ Vectors excelente (HNSW otimizado)                           │
│ ✅ Rust (performance)                                            │
│ ❌ Full-text básico                                             │
│ ❌ Precisa ES adicional para logs                               │
│ ❌ Redundância: 2 search engines                                │
│ DECISÃO: ❌ Rejeitado por complexidade                          │
└─────────────────────────────────────────────────────────────────┘

RESULTADO: OpenSearch único = Full-text + Vectors + Logs
```

#### **D3: Embeddings Model Selection**

```
REQUISITOS:
- Português (editais, licitações)
- CPU-friendly (i5-11600KF)
- Boa qualidade semantic search
- Storage viável (50k documentos)

BENCHMARK (50k docs, texto médio 5k chars):

┌──────────────────────────────────────────────────────────────────┐
│ BERTimbau (neuralmind/bert-base-portuguese-cased)               │
│ Dimensions: 768                                                  │
│ Model size: 420 MB                                               │
│ Encoding speed: 100 ms/doc (CPU)                                 │
│ Total time 50k: 50k × 100ms = 5000s = ~83 min                   │
│ Storage: 50k × 768 × 4 bytes = 150 MB (vetores)                 │
│         + 450 MB (HNSW index) = 600 MB                           │
│ Qualidade PT-BR: ⭐⭐⭐⭐⭐ (melhor)                              │
│ PROBLEMA: Não é sentence-transformer (precisa fine-tune)         │
│ DECISÃO: ❌ Qualidade top, mas complexidade desnecessária       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ multilingual-e5-base                                             │
│ Dimensions: 768                                                  │
│ Model size: 560 MB                                               │
│ Encoding speed: 80 ms/doc (CPU)                                  │
│ Total time 50k: 50k × 80ms = 4000s = ~67 min                    │
│ Storage: 600 MB                                                  │
│ Qualidade PT-BR: ⭐⭐⭐⭐ (excelente)                             │
│ NOTA: SOTA para multilingual, instruction-based                  │
│ DECISÃO: ⚠️ Bom, mas e5-small é suficiente                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ multilingual-e5-small (ESCOLHIDO)                                │
│ Dimensions: 384 (metade!)                                        │
│ Model size: 230 MB                                               │
│ Encoding speed: 40 ms/doc (2x mais rápido!)                      │
│ Total time 50k: 50k × 40ms = 2000s = ~33 min                    │
│ Storage: 50k × 384 × 4 = 75 MB (vetores)                        │
│         + 225 MB (HNSW index) = 300 MB (metade!)                 │
│ Qualidade PT-BR: ⭐⭐⭐⭐ (95% do base)                           │
│ VANTAGENS:                                                       │
│ ✅ 2x mais rápido                                                │
│ ✅ Metade do storage                                             │
│ ✅ Qualidade suficiente (95%)                                    │
│ ✅ Instruction-based (query: / passage:)                         │
│ ✅ SOTA multilingual                                             │
│ DECISÃO: ✅ ESCOLHIDO - Melhor custo-benefício                  │
└──────────────────────────────────────────────────────────────────┘

RESULTADO: multilingual-e5-small (384 dims)
- 33 min para indexar 50k (vs 83 min BERTimbau)
- 300 MB storage (vs 600 MB)
- Qualidade apenas 5% menor
```

#### **D4: Docling vs Granite-Docling**

```
REQUISITOS:
- Extrair texto de editais PDF (50-200 páginas)
- Tabelas importantes
- CPU-only (i5-11600KF, sem GPU)
- Escalar para 500+ PDFs/dia

BENCHMARK (Edital 150 páginas):

┌──────────────────────────────────────────────────────────────────┐
│ Docling (rule-based, MIT License)                               │
│ Type: Heuristic + regex + layout analysis                       │
│ Model size: ~50 MB                                               │
│ Speed: 2 seconds/página (CPU)                                    │
│ Total 150 páginas: 150 × 2s = 300s = 5 min                      │
│ RAM per worker: ~200 MB                                          │
│ Parallel: 12 workers = 150/12 = 13 pág/worker × 2s = 26s        │
│ Qualidade texto: 95%                                             │
│ Qualidade tabelas simples: 90%                                   │
│ Qualidade tabelas complexas: 70%                                 │
│ OCR support: ✅ Tesseract                                        │
│ VANTAGENS:                                                       │
│ ✅ CPU-friendly                                                  │
│ ✅ Rápido                                                        │
│ ✅ Paralelizável                                                 │
│ ✅ RAM baixo                                                     │
│ ⚠️ Tabelas complexas OK (70%)                                   │
│ DECISÃO: ✅ ESCOLHIDO - Suficiente para editais                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ Granite-Docling-258M (model-based)                               │
│ Type: LLM-based extraction (258M params)                         │
│ Model size: ~1 GB                                                │
│ Speed (CPU): 15-20 seconds/página                                │
│ Total 150 páginas: 150 × 18s = 2700s = 45 min                   │
│ Speed (GPU): 2-3 seconds/página                                  │
│ RAM per worker: ~2 GB                                            │
│ Parallel: 6 workers max (RAM limit) = 150/6 = 25 pág × 18s = 7.5min│
│ Qualidade texto: 98%                                             │
│ Qualidade tabelas simples: 95%                                   │
│ Qualidade tabelas complexas: 95%                                 │
│ OCR support: ✅ Built-in                                         │
│ PROBLEMAS:                                                       │
│ ❌ 9x mais lento (CPU)                                           │
│ ❌ Precisa GPU para ser viável                                   │
│ ❌ RAM alto (limita paralelismo)                                 │
│ ✅ Qualidade +5% (não justifica custo)                           │
│ DECISÃO: ❌ Rejeitado - Overkill, sem GPU                       │
└──────────────────────────────────────────────────────────────────┘

RESULTADO: Docling rule-based
- 26s por edital (parallel) vs 7.5min (Granite)
- 95% qualidade suficiente para editais governamentais
- Editais têm estrutura formal (regras funcionam bem)
```

---

## 10. Schemas de Dados

### 10.1 Bronze Layer Schemas

#### **Licitações (Parquet)**
```python
# /bronze/licitacoes/year=YYYY/month=MM/day=DD.parquet

schema = {
    # Identificação
    "numero_licitacao": "string",
    "ano": "int32",
    "modalidade": "string",  # Pregão, Concorrência, etc
    "situacao": "string",

    # Órgão
    "codigo_orgao": "string",
    "nome_orgao": "string",
    "esfera": "string",  # Federal, Estadual, Municipal
    "uf": "string",
    "municipio": "string",

    # Objeto
    "objeto": "string",
    "categoria": "string",  # TI, Obras, Serviços, etc
    "descricao_detalhada": "string",

    # Valores
    "valor_estimado": "float64",
    "valor_homologado": "float64",

    # Datas (as strings, sem parse)
    "data_abertura": "string",  # "2024-10-21"
    "data_homologacao": "string",
    "data_inicio": "string",
    "data_fim": "string",

    # Vencedor
    "cnpj_empresa_vencedora": "string",
    "nome_empresa_vencedora": "string",

    # Edital
    "edital_url": "string",
    "edital_hash": "string",  # SHA256 do PDF

    # Metadata
    "_source": "string",  # "portal_transparencia" ou "pncp"
    "_collected_at": "timestamp",

    # Particionamento
    "year": "int32",
    "month": "int32",
    "day": "int32"
}
```

#### **Editais Texto (JSON)**
```json
// /bronze/editais_text/{licitacao_id}.json

{
  "licitacao_id": "123456",
  "job_id": "ingest-abc123",
  "pages": 150,
  "texto_completo": "EDITAL DE LICITAÇÃO Nº 123/2024...",
  "secoes": {
    "preambulo": "O Município de XYZ...",
    "objeto": "1. DO OBJETO\n1.1 Contratação de...",
    "habilitacao": "2. DA HABILITAÇÃO\n2.1 Os licitantes...",
    "julgamento": "3. DO JULGAMENTO\n3.1 Será vencedor..."
  },
  "tabelas": [
    {
      "secao": "itens",
      "page": 5,
      "headers": ["Item", "Descrição", "Qtd", "Valor Unit"],
      "rows": [
        ["1", "Notebook Intel i5 8GB", "50", "3500.00"],
        ["2", "Mouse USB", "50", "25.00"]
      ]
    }
  ],
  "entidades_detectadas": {
    "valores": [1200000.00, 3500.00, 25.00],
    "datas": ["2024-11-01", "2024-11-15", "2024-12-31"],
    "cnpjs": [],
    "empresas_citadas": []
  },
  "metadata": {
    "pdf_path": "/mnt/d/data/bronze/editais_raw/123456.pdf",
    "pdf_size_bytes": 2048576,
    "pdf_hash": "sha256:abc...",
    "extraction_engine": "docling",
    "ocr_used": false
  },
  "processed_at": "2024-10-21T02:45:00Z"
}
```

#### **Preços Mercado (Parquet)**
```python
# /bronze/precos_mercado/marketplace/YYYY/MM/DD.parquet

schema = {
    # Produto
    "produto_id": "string",
    "titulo": "string",
    "descricao": "string",
    "marca": "string",
    "modelo": "string",

    # Classificação
    "categoria_marketplace": "string",  # Original do site
    "categoria_ml_id": "string",  # ID categoria Mercado Livre

    # Preço
    "preco": "float64",
    "moeda": "string",  # "BRL"
    "preco_original": "float64",  # Se houver desconto
    "desconto_percentual": "float32",

    # Vendedor
    "vendedor_id": "string",
    "vendedor_nome": "string",
    "vendedor_reputacao": "string",

    # Metadata
    "marketplace": "string",  # "mercadolivre", "magazineluiza", etc
    "url": "string",
    "disponivel": "bool",
    "estoque": "int32",

    # Coleta
    "_collected_at": "timestamp",
    "year": "int32",
    "month": "int32",
    "day": "int32"
}
```

### 10.2 Silver Layer Schemas

#### **Licitações Clean (Parquet)**
```python
# /silver/licitacoes_clean/year=YYYY/month=MM.parquet

schema = {
    # IDs
    "id": "int64",  # Auto-generated
    "licitacao_id": "string",  # numero_licitacao + ano

    # Órgão
    "codigo_orgao": "string",
    "nome_orgao": "string",
    "esfera": "category",  # Federal, Estadual, Municipal
    "uf": "category",
    "municipio": "string",
    "codigo_ibge": "string",

    # Objeto
    "objeto": "string",
    "categoria": "category",
    "subcategoria": "category",

    # Valores (validated, not null)
    "valor_estimado": "float64",
    "valor_homologado": "float64",
    "valor_final": "float64",  # Coalesce(homologado, estimado)

    # Datas (parsed datetime)
    "data_abertura": "date",
    "data_homologacao": "date",
    "data_inicio": "date",
    "data_fim": "date",

    # Durações derivadas
    "dias_duracao": "int32",
    "dias_abertura_homologacao": "int32",

    # Empresa (normalized CNPJ)
    "cnpj": "string",  # Apenas dígitos
    "cnpj_formatado": "string",  # 00.000.000/0000-00
    "empresa_nome": "string",

    # Modalidade
    "modalidade": "category",
    "tipo_licitacao": "category",
    "criterio_julgamento": "category",

    # Flags
    "tem_edital": "bool",
    "edital_processado": "bool",

    # Metadata
    "_source": "string",
    "_validated_at": "timestamp",

    # Particionamento
    "year": "int32",
    "month": "int32"
}
```

#### **Editais Parsed (JSON)**
```json
// /silver/editais_parsed/{licitacao_id}.json

{
  "licitacao_id": "123456",
  "parsed_from": "ingest-abc123",

  // Dados estruturados extraídos
  "dados_extraidos": {
    "objeto_resumo": "Contratação de consultoria em TI",
    "valor_estimado_edital": 1200000.00,
    "prazo_resposta_dias": 5,
    "prazo_execucao_meses": 12,
    "criterio_julgamento": "menor preço",
    "modalidade": "Pregão Eletrônico"
  },

  // Requisitos identificados
  "requisitos": [
    {
      "tipo": "certificacao",
      "descricao": "ISO 9001:2015",
      "obrigatorio": true,
      "secao": "4.2.1"
    },
    {
      "tipo": "experiencia",
      "descricao": "Mínimo 5 anos em projetos similares",
      "obrigatorio": true,
      "secao": "4.2.3"
    },
    {
      "tipo": "tecnico",
      "descricao": "Equipe com no mínimo 3 profissionais certificados",
      "obrigatorio": false,
      "secao": "4.3.2"
    }
  ],

  // Itens/Produtos
  "itens": [
    {
      "numero": "1",
      "descricao": "Consultoria em segurança da informação",
      "unidade": "hora",
      "quantidade": 500,
      "valor_unitario": 200.00,
      "valor_total": 100000.00
    },
    {
      "numero": "2",
      "descricao": "Desenvolvimento de sistema web",
      "unidade": "hora",
      "quantidade": 2000,
      "valor_unitario": 150.00,
      "valor_total": 300000.00
    }
  ],

  // Entidades NER
  "entidades": {
    "pessoas": [],
    "empresas_citadas": [],
    "valores_monetarios": [1200000.00, 200.00, 100000.00, 150.00, 300000.00],
    "datas_mencionadas": ["2024-11-01", "2024-11-15", "2025-11-01"],
    "localizacoes": ["Brasília", "DF"]
  },

  // Metadata
  "parsing": {
    "engine": "spacy_pt_core_news_lg",
    "confidence": 0.92,
    "parsed_at": "2024-10-21T03:15:00Z"
  }
}
```

#### **Editais Analysis (JSON)**
```json
// /silver/editais_analysis/{licitacao_id}_analysis.json

{
  "licitacao_id": "123456",
  "analyzed_from": "123456.json",

  // Flags (rule-based)
  "flags": {
    "clausula_restritiva": true,
    "prazo_curto": true,
    "requisitos_excessivos": false,
    "marca_especifica_citada": false,
    "valores_inconsistentes": false,
    "edital_incompleto": false
  },

  // Problemas identificados
  "problemas": [
    {
      "tipo": "prazo_resposta",
      "severidade": "alto",  // baixo, médio, alto
      "descricao": "Prazo de resposta de 5 dias é muito curto (recomendado: 8+ dias)",
      "localizacao": "Seção 3.1",
      "evidencia": "Os licitantes terão prazo de 5 (cinco) dias...",
      "score_impacto": 0.35
    },
    {
      "tipo": "clausula_restritiva",
      "severidade": "médio",
      "descricao": "Exige certificação rara (ISO 27001 específica para cloud)",
      "localizacao": "Seção 4.2.5",
      "evidencia": "Certificação ISO/IEC 27001:2022 específica para ambientes cloud...",
      "score_impacto": 0.25
    },
    {
      "tipo": "requisito_excessivo",
      "severidade": "baixo",
      "descricao": "Exige 3 certificações simultâneas (pode reduzir competição)",
      "localizacao": "Seção 4.2",
      "evidencia": "A empresa deverá possuir ISO 9001, ISO 27001 e CMMI nível 3...",
      "score_impacto": 0.12
    }
  ],

  // Scores
  "scores": {
    "score_restritivo_regras": 0.68,  // 0-1 (rule-based)
    "score_restritivo_llm": 0.75,     // 0-1 (LLM analysis)
    "score_restritivo_final": 0.71,   // Média ponderada
    "confidence": 0.87
  },

  // Análise LLM (Llama 3)
  "llm_analysis": {
    "summary": "Este edital apresenta indícios moderados de direcionamento...",
    "principais_preocupacoes": [
      "Prazo de resposta extremamente curto (5 dias)",
      "Certificação ISO 27001 cloud específica é rara no mercado brasileiro",
      "Combinação de 3 certificações simultâneas limita fornecedores"
    ],
    "recomendacao": "Investigar. Sugerido contato com órgão para esclarecimentos.",
    "model": "llama3.1:8b-instruct-q4_K_M",
    "generated_at": "2024-10-21T03:25:00Z"
  },

  // Metadata
  "analysis": {
    "version": "1.0",
    "analyzed_at": "2024-10-21T03:25:00Z",
    "duration_seconds": 45
  }
}
```

#### **Joined Full (Parquet)**
```python
# /silver/joined/YYYY-MM-DD.parquet
# Integra: licitacoes + empresas + cnpj + ceis/cnep + editais

schema = {
    # From licitacoes_clean (todas colunas)
    # +
    # From empresas (CNPJ enrichment)
    "empresa_razao_social": "string",
    "empresa_nome_fantasia": "string",
    "empresa_porte": "category",  # MEI, ME, EPP, Grande
    "empresa_natureza_juridica": "string",
    "empresa_capital_social": "float64",
    "empresa_data_abertura": "date",
    "empresa_situacao": "category",  # Ativa, Baixada, Suspensa

    # From CEIS/CNEP
    "empresa_punida_ceis": "bool",
    "empresa_punida_cnep": "bool",
    "data_inicio_punicao": "date",
    "data_fim_punicao": "date",
    "tipo_punicao": "string",
    "orgao_sancionador": "string",

    # From editais_parsed (selecionados)
    "edital_objeto_resumo": "string",
    "edital_prazo_resposta_dias": "int32",
    "edital_num_requisitos": "int32",
    "edital_num_itens": "int32",

    # From editais_analysis
    "edital_flag_restritivo": "bool",
    "edital_score_restritivo": "float32",
    "edital_num_problemas": "int32",

    # Metadata
    "_joined_at": "timestamp"
}
```

### 10.3 Gold Layer Schemas

#### **Features ML (Parquet)**
```python
# /gold/features/features_full.parquet

schema = {
    # IDs
    "id": "int64",
    "licitacao_id": "string",

    # Target (para training)
    "target": "int8",  # 0=normal, 1=fraude (se labeled)

    # ===== FEATURES (30+) =====

    # Preço (8)
    "valor_total": "float64",
    "log_valor_total": "float32",
    "preco_vs_media_categoria": "float32",
    "preco_vs_mediana_categoria": "float32",
    "zscore_preco": "float32",
    "percentile_preco": "float32",
    "preco_vs_mercado": "float32",  # NEW: ratio com preço marketplace
    "preco_vs_p95_mercado": "float32",  # NEW: vs percentil 95

    # Temporal (6)
    "dia_semana": "int8",
    "mes": "int8",
    "trimestre": "int8",
    "ano": "int16",
    "dias_duracao": "int32",
    "dias_ate_inicio": "int32",

    # Empresa (8)
    "num_licitacoes_anteriores": "int32",
    "valor_total_historico": "float64",
    "taxa_vitoria": "float32",
    "tempo_desde_fundacao": "float32",  # Anos
    "num_socios": "int16",
    "capital_social": "float64",
    "flag_empresa_punida": "int8",  # 0/1
    "num_contratos_ativos": "int16",

    # Órgão (5)
    "num_licitacoes_orgao": "int32",
    "valor_medio_orgao": "float64",
    "taxa_suspeita_historica_orgao": "float32",
    "esfera_encoded": "int8",  # 0=Fed, 1=Est, 2=Mun
    "regiao_encoded": "int8",  # 0=N, 1=NE, 2=CO, 3=SE, 4=S

    # Modalidade (3)
    "modalidade_encoded": "int8",
    "tipo_licitacao_encoded": "int8",
    "criterio_julgamento_encoded": "int8",

    # Edital (5) - NEW
    "edital_score_restritivo": "float32",
    "edital_num_problemas": "int8",
    "edital_prazo_curto_flag": "int8",
    "edital_requisitos_excessivos_flag": "int8",
    "edital_marca_especifica_flag": "int8",

    # Metadata
    "_feature_version": "string",  # "v1.0"
    "_created_at": "timestamp"
}
```

#### **PostgreSQL: licitacoes_gold**
```sql
CREATE TABLE licitacoes_gold (
    -- IDs
    id BIGSERIAL PRIMARY KEY,
    licitacao_id VARCHAR(50) UNIQUE NOT NULL,

    -- Basic info
    numero_licitacao VARCHAR(50) NOT NULL,
    ano INTEGER NOT NULL,
    descricao TEXT,
    objeto TEXT,

    -- Valores
    valor_total DECIMAL(15, 2),
    valor_homologado DECIMAL(15, 2),

    -- Datas
    data_abertura DATE,
    data_homologacao DATE,

    -- Órgão
    codigo_orgao VARCHAR(20),
    nome_orgao VARCHAR(200),
    esfera VARCHAR(20),
    uf CHAR(2),
    municipio VARCHAR(100),

    -- Empresa
    cnpj VARCHAR(14),
    empresa_nome VARCHAR(200),
    flag_empresa_punida BOOLEAN DEFAULT FALSE,

    -- Modalidade
    modalidade VARCHAR(50),
    tipo_licitacao VARCHAR(50),

    -- Features selecionadas (subset do ML)
    log_valor_total FLOAT,
    preco_vs_media_categoria FLOAT,
    preco_vs_mercado FLOAT,
    dias_duracao INTEGER,
    tempo_desde_fundacao FLOAT,
    num_licitacoes_anteriores INTEGER,

    -- Edital
    edital_score_restritivo FLOAT,
    edital_num_problemas INTEGER,

    -- ML Predictions (populated após inference)
    fraud_score FLOAT,
    predicted_class INTEGER,  -- 0=normal, 1=fraude
    shap_top_features JSONB,  -- Top 5 features + values
    explanation_text TEXT,  -- LLM explanation
    similar_contracts JSONB,  -- Array de IDs similares (RAG)

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    predicted_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_fraud_score ON licitacoes_gold(fraud_score DESC);
CREATE INDEX idx_data_abertura ON licitacoes_gold(data_abertura DESC);
CREATE INDEX idx_valor_total ON licitacoes_gold(valor_total DESC);
CREATE INDEX idx_cnpj ON licitacoes_gold(cnpj);
CREATE INDEX idx_modalidade ON licitacoes_gold(modalidade);
CREATE INDEX idx_orgao ON licitacoes_gold(codigo_orgao);

-- Full-text search
CREATE INDEX idx_descricao_fts ON licitacoes_gold
USING gin(to_tsvector('portuguese', descricao));
```

#### **PostgreSQL: editais_metadata**
```sql
CREATE TABLE editais_metadata (
    id BIGSERIAL PRIMARY KEY,
    licitacao_id VARCHAR(50) UNIQUE NOT NULL REFERENCES licitacoes_gold(licitacao_id),

    -- PDF info
    has_pdf BOOLEAN DEFAULT FALSE,
    pdf_path TEXT,
    pdf_size_bytes BIGINT,
    pdf_pages INTEGER,

    -- Processing
    ingestify_job_id VARCHAR(100),
    processing_status VARCHAR(20),  -- queued, processing, completed, failed
    processed_at TIMESTAMP,
    processing_duration_seconds INTEGER,

    -- Analysis
    has_analysis BOOLEAN DEFAULT FALSE,
    score_restritivo FLOAT,
    num_problemas INTEGER,
    problemas JSONB,  -- Array de problemas

    -- Flags
    flag_prazo_curto BOOLEAN DEFAULT FALSE,
    flag_clausula_restritiva BOOLEAN DEFAULT FALSE,
    flag_requisitos_excessivos BOOLEAN DEFAULT FALSE,
    flag_marca_especifica BOOLEAN DEFAULT FALSE,

    -- LLM analysis
    llm_summary TEXT,
    llm_recomendacao VARCHAR(50),  -- "investigar", "monitorar", "aprovar"

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_score_restritivo ON editais_metadata(score_restritivo DESC);
CREATE INDEX idx_has_analysis ON editais_metadata(has_analysis);
```

#### **PostgreSQL: precos_referencia**
```sql
CREATE TABLE precos_referencia (
    id BIGSERIAL PRIMARY KEY,

    -- Categoria
    categoria VARCHAR(100) NOT NULL,
    subcategoria VARCHAR(100),
    item_tipo VARCHAR(100),  -- "notebook", "servidor", "consultoria", etc

    -- Estatísticas de preço
    preco_medio DECIMAL(15, 2),
    preco_mediano DECIMAL(15, 2),
    preco_p25 DECIMAL(15, 2),
    preco_p75 DECIMAL(15, 2),
    preco_p90 DECIMAL(15, 2),
    preco_p95 DECIMAL(15, 2),
    desvio_padrao DECIMAL(15, 2),

    -- Metadata
    num_observacoes INTEGER,
    data_inicio DATE,  -- Período dos dados
    data_fim DATE,
    marketplaces TEXT[],  -- Array: ["mercadolivre", "magazineluiza"]

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_categoria ON precos_referencia(categoria);
CREATE INDEX idx_item_tipo ON precos_referencia(item_tipo);
```

#### **OpenSearch: contratos_index**
```json
// Mapping para contratos_index

{
  "mappings": {
    "properties": {
      // IDs
      "licitacao_id": {"type": "keyword"},
      "numero_licitacao": {"type": "keyword"},

      // Full-text search
      "descricao": {
        "type": "text",
        "analyzer": "portuguese"
      },
      "objeto": {
        "type": "text",
        "analyzer": "portuguese"
      },

      // Structured fields
      "valor_total": {"type": "float"},
      "data_abertura": {"type": "date"},
      "modalidade": {"type": "keyword"},
      "orgao_nome": {"type": "keyword"},
      "empresa_nome": {"type": "keyword"},
      "cnpj": {"type": "keyword"},

      // ML predictions
      "fraud_score": {"type": "float"},
      "predicted_class": {"type": "integer"},

      // Embedding para semantic search
      "embedding": {
        "type": "knn_vector",
        "dimension": 384,  // multilingual-e5-small
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 128,
            "m": 24
          }
        }
      },

      // Metadata
      "indexed_at": {"type": "date"}
    }
  },
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 100
    }
  }
}
```

#### **OpenSearch: editais_index**
```json
// Mapping para editais_index (from Ingestify.ai + enrichments)

{
  "mappings": {
    "properties": {
      // IDs
      "licitacao_id": {"type": "keyword"},
      "job_id": {"type": "keyword"},

      // Full-text search
      "texto_completo": {
        "type": "text",
        "analyzer": "portuguese"
      },
      "objeto": {
        "type": "text",
        "analyzer": "portuguese"
      },

      // Seções (nested)
      "secoes": {
        "type": "nested",
        "properties": {
          "nome": {"type": "keyword"},
          "conteudo": {
            "type": "text",
            "analyzer": "portuguese"
          }
        }
      },

      // Tabelas (nested)
      "tabelas": {
        "type": "nested",
        "properties": {
          "secao": {"type": "keyword"},
          "headers": {"type": "keyword"},
          "rows": {"type": "text"}
        }
      },

      // Analysis flags
      "flags": {
        "type": "object",
        "properties": {
          "clausula_restritiva": {"type": "boolean"},
          "prazo_curto": {"type": "boolean"},
          "requisitos_excessivos": {"type": "boolean"},
          "marca_especifica": {"type": "boolean"}
        }
      },

      "score_restritivo": {"type": "float"},
      "num_problemas": {"type": "integer"},

      // Embedding para semantic search
      "embedding": {
        "type": "knn_vector",
        "dimension": 384,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 128,
            "m": 24
          }
        }
      },

      // Metadata
      "pages": {"type": "integer"},
      "processed_at": {"type": "date"},
      "indexed_at": {"type": "date"}
    }
  }
}
```

---

## 11. Performance & Scalability

### 11.1 Performance Benchmarks (50k licitações)

| Workload | Hardware | Duration | Throughput | Bottleneck |
|----------|----------|----------|------------|------------|
| **Bronze Ingestion** | HDD write | 30 min | 1.6k licitações/min | Network (API calls) |
| **PDF Processing** | CPU (12 threads) | 22 min | 23 PDFs/min | CPU (Docling) |
| **Silver Cleaning** | HDD read/write | 55 min | 900 licitações/min | CPU (validation) |
| **Feature Engineering** | CPU + RAM | 20 min | 2.5k licitações/min | CPU (calculations) |
| **Embeddings** | CPU | 33 min | 1.5k docs/min | CPU (model inference) |
| **XGBoost Training** | CPU + RAM | 5 min | N/A | CPU (gradient boosting) |
| **XGBoost Inference** | CPU | <5 min | 10k pred/min | CPU (ensemble) |
| **LLM Explanations** | CPU | 5 min | 4 explanations/min | CPU (Llama 3) |
| **API Query (PostgreSQL)** | SSD + DB | <100ms | 1k req/min | Network, DB indexes |
| **Semantic Search (OpenSearch)** | SSD + vectors | <200ms | 500 req/min | Vector search (HNSW) |

### 11.2 Escalabilidade

#### **Capacidade Atual (i5 + 48GB RAM)**

| Métrica | Atual (50k) | Limite Hardware | Limite Storage |
|---------|-------------|-----------------|----------------|
| **Licitações** | 50k | ~500k (RAM) | ~500k (SSD 480GB) |
| **Editais PDF** | 50k (50GB) | ~500k | ~500GB (HDD) |
| **Embeddings** | 50k (300MB) | ~500k (3GB) | ~500k (OK SSD) |
| **PostgreSQL** | 50k (150MB) | ~1M (10GB) | ~1M (OK SSD) |
| **OpenSearch** | 50k (100MB) | ~1M (15GB) | ~1M (OK SSD) |
| **Parquet Gold** | 50k (50MB) | ~500k (500MB) | ~500k (OK SSD) |

**Conclusão:** Hardware atual suporta **500k licitações** antes de precisar upgrade.

#### **Paths de Escalabilidade**

```
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1: Single Machine (Atual)                                │
│  Capacidade: 50k-500k licitações                                │
│  Hardware: i5 + 48GB RAM + SSD 480GB + HDD 1.8TB               │
│  Custo: R$ 0 (já possui)                                        │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Quando > 500k
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2: Vertical Scaling                                       │
│  Upgrades:                                                       │
│  ├─ RAM: 48GB → 128GB (R$ 2k)                                  │
│  ├─ SSD: 480GB → 2TB (R$ 1k)                                   │
│  └─ HDD: 1.8TB → 8TB (R$ 800)                                  │
│  Capacidade: 500k → 2M licitações                               │
│  Custo: ~R$ 3.8k                                                │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼ Quando > 2M
┌─────────────────────────────────────────────────────────────────┐
│  FASE 3: Horizontal Scaling (Cluster)                           │
│  Arquitetura:                                                    │
│  ├─ 1 master (Airflow scheduler)                                │
│  ├─ 3-5 workers (processing, CPU tasks)                         │
│  ├─ PostgreSQL: Master-Replica (read scaling)                   │
│  ├─ OpenSearch: 3-node cluster (sharding)                       │
│  └─ Shared storage: NFS ou Ceph                                 │
│  Capacidade: 2M → 10M+ licitações                               │
│  Custo: ~R$ 50-100k (infraestrutura governo)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 11.3 Otimizações Futuras

**Performance:**
- [ ] Dask para feature engineering paralelo (se > 100GB datasets)
- [ ] DuckDB para queries analíticas rápidas (alternativa ao pandas)
- [ ] Quantização INT8 para embeddings (75MB → 37MB, -2% qualidade)
- [ ] GPU para Llama 3 (10s → 1s por explicação)
- [ ] Caching agressivo de embeddings (Redis)

**Escalabilidade:**
- [ ] Particionamento PostgreSQL (por ano, esfera)
- [ ] OpenSearch sharding (3+ nodes)
- [ ] Airflow Celery Executor (distributed workers)
- [ ] MinIO cluster (multi-node, distributed erasure coding)

---

## 12. MinIO Configuration

### 12.1 Estrutura de Buckets

```
MinIO Server (minio:9000)
│
├─ bronze/                       # Raw data
│  ├─ licitacoes/
│  │  └─ year=YYYY/month=MM/day=DD/*.parquet
│  ├─ editais_raw/
│  │  └─ {licitacao_id}.pdf
│  ├─ editais_text/
│  │  └─ {licitacao_id}.json
│  ├─ precos_mercado/
│  │  └─ marketplace/YYYY/MM/DD/*.parquet
│  └─ cnpj/
│     └─ receita_YYYY-MM.parquet
│
├─ silver/                       # Clean data
│  ├─ licitacoes_clean/
│  ├─ editais_parsed/
│  ├─ editais_analysis/
│  ├─ precos_normalized/
│  └─ joined_full/
│
├─ gold/                         # ML-ready features
│  ├─ features_ml/
│  ├─ embeddings/
│  └─ agregados/
│
├─ mlflow/                       # MLflow artifacts
│  ├─ experiments/
│  ├─ models/
│  └─ artifacts/
│
├─ backups/                      # Backups
│  ├─ postgres/
│  ├─ opensearch/
│  └─ gold_snapshots/
│
└─ tmp/                          # Temporary processing
   └─ airflow_tmp/
```

### 12.2 Configuração Docker Compose

```yaml
services:
  minio:
    image: minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Console UI
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      MINIO_VOLUMES: "/data"
    volumes:
      - /var/storage:/data      # HDD 1.81TB backend
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://minio:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # Inicialização de buckets (run once)
  minio-init:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      mc alias set myminio http://minio:9000 minioadmin minioadmin;
      mc mb --ignore-existing myminio/bronze;
      mc mb --ignore-existing myminio/silver;
      mc mb --ignore-existing myminio/gold;
      mc mb --ignore-existing myminio/mlflow;
      mc mb --ignore-existing myminio/backups;
      mc mb --ignore-existing myminio/tmp;
      mc version enable myminio/bronze;
      mc version enable myminio/silver;
      mc version enable myminio/gold;
      mc version enable myminio/mlflow;
      exit 0;
      "
```

### 12.3 Python Client Configuration

```python
# backend/app/core/storage.py
import boto3
from botocore.client import Config

def get_s3_client():
    """Get MinIO S3 client"""
    return boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

# Pandas integration with s3fs
import s3fs

fs = s3fs.S3FileSystem(
    key='minioadmin',
    secret='minioadmin',
    client_kwargs={'endpoint_url': 'http://minio:9000'}
)

# Read Parquet from S3
import pandas as pd
df = pd.read_parquet('s3://bronze/licitacoes/year=2025/month=10/day=21/data.parquet', filesystem=fs)

# Write Parquet to S3
df.to_parquet('s3://silver/licitacoes_clean/2025-10-21.parquet', filesystem=fs, compression='snappy')
```

### 12.4 Benefícios da Escolha MinIO

| Benefício | Descrição |
|-----------|-----------|
| **S3 API Compatibility** | Compatível com boto3, AWS SDK, s3fs, pandas, pyarrow |
| **Flexibilidade I/O** | Múltiplos clientes simultâneos (Airflow, MLflow, Ingestify) |
| **Versioning** | Auditoria completa, rollback de dados |
| **Escalabilidade** | Fácil migração para AWS S3 se necessário |
| **Performance** | Cache inteligente, multipart upload |
| **Zero custo** | Open source AGPL v3 |
| **Familiar Tooling** | Mesma API do S3 AWS |
| **Enterprise-ready** | Erasure coding, replication, encryption |

---

## 📝 Conclusão

Este documento define a **arquitetura Lakehouse completa** do Gov Contracts AI, incluindo:

✅ **Padrão Lakehouse** (Data Lake MinIO S3 + Data Warehouse + Search Engine)
✅ **Medallion Architecture** (Bronze → Silver → Gold)
✅ **MinIO S3-compatible** (Object storage com API S3, versioning, escalabilidade)
✅ **100% Open Source** (zero vendor lock-in)
✅ **Integração Ingestify.ai** (microserviço PDF processing)
✅ **OpenSearch unificado** (full-text + semantic + logs)
✅ **Embeddings e5-small** (384 dims, CPU-friendly)
✅ **Docling rule-based** (rápido, suficiente)
✅ **Storage strategy** (MinIO S3 sobre HDD + PostgreSQL/OpenSearch em SSD)
✅ **Schemas completos** (Bronze/Silver/Gold)
✅ **Fluxo end-to-end** (3 horas: coleta → features → predictions)
✅ **Performance benchmarks** (50k licitações)
✅ **Escalabilidade** (até 500k single machine, 10M+ cluster)

**Próximos passos:** Implementação seguindo as fases 1-5 do PRD (20 semanas).

---

**Documento aprovado para implementação.**
**Versão:** 1.1
**Data:** 21 de Outubro de 2025
