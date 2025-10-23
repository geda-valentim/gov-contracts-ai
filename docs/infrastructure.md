# 🏗️ Infraestrutura Gov Contracts AI

## 📋 Visão Geral

Stack completa de Data Science & ML para detecção de fraudes em licitações brasileiras.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA DE APLICAÇÃO                          │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Backend  │  Next.js Frontend  │  ML Models (XGBoost)  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAMADA DE ORQUESTRAÇÃO                        │
├─────────────────────────────────────────────────────────────────┤
│          Apache Airflow (Pipelines & Scheduling)                │
│   • Ingestão de dados (PNCP API)                               │
│   • Transformações ETL                                          │
│   • Training de modelos ML                                      │
│   • Deploy automático                                           │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAMADA DE DADOS                             │
├──────────────────┬──────────────────┬─────────────────────────┤
│   Data Lake      │  Data Warehouse  │    Search Engine        │
│   (MinIO S3)     │  (PostgreSQL 15) │   (OpenSearch 3)        │
│                  │                  │                         │
│  bronze  🥉   │  • Structured    │  • Full-text search     │
│  silver  🥈   │  • OLAP queries  │  • Semantic search      │
│  gold    🥇   │  • pg_vector     │  • NLP analysis         │
│  mlflow          │  • Analytics     │  • Aggregations         │
│  backups         │                  │                         │
│  tmp             │                  │                         │
└──────────────────┴──────────────────┴─────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                CAMADA DE INFRAESTRUTURA                         │
├──────────────────┬──────────────────┬─────────────────────────┤
│   Cache/Queue    │   ML Tracking    │    Monitoring           │
│   (Redis 7)      │   (MLflow)       │   (Prometheus)          │
└──────────────────┴──────────────────┴─────────────────────────┘
```

---

## 🐳 Serviços Docker

### 📊 Data Layer (Camada de Dados)

#### PostgreSQL 15
- **Container:** `govcontracts-postgres`
- **Porta:** `5433:5432` (externa: 5433)
- **Databases:** `govcontracts`, `mlflow`, `airflow`
- **User/Pass:** `admin/dev123`
- **IP:** `172.30.0.5`
- **Volume:** `postgres_data`

**Uso:**
- Data Warehouse para dados estruturados
- Backend do MLflow (experiments tracking)
- Backend do Airflow (metadata)

#### Redis 7
- **Container:** `govcontracts-redis`
- **Porta:** `6381:6379` (externa: 6381)
- **IP:** `172.30.0.6`
- **Volume:** `redis_data`

**Uso:**
- Cache de predições (TTL 24h)
- Message broker para Celery (Airflow workers)
- Session storage

#### MinIO (S3-compatible)
- **Container:** `govcontracts-minio`
- **Porta API:** `9000:9000` (externa: 9000)
- **Porta Console:** `9001:9001` (externa: 9001)
- **User/Pass:** `minioadmin/minioadmin`
- **IP:** `172.30.0.10`
- **Volume:** `minio_data`

**Buckets:**
```
bronze/          # 🥉 Raw data (imutável, versionado)
├─ licitacoes/      #   Particionado: year=YYYY/month=MM/day=DD/
├─ editais_raw/     #   PDFs originais
├─ editais_text/    #   Texto extraído (JSON)
├─ precos_mercado/  #   Preços de referência
└─ cnpj/            #   Dados da Receita Federal

silver/          # 🥈 Clean data (validado, normalizado)
├─ licitacoes_clean/
├─ editais_parsed/
├─ editais_analysis/
└─ precos_normalized/

gold/            # 🥇 ML-ready (features engineered)
├─ features_ml/
├─ embeddings/
└─ agregados/

mlflow/             # Artefatos ML (modelos, plots, metrics)
backups/            # Backups do sistema
tmp/                # Arquivos temporários (auto-delete 7 dias)
```

**Console UI:** http://localhost:9001

#### OpenSearch 3
- **Container:** `govcontracts-opensearch`
- **Porta API:** `9201:9200` (externa: 9201)
- **Porta Performance:** `9601:9600` (externa: 9601)
- **IP:** `172.30.0.11`
- **Volume:** `opensearch_data`
- **Memória JVM:** 512MB

**Uso:**
- Full-text search em editais
- Busca semântica (vector search)
- Análise NLP com BERT
- Detecção de cláusulas restritivas

#### OpenSearch Dashboards
- **Container:** `govcontracts-opensearch-dashboards`
- **Porta:** `5602:5601` (externa: 5602)
- **IP:** `172.30.0.12`

**Dashboards UI:** http://localhost:5602

---

### 🤖 ML & Tracking Layer

#### MLflow
- **Container:** `govcontracts-mlflow`
- **Porta:** `5000:5000`
- **IP:** `172.30.0.7`
- **Volume:** `mlflow_data`

**Uso:**
- Experiment tracking (hiperparâmetros, métricas)
- Model registry (versionamento de modelos)
- Artifact storage (modelos ONNX, SHAP explainers)

**MLflow UI:** http://localhost:5000

**Integração:**
- Backend: PostgreSQL (`mlflow` database)
- Artifact Store: MinIO S3 (`s3://mlflow/artifacts`)

