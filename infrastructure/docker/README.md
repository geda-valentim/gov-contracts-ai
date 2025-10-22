# Gov Contracts AI - Data Layer Infrastructure

Docker configuration for Phase 1 Data Layer services: **MinIO**, **PostgreSQL**, and **Redis**.

## 📋 Status da Implementação

**Fase 1: Core Data Layer** ✅ **IMPLEMENTADO**

Este diretório contém toda a infraestrutura Docker para os três serviços fundamentais do Data Layer:

### ✅ O que foi criado

1. **MinIO (Object Storage)**
   - ✅ Dockerfile customizado com healthcheck
   - ✅ Script de inicialização automática de buckets (`init-buckets.sh`)
   - ✅ Configuração de versionamento (bronze/silver/gold)
   - ✅ Lifecycle policies (bucket `tmp` com auto-delete 7 dias)
   - ✅ Integração com HDD 1.81TB (`/var/storage`)

2. **PostgreSQL 16 (Data Warehouse)**
   - ✅ Dockerfile baseado em `pgvector/pgvector:0.8.1-pg16` (oficial)
   - ✅ pg_vector v0.8.1 pré-instalado (384-4000 dimensões)
   - ✅ 4 scripts de inicialização SQL:
     - `01-create-extensions.sql` - pg_vector, pg_trgm, uuid-ossp
     - `02-create-schemas.sql` - app, ml, ai, audit, analytics
     - `03-create-users.sql` - app_user, readonly_user, ml_user
     - `04-create-functions.sql` - Funções utilitárias (CNPJ, similarity)
   - ✅ Configuração otimizada para SSD (`postgresql.conf`)
   - ✅ Autenticação configurada (`pg_hba.conf`)

3. **Redis 7 (Cache & Sessions)**
   - ✅ Dockerfile com Alpine Linux
   - ✅ Configuração customizada (`redis.conf`)
   - ✅ 2GB maxmemory com LRU eviction
   - ✅ Persistência RDB habilitada

4. **Orquestração**
   - ✅ `docker-compose.yml` completo com 5 serviços:
     - MinIO (S3 API + Console)
     - MinIO Init (bucket initialization)
     - PostgreSQL 16
     - Redis 7
     - Adminer (dev profile)
     - RedisInsight (dev profile)
   - ✅ Rede isolada customizada (172.20.0.0/16)
   - ✅ IPs estáticos para cada serviço
   - ✅ Healthchecks configurados
   - ✅ Volumes persistentes

5. **Configuração**
   - ✅ `.env.example` com todas as variáveis de ambiente
   - ✅ Documentação completa (README.md)
   - ✅ Exemplos Python para cada serviço

### 🎯 Próximos Passos

Agora que a infraestrutura está pronta, os próximos passos são:

1. **Testar o ambiente**: Subir os serviços e verificar funcionamento
2. **Validar conectividade**: Testar scripts Python de exemplo
3. **Ingestão de dados**: Começar a popular MinIO e PostgreSQL
4. **Fase 2**: Adicionar ML Layer (MLflow, model serving)

### 📦 Estrutura de Arquivos

