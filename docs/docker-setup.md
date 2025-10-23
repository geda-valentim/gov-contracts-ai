# Docker Setup - Gov Contracts AI

**Versão:** 1.0
**Data:** 22 de Outubro de 2025

---

## 🐳 Arquivos Docker-Compose

O projeto tem **dois** arquivos docker-compose:

### 1. `/infrastructure/docker/docker-compose.yml` ✅ **RECOMENDADO**

**Localização:** `infrastructure/docker/`

**Serviços:**
- PostgreSQL 16 (pgvector)
- MinIO (S3-compatible)
- Redis 7

**Uso:**
```bash
cd infrastructure/docker
docker compose up -d
```

**Características:**
- ✅ Configuração madura e testada
- ✅ Scripts de inicialização PostgreSQL
- ✅ MinIO com auto-criação de buckets
- ✅ Healthchecks configurados
- ✅ Rede: `172.30.0.0/16`

---

###  2. `/docker-compose.yml` (Raiz) ⚠️ **EM DESENVOLVIMENTO**

**Localização:** Raiz do projeto

**Serviços:**
- Todos os de `infrastructure/docker/` +
- Airflow (webserver, scheduler, worker, triggerer)
- MLflow
- OpenSearch + Dashboards

**Status:** 🚧 Em desenvolvimento

**Problemas conhecidos:**
- MinIO healthcheck falhando
- Conflito de rede se ambos stacks rodarem simultaneamente

**Uso futuro:**
```bash
# Quando estabilizado
docker compose up -d
```

---

## 🚀 Setup Recomendado (Fase Atual)

### Passo 1: Limpar Ambiente

```bash
# Parar todos os containers
docker stop $(docker ps -aq)

# Remover containers órfãos
docker container prune -f

# Limpar redes não utilizadas
docker network prune -f

# (OPCIONAL) Remover volumes para fresh start
docker volume prune -f
```

### Passo 2: Subir Serviços Base

```bash
cd /home/gov-contracts-ai/infrastructure/docker

# Subir PostgreSQL, MinIO e Redis
docker compose up -d

# Aguardar todos ficarem healthy
docker compose ps

# Verificar logs
docker compose logs -f
```

### Passo 3: Verificar Serviços

```bash
# PostgreSQL
docker compose exec postgres psql -U admin -d govcontracts -c "\l"
docker compose exec postgres psql -U admin -d airflow -c "\l"

# MinIO
curl http://localhost:9000/minio/health/live

# Redis
docker compose exec redis redis-cli ping
```

---

## 🔧 Troubleshooting

### Erro: "Pool overlaps with other one on this address space"

**Problema:** Dois docker-compose usando mesma subnet `172.30.0.0/16`

**Solução:**
```bash
# 1. Parar todos os stacks
docker compose down  # na raiz
cd infrastructure/docker && docker compose down

# 2. Remover containers órfãos
docker ps -a | grep govcontracts | awk '{print $1}' | xargs -r docker rm -f

# 3. Limpar redes
docker network prune -f

# 4. Subir apenas um stack
cd infrastructure/docker
docker compose up -d
```

### Erro: "directory /var/lib/postgresql/data exists but is not empty"

**Problema:** Volume PostgreSQL com dados antigos incompatíveis

**Solução:**
```bash
# Remover volume e recriar
docker compose down -v
docker compose up -d
```

### MinIO Unhealthy

**Problema:** Healthcheck falhando

**Verificação:**
```bash
# Ver logs
docker logs minio --tail=50

# Testar manualmente
curl http://localhost:9000/minio/health/live
```

**Solução temporária:**
```bash
# Aguardar mais tempo
sleep 60 && docker compose ps

# Se persistir, reiniciar
docker compose restart minio
```

### Banco "airflow" não existe

**Status:** ✅ **RESOLVIDO**

**Solução aplicada:**
- Criado script `infrastructure/docker/postgres/init-scripts/00-create-airflow-db.sql`
- Script cria automaticamente banco `airflow` na inicialização

**Verificação:**
```bash
docker compose exec postgres psql -U admin -l | grep airflow
```

---

## 📊 Portas dos Serviços

### Infrastructure Stack (Recomendado)

| Serviço | Porta Externa | Porta Interna | Descrição |
|---------|---------------|---------------|-----------|
| **PostgreSQL** | 5433 | 5432 | Database |
| **Redis** | 6380 | 6379 | Cache |
| **MinIO API** | 9000 | 9000 | S3 API |
| **MinIO Console** | 9001 | 9001 | Web UI |