---

### 🔄 Orchestration Layer (Airflow)

#### Airflow Webserver
- **Container:** `govcontracts-airflow-webserver`
- **Porta:** `8081:8080` (externa: 8081)
- **IP:** `172.30.0.20`

**UI:** http://localhost:8081
**User/Pass:** `airflow/airflow`

#### Airflow Scheduler
- **Container:** `govcontracts-airflow-scheduler`
- **IP:** `172.30.0.21`

**Responsabilidades:**
- Agendar DAGs (schedule_interval)
- Disparar task instances
- Monitorar dependências

#### Airflow Worker (Celery)
- **Container:** `govcontracts-airflow-worker`
- **IP:** `172.30.0.22`

**Responsabilidades:**
- Executar tasks
- Processar jobs paralelos
- Integração com MinIO, PostgreSQL, OpenSearch

#### Airflow Triggerer
- **Container:** `govcontracts-airflow-triggerer`
- **IP:** `172.30.0.23`

**Responsabilidades:**
- Deferrable tasks (async operators)
- Event-driven tasks

#### Airflow Init
- **Container:** `govcontracts-airflow-init` (executa uma vez)
- **Responsabilidades:**
  - Criar database `airflow` no PostgreSQL
  - Rodar migrations (alembic)
  - Criar usuário admin (airflow/airflow)
  - Configurar permissões de diretórios

**Volumes Airflow:**
```
./airflow/dags/      # DAG definitions (Python files)
./airflow/logs/      # Execution logs
./airflow/plugins/   # Custom operators, hooks, sensors
./airflow/config/    # Custom airflow.cfg
```

**Pacotes instalados:**
- `apache-airflow-providers-amazon` (S3 operators)
- `boto3` (AWS SDK)
- `s3fs` (Filesystem-like S3 access)

---

## 🌐 Rede Docker

**Nome:** `govcontracts-network`
**Tipo:** bridge
**Subnet:** `172.30.0.0/16`

**Motivo:** Subnet customizada para evitar conflitos com outros projetos Docker.

**Mapeamento de IPs:**
```
172.30.0.5   → PostgreSQL
172.30.0.6   → Redis
172.30.0.7   → MLflow
172.30.0.10  → MinIO
172.30.0.11  → OpenSearch
172.30.0.12  → OpenSearch Dashboards
172.30.0.20  → Airflow Webserver
172.30.0.21  → Airflow Scheduler
172.30.0.22  → Airflow Worker
172.30.0.23  → Airflow Triggerer
```

---

## 🚀 Quick Start

### 1. Iniciar todos os serviços
```bash
docker compose up -d
```

### 2. Verificar status
```bash
docker compose ps
```

Aguardar até todos os containers estarem **healthy**.

### 3. Acessar interfaces

- **Airflow UI:** http://localhost:8081 (airflow/airflow)
- **MLflow UI:** http://localhost:5000
- **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin)
- **OpenSearch Dashboards:** http://localhost:5602

### 4. Verificar logs
```bash
# Ver logs de todos os serviços
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f airflow-scheduler
docker compose logs -f minio
docker compose logs -f opensearch
```

### 5. Parar tudo
```bash
docker compose down
```

**⚠️ ATENÇÃO:** Para remover volumes (apaga todos os dados):
```bash
docker compose down -v
```

---

## 📦 Volumes Docker

Todos os dados persistentes são armazenados em volumes gerenciados pelo Docker:

```bash
# Ver volumes
docker volume ls | grep gov-contracts-ai

# Inspecionar volume
docker volume inspect gov-contracts-ai_postgres_data

# Ver uso de espaço
docker system df -v

# Backup de um volume (exemplo: PostgreSQL)
docker run --rm \
  -v gov-contracts-ai_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore de um volume
docker run --rm \
  -v gov-contracts-ai_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

**Volumes criados:**
- `postgres_data` (~500MB)
- `redis_data` (~50MB)
- `mlflow_data` (~100MB)
- `minio_data` (~1GB+)
- `opensearch_data` (~500MB)

---

## 🔧 Configuração de Desenvolvimento

### Variáveis de Ambiente

Crie um arquivo `.env` no diretório raiz:

```bash
# MinIO
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=admin
POSTGRES_PASSWORD=dev123
POSTGRES_DB=govcontracts