```
infrastructure/docker/
├── docker-compose.yml              # Orquestração dos 3 serviços
├── .env.example                    # Variáveis de ambiente
├── README.md                       # Esta documentação
│
├── minio/                          # MinIO S3-Compatible Storage
│   ├── Dockerfile
│   ├── init-buckets.sh            # Auto-criação de buckets
│   └── .env.example
│
├── postgres/                       # PostgreSQL 16 Data Warehouse
│   ├── Dockerfile
│   ├── postgresql.conf            # Otimizado para SSD (2GB shared_buffers)
│   ├── pg_hba.conf                # Autenticação scram-sha-256
│   ├── .env.example
│   └── init-scripts/              # Scripts SQL de inicialização
│       ├── 01-create-extensions.sql
│       ├── 02-create-schemas.sql
│       ├── 03-create-users.sql
│       └── 04-create-functions.sql
│
└── redis/                          # Redis 7 Cache
    ├── Dockerfile
    ├── redis.conf                 # 2GB maxmemory, LRU eviction
    └── .env.example
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER - PHASE 1                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │    MinIO     │    │  PostgreSQL  │    │    Redis     │    │
│  │              │    │      16      │    │      7       │    │
│  │ S3 API       │    │              │    │              │    │
│  │ Data Lake    │    │ Data         │    │ Cache        │    │
│  │              │    │ Warehouse    │    │ Sessions     │    │
│  │ Port: 9100   │    │ Port: 5433   │    │ Port: 6380   │    │
│  │ UI:   9101   │    │              │    │              │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Network: 172.30.0.0/16                                 │  │
│  │  - MinIO:      172.30.0.10                              │  │
│  │  - PostgreSQL: 172.30.0.20                              │  │
│  │  - Redis:      172.30.0.30                              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### 1. MinIO (S3-Compatible Object Storage)

**Purpose**: Data Lake for raw, processed, and ML-ready data (Medallion Architecture)

**Features**:
- S3-compatible API (boto3, s3fs, AWS SDK)
- Bucket versioning for data lineage
- Lifecycle policies for temporary data
- Web console UI (port 9001)
- Backed by HDD 1.81TB (configurável via `MINIO_DATA_DIR` em `.env`)

**Buckets**:
- `bronze/` - Raw data from APIs and scraping
- `silver/` - Cleaned and validated data
- `gold/` - Feature-engineered ML datasets
- `mlflow/` - MLflow artifacts and models
- `backups/` - Database backups
- `tmp/` - Temporary processing (7-day auto-delete)

**Access**:
- S3 API: `http://localhost:9100` (mapeado de 9000)
- Console UI: `http://localhost:9101` (mapeado de 9001)
- Default credentials: `minioadmin` / `minioadmin`

### 2. PostgreSQL 16 (Data Warehouse)

**Purpose**: Structured data storage for API queries and analytics

**Features**:
- PostgreSQL 16 with Debian (from official pgvector image)
- **pg_vector v0.8.1** pre-installed (vector similarity search)
  - Supports HNSW and IVFFlat indexes
  - Up to 4,000 dimensions (halfvec)
  - L2, cosine, inner product distances
- Extensions: `pg_trgm`, `uuid-ossp`, `pg_stat_statements`
- Custom schemas: `app`, `ml`, `ai`, `audit`, `analytics`
- Optimized for SSD storage (2GB shared_buffers)
- Portuguese full-text search support
- Multiple users: `app_user`, `readonly_user`, `ml_user`

**Access**:
- Host: `localhost:5433` (mapeado de 5432)
- Database: `govcontracts`
- User: `admin`
- Password: `dev123` (change in production!)

**Management UI** (optional):
- Adminer: `http://localhost:8080` (use `--profile dev`)

### 3. Redis 7 (Cache & Sessions)

**Purpose**: High-performance caching and session management

**Features**:
- Redis 7 with Alpine Linux
- 2GB memory limit with LRU eviction
- RDB persistence (snapshots)
- Optimized for cache use case
- Slow query logging

**Access**:
- Host: `localhost:6380` (mapeado de 6379)
- No password (development mode)

**Management UI** (optional):
- RedisInsight: `http://localhost:5540` (use `--profile dev`)

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB+ RAM available
- 50GB+ free disk space (SSD for PostgreSQL, HDD for MinIO)

### 2. Setup

```bash
# Navigate to infrastructure directory
cd infrastructure/docker

# Copy environment variables
cp .env.example .env

# Edit .env and customize values (especially passwords!)
nano .env

# IMPORTANT: Ensure MinIO data directory exists
# Default: /mnt/d/minio/data (configure in .env via MINIO_DATA_DIR)
mkdir -p /mnt/d/minio/data

# Build and start services
docker compose up -d

# View logs
docker compose logs -f

# Check service health
docker compose ps
```

### 3. Verify Installation

**MinIO**:
```bash
# Check MinIO health
curl http://localhost:9100/minio/health/live

# Access MinIO Console
# Open browser: http://localhost:9101
# Login: minioadmin / minioadmin

# Verify buckets were created
docker compose logs minio-init
```

**PostgreSQL**:
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U admin -d govcontracts

# List schemas
\dn+

# List extensions
\dx