### Full Stack (Futuro)

Adiciona:

| Serviço | Porta Externa | Porta Interna | Descrição |
|---------|---------------|---------------|-----------|
| **MLflow** | 5000 | 5000 | Tracking |
| **Airflow UI** | 8081 | 8080 | Webserver |
| **OpenSearch** | 9201 | 9200 | Search Engine |
| **OpenSearch Dashboards** | 5602 | 5601 | Kibana-like UI |

---

## 🎯 Roadmap

### Fase 1: Data Layer ✅ (Atual)
- [x] PostgreSQL com pgvector
- [x] MinIO para Data Lake
- [x] Redis para cache
- [x] Scripts de inicialização
- [x] Banco `airflow` criado automaticamente

### Fase 2: Orchestration (Próxima)
- [ ] Migrar Airflow para stack principal
- [ ] Validar healthchecks
- [ ] Testes de conectividade
- [ ] Documentar DAGs

### Fase 3: ML/AI Layer
- [ ] MLflow funcionando
- [ ] Integração com MinIO
- [ ] Model registry

### Fase 4: Observability
- [ ] OpenSearch para logs
- [ ] Dashboards configurados
- [ ] Alertas

---

## 📝 Convenções

### Network

**Subnet:** `172.30.0.0/16`

**IPs estáticos:**
- PostgreSQL: `172.30.0.5`
- Redis: `172.30.0.6`
- MLflow: `172.30.0.7`
- MinIO: `172.30.0.10`
- OpenSearch: `172.30.0.11`
- OpenSearch Dashboards: `172.30.0.12`
- Airflow Webserver: `172.30.0.20`
- Airflow Scheduler: `172.30.0.21`
- Airflow Worker: `172.30.0.22`
- Airflow Triggerer: `172.30.0.23`

### Volumes

**Nomeação:** `gov-contracts-ai_<service>_data`

**Volumes criados:**
- `postgres_data` - Dados PostgreSQL
- `redis_data` - Persistência Redis
- `minio_data` - Object storage
- `mlflow_data` - MLflow artifacts
- `opensearch_data` - Índices OpenSearch

### Containers

**Nomeação:** `govcontracts-<service>`

**Containers:**
- `govcontracts-postgres`
- `govcontracts-redis`
- `govcontracts-minio`
- `govcontracts-minio-init` (one-time)
- `govcontracts-mlflow`
- `govcontracts-opensearch`
- `govcontracts-opensearch-dashboards`
- `govcontracts-airflow-webserver`
- `govcontracts-airflow-scheduler`
- `govcontracts-airflow-worker`
- `govcontracts-airflow-triggerer`
- `govcontracts-airflow-init` (one-time)

---

## 🔒 Segurança

### Credenciais Padrão (DEV ONLY)

**PostgreSQL:**
- User: `admin`
- Password: `dev123`
- Databases: `govcontracts`, `airflow`, `mlflow`

**MinIO:**
- User: `minioadmin`
- Password: `minioadmin`

**Airflow UI:**
- User: `airflow`
- Password: `airflow`

**⚠️ IMPORTANTE:** Mudar todas as credenciais em produção!

---

## 🔗 Links Úteis

### Documentação Oficial

- [Docker Compose](https://docs.docker.com/compose/)
- [PostgreSQL 16](https://www.postgresql.org/docs/16/)
- [MinIO](https://min.io/docs/minio/linux/index.html)
- [Redis 7](https://redis.io/docs/)
- [Apache Airflow](https://airflow.apache.org/docs/)

### Troubleshooting

- [Docker Network Issues](https://docs.docker.com/network/troubleshooting/)
- [PostgreSQL Init Scripts](https://hub.docker.com/_/postgres)
- [MinIO Healthcheck](https://min.io/docs/minio/linux/operations/monitoring.html)

---

## 📞 Suporte

### Logs

```bash
# Todos os serviços
docker compose logs -f

# Serviço específico
docker compose logs -f postgres

# Últimas 100 linhas
docker compose logs --tail=100 minio
```

### Restart

```bash
# Serviço específico
docker compose restart postgres

# Todos os serviços
docker compose restart

# Hard restart (down + up)
docker compose down && docker compose up -d
```

### Reset Completo

```bash
# ⚠️ ATENÇÃO: Apaga todos os dados!
docker compose down -v
docker compose up -d
```

---

*Última atualização: 22/10/2025*
*Mantido por: Equipe de Desenvolvimento*