# Redis
REDIS_HOST=localhost
REDIS_PORT=6381

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9201

# Airflow
AIRFLOW_HOME=/opt/airflow
AIRFLOW__CORE__EXECUTOR=CeleryExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://admin:dev123@localhost:5433/airflow
```

### Conectar do Host (Python)

```python
# MinIO / S3
import boto3
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# PostgreSQL
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    user='admin',
    password='dev123',
    database='govcontracts'
)

# Redis
import redis
r = redis.Redis(host='localhost', port=6381, decode_responses=True)

# OpenSearch
from opensearchpy import OpenSearch
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9201}],
    http_auth=None,  # Security disabled in dev
    use_ssl=False
)
```

### Conectar do Container (Python DAGs do Airflow)

**Importante:** Dentro da rede Docker, use **nomes de serviços** e **portas internas**:

```python
# MinIO / S3 (dentro do Airflow)
import boto3
s3 = boto3.client(
    's3',
    endpoint_url='http://minio:9000',  # ← porta INTERNA 9000
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# PostgreSQL (dentro do Airflow)
conn = psycopg2.connect(
    host='postgres',  # ← nome do serviço
    port=5432,        # ← porta INTERNA 5432
    user='admin',
    password='dev123',
    database='govcontracts'
)

# Redis (dentro do Airflow)
r = redis.Redis(host='redis', port=6379)  # ← porta INTERNA 6379

# OpenSearch (dentro do Airflow)
client = OpenSearch(
    hosts=[{'host': 'opensearch', 'port': 9200}],  # ← porta INTERNA 9200
    use_ssl=False
)
```

---

## 🔍 Troubleshooting

### Containers não iniciam

```bash
# Ver logs de erro
docker compose logs

# Ver status detalhado
docker compose ps -a

# Reiniciar um serviço específico
docker compose restart postgres
```

### Porta em uso

```bash
# Linux/Mac
lsof -i :8081

# Mudar porta no docker-compose.yml
ports:
  - "8082:8080"  # Muda porta externa para 8082
```

### Falta de memória

OpenSearch e Airflow requerem **mínimo 4GB de RAM** no Docker.

```bash
# Docker Desktop: Settings → Resources → Memory (8GB recomendado)

# Verificar memória disponível
docker run --rm debian:bookworm-slim bash -c 'numfmt --to iec $(echo $(($(getconf _PHYS_PAGES) * $(getconf PAGE_SIZE))))'
```

### Volume corrompido

```bash
# Parar containers
docker compose down

# Remover volume específico
docker volume rm gov-contracts-ai_postgres_data

# Recriar
docker compose up -d
```

### Airflow não aceita DAGs

```bash
# Verificar permissões
ls -la ./airflow/dags

# Corrigir (Linux)
sudo chown -R 50000:0 ./airflow/dags ./airflow/logs ./airflow/plugins

# Ver logs do scheduler
docker compose logs -f airflow-scheduler
```

---

## 📚 Próximos Passos

1. **Criar primeiro DAG do Airflow**
   - Ingestão diária de licitações (PNCP API → bronze)
   - Transformação ETL (bronze → silver)
   - Feature engineering (silver → gold)

2. **Configurar MinIO connections no Airflow**
   ```bash
   docker exec -it govcontracts-airflow-webserver bash
   airflow connections add 'minio_default' \
     --conn-type 'aws' \
     --conn-login 'minioadmin' \
     --conn-password 'minioadmin' \
     --conn-extra '{"endpoint_url": "http://minio:9000"}'
   ```

3. **Indexar dados no OpenSearch**
   - Criar index para editais
   - Configurar mappings para busca semântica
   - Popular com dados de silver

4. **Treinar primeiro modelo ML**
   - Criar DAG de training (XGBoost)
   - Registrar no MLflow
   - Exportar para ONNX

---

## 🔐 Segurança (Produção)

**⚠️ Esta configuração é para DESENVOLVIMENTO!**

Para produção:
1. Trocar todas as senhas padrão
2. Habilitar TLS/SSL em todos os serviços
3. Habilitar autenticação no OpenSearch
4. Usar secrets manager (AWS Secrets Manager, Vault)
5. Configurar RBAC no Airflow
6. Habilitar audit logging
7. Usar imagens específicas (não `:latest`)

---

## 📊 Monitoramento

```bash
# Ver uso de recursos
docker stats

# Ver portas expostas
docker compose ps --format "table {{.Service}}\t{{.Ports}}"

# Healthchecks
docker inspect govcontracts-postgres | grep -A 10 Health
docker inspect govcontracts-opensearch | grep -A 10 Health
```

---

**Stack Version:** 1.0
**Data:** 22 de Outubro de 2025
**Última atualização:** Adição do Apache Airflow e OpenSearch