# Check users
SELECT rolname FROM pg_roles WHERE rolname NOT LIKE 'pg_%';

# Exit psql
\q
```

**Redis**:
```bash
# Test Redis connection
docker compose exec redis redis-cli ping
# Expected output: PONG

# Check Redis info
docker compose exec redis redis-cli info server

# Monitor Redis in real-time
docker compose exec redis redis-cli monitor
```

## Usage Examples

### Python - MinIO (boto3)

```python
import boto3
from botocore.client import Config

# Create S3 client
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9100',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Upload file
s3.upload_file('data.parquet', 'bronze', 'licitacoes/2025-10-21.parquet')

# Download file
s3.download_file('bronze', 'licitacoes/2025-10-21.parquet', 'local_data.parquet')

# List objects in bucket
response = s3.list_objects_v2(Bucket='bronze', Prefix='licitacoes/')
for obj in response.get('Contents', []):
    print(f"{obj['Key']} - {obj['Size']} bytes")
```

### Python - MinIO with Pandas (s3fs)

```python
import pandas as pd
import s3fs

# Create s3fs filesystem
fs = s3fs.S3FileSystem(
    key='minioadmin',
    secret='minioadmin',
    client_kwargs={'endpoint_url': 'http://localhost:9100'}
)

# Read Parquet from S3
df = pd.read_parquet(
    's3://bronze/licitacoes/year=2025/month=10/day=21/data.parquet',
    filesystem=fs
)

# Write Parquet to S3
df.to_parquet(
    's3://silver/licitacoes_clean/2025-10-21.parquet',
    filesystem=fs,
    compression='snappy'
)

# Read CSV from S3
df_csv = pd.read_csv('s3://bronze/precos_mercado/sinapi_2025.csv', storage_options={
    'key': 'minioadmin',
    'secret': 'minioadmin',
    'client_kwargs': {'endpoint_url': 'http://localhost:9100'}
})
```

### Python - PostgreSQL (psycopg2)

```python
import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to PostgreSQL
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='govcontracts',
    user='admin',
    password='dev123'
)

# Query with dictionary cursor
with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("SELECT * FROM app.licitacoes LIMIT 10")
    rows = cur.fetchall()
    for row in rows:
        print(row['numero_licitacao'], row['orgao'])

# Insert data
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO app.licitacoes (numero_licitacao, orgao, valor_estimado)
        VALUES (%s, %s, %s)
    """, ('2025/001', 'MEC', 100000.00))
    conn.commit()

conn.close()
```

### Python - PostgreSQL with SQLAlchemy

```python
from sqlalchemy import create_engine, text
import pandas as pd

# Create engine
engine = create_engine(
    'postgresql://admin:dev123@localhost:5433/govcontracts'
)

# Query to DataFrame
df = pd.read_sql("SELECT * FROM app.licitacoes LIMIT 100", engine)

# Write DataFrame to PostgreSQL
df.to_sql('licitacoes_staging', engine, schema='app', if_exists='replace', index=False)

# Execute raw SQL
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM app.licitacoes"))
    count = result.scalar()
    print(f"Total licitacoes: {count}")
```

### Python - Redis (redis-py)

```python
import redis
import json

# Connect to Redis
r = redis.Redis(host='localhost', port=6380, db=0, decode_responses=True)

# Set key with TTL (24 hours)
r.setex('prediction:123', 86400, json.dumps({
    'licitacao_id': '123',
    'fraud_score': 0.85,
    'model_version': 'v1.2.3'
}))

# Get key
cached = r.get('prediction:123')
if cached:
    prediction = json.loads(cached)
    print(f"Fraud score: {prediction['fraud_score']}")

# Check if key exists
exists = r.exists('prediction:123')

# Delete key
r.delete('prediction:123')

# Hash operations
r.hset('user:456', mapping={
    'name': 'João Silva',
    'role': 'analyst',
    'last_login': '2025-10-21'
})
user = r.hgetall('user:456')
```

## Docker Compose Commands

```bash
# Start all services
docker compose up -d

# Start with development tools (Adminer + RedisInsight)
docker compose --profile dev up -d

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: data loss!)
docker compose down -v

# Restart a specific service
docker compose restart postgres

# View logs
docker compose logs -f
docker compose logs -f postgres
docker compose logs -f minio

# Execute command in container
docker compose exec postgres psql -U admin -d govcontracts
docker compose exec redis redis-cli
docker compose exec minio mc alias list

# Rebuild and restart service
docker compose up -d --build postgres

# Check service health
docker compose ps
```

## Backup and Restore

### PostgreSQL Backup

```bash
# Backup database
docker compose exec postgres pg_dump -U admin -d govcontracts -F c -f /tmp/backup.dump

# Copy backup to host
docker compose cp postgres:/tmp/backup.dump ./backups/govcontracts_$(date +%Y%m%d).dump

# Backup to MinIO S3
docker compose exec postgres pg_dump -U admin -d govcontracts | \
  docker compose exec -T minio mc pipe local/backups/postgres_$(date +%Y%m%d).sql
```

### PostgreSQL Restore

```bash
# Restore from dump file
docker compose exec postgres pg_restore -U admin -d govcontracts -c /tmp/backup.dump
```

### MinIO Backup

MinIO data is backed by persistent volume. To backup:

```bash
# Option 1: Copy entire data directory (adjust path based on MINIO_DATA_DIR)
cp -r /mnt/d/minio/data /backups/minio_$(date +%Y%m%d)

# Option 2: Use mc mirror
docker compose run --rm minio-init mc mirror local/bronze /backups/bronze
```

## Monitoring

### View Resource Usage

```bash
# Docker stats
docker stats

# PostgreSQL connections
docker compose exec postgres psql -U admin -d govcontracts -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Redis info
docker compose exec redis redis-cli info stats

# MinIO metrics (Prometheus format)
curl http://localhost:9100/minio/v2/metrics/cluster
```

## Troubleshooting

### PostgreSQL won't start

```bash
# Check logs
docker compose logs postgres

# Verify permissions on data directory
docker compose exec postgres ls -la /var/lib/postgresql/data

# Reset database (WARNING: data loss!)
docker compose down -v
docker compose up -d postgres
```

### MinIO buckets not created

```bash
# Re-run init script
docker compose up minio-init

# Manual bucket creation
docker compose exec minio mc alias set local http://localhost:9100 minioadmin minioadmin
docker compose exec minio mc mb local/bronze
docker compose exec minio mc version enable local/bronze
```

### Redis memory issues

```bash
# Check memory usage
docker compose exec redis redis-cli info memory

# Clear all keys (WARNING: data loss!)
docker compose exec redis redis-cli FLUSHALL

# Increase maxmemory in redis.conf and restart
docker compose restart redis
```

### Network connectivity issues

```bash
# Inspect network
docker network inspect gov-contracts-ai_gov-contracts-network

# Test connectivity between services
docker compose exec postgres ping -c 3 minio
docker compose exec redis ping -c 3 postgres
```

## Security Considerations

**IMPORTANT**: This configuration is for **DEVELOPMENT ONLY**.

For production:

1. **Change all default passwords** in `.env`
2. **Enable TLS/SSL** for all services
3. **Restrict network access** (remove 0.0.0.0 bindings)
4. **Enable authentication** for Redis
5. **Use secrets management** (AWS Secrets Manager, Vault)
6. **Configure firewall rules** (only allow necessary ports)
7. **Enable audit logging** for PostgreSQL and MinIO
8. **Implement backup strategy** with encryption
9. **Use read-only filesystems** where possible
10. **Scan images for vulnerabilities** (Trivy, Clair)

## Next Steps

After the Data Layer is operational:

1. **Test data pipeline**: Ingest sample data to MinIO → Load to PostgreSQL
2. **Verify connectivity**: Ensure backend app can connect to all services
3. **Configure monitoring**: Set up Prometheus + Grafana for metrics
4. **Implement backups**: Automate daily backups to S3/MinIO
5. **Phase 2**: Deploy ML services (MLflow, model serving)

## Resources

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Redis 7 Documentation](https://redis.io/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## License

This infrastructure configuration is part of the Gov Contracts AI project.

---

**Gov Contracts AI** - Phase 1: Data Layer
Built with ❤️ for transparency in Brazilian government procurement
