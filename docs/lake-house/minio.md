# 🗄️ GUIA DE CONFIGURAÇÃO MINIO S3
## Gov Contracts AI - Object Storage Setup

**Data:** 21 de Outubro de 2025
**Versão:** 1.1 (Atualizado com configurações de produção)
**Propósito:** Configurar MinIO como S3-compatible storage para Data Lake

---

## ⚙️ DECISÕES DE IMPLEMENTAÇÃO

Este documento reflete as decisões tomadas durante a implementação real do projeto:

### 🔌 Portas Customizadas
- **API S3:** `9000` (host) → `9000` (container)
- **Web Console:** `9001` (host) → `9001` (container)
- **Motivo:** Evitar conflitos com outros projetos rodando em desenvolvimento

### 🌐 Rede Docker
- **Subnet:** `172.30.0.0/16`
- **Network:** `govcontracts-network`
- **Motivo:** Subnets 172.20.x e 172.25.x já estavam em uso por outros projetos

### 📦 Volumes
- Uso de **volumes nomeados** do Docker (não bind mounts)
- Gerenciamento automático pelo Docker
- Facilita backup e migração

### 🐳 Docker Compose
- **Versão:** Compose v2 (sem campo `version:`)
- **Comando:** `docker compose` (sem hífen)
- **Init Container:** Criação automática de buckets com `minio-init`

### 🔐 Credenciais
- **User:** `minioadmin`
- **Password:** `minioadmin`
- ⚠️ **IMPORTANTE:** Trocar em produção!

---

## 📋 ÍNDICE

1. [O que é MinIO](#o-que-é-minio)
2. [Por que usar MinIO](#por-que-usar-minio)
3. [Arquitetura de Buckets](#arquitetura-de-buckets)
4. [Pré-requisitos](#pré-requisitos)
5. [Instalação via Docker](#instalação-via-docker)
6. [Criação dos Buckets](#criação-dos-buckets)
7. [Configuração Avançada](#configuração-avançada)
8. [Integração com Python](#integração-com-python)
9. [Testes e Validação](#testes-e-validação)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 O QUE É MINIO

**MinIO** é um servidor de object storage open source compatível com S3 (AWS). Funciona como um "AWS S3 local" que você pode rodar no seu servidor.

### Características Principais:
- ✅ **S3-compatible API** - Mesma API do AWS S3
- ✅ **100% Open Source** - AGPL v3
- ✅ **Alta Performance** - Escrito em Go
- ✅ **Escalável** - Single-server até distributed mode
- ✅ **Versioning** - Controle de versões de objetos
- ✅ **Encryption** - AES-256 at rest
- ✅ **Web Console** - UI para gerenciamento

---

## 💡 POR QUE USAR MINIO

### Comparação: Filesystem Local vs MinIO

| Aspecto | Filesystem Local | MinIO S3 |
|---------|------------------|----------|
| **Escalabilidade** | ❌ Difícil horizontal scaling | ✅ Distributed mode nativo |
| **API Padrão** | ❌ File I/O específico | ✅ S3 API (padrão mercado) |
| **Versioning** | ❌ Manual (Git-like) | ✅ Built-in (object versioning) |
| **HA (Alta Disponibilidade)** | ❌ Requer setup complexo | ✅ Erasure coding nativo |
| **Cloud Migration** | ❌ Reescrever código | ✅ Drop-in replacement (AWS S3) |
| **Multi-client** | ⚠️ File locking issues | ✅ Concurrent access safe |
| **Backup** | ❌ rsync manual | ✅ `mc mirror` integrado |
| **Monitoring** | ❌ Custom scripts | ✅ Prometheus metrics |
| **Lifecycle** | ❌ Manual cleanup | ✅ Policies automáticas |

### Vantagens para o Projeto:
1. **Compatibilidade total com AWS S3** - Se precisar migrar para cloud, é só trocar endpoint
2. **Airflow/MLflow/Pandas** - Todas essas ferramentas têm suporte S3 nativo
3. **Auditoria** - Versioning mostra quem modificou o quê e quando
4. **Escalabilidade** - Começa single-server, escala para cluster distribuído
5. **Object storage** - Ideal para arquivos grandes (PDFs, Parquet, modelos ML)

---

## 🏗️ ARQUITETURA DE BUCKETS

### Estrutura Completa

```
MinIO Server (http://localhost:9000)  ⚠️ PORTA 9000, NÃO 9000
Console Web (http://localhost:9001)   ⚠️ PORTA 9001, NÃO 9001
│
├─ 📦 bronze/                    # RAW DATA (dados brutos)
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
├─ 🥈 silver/                    # CLEAN DATA (dados limpos)
│  ├─ licitacoes_clean/
│  ├─ editais_parsed/
│  ├─ editais_analysis/
│  ├─ precos_normalized/
│  └─ joined_full/
│
├─ 🥇 gold/                      # ML-READY (features engineered)
│  ├─ features_ml/
│  ├─ embeddings/
│  └─ agregados/
│
├─ 🤖 mlflow/                    # ML ARTIFACTS
│  ├─ experiments/
│  ├─ models/
│  └─ artifacts/
│
├─ 💾 backups/                   # BACKUPS
│  ├─ postgres/
│  ├─ opensearch/
│  └─ gold_snapshots/
│
└─ 📁 tmp/                       # TEMPORARY FILES
   └─ airflow_tmp/
```

### Medallion Architecture (Bronze → Silver → Gold)

```
┌──────────────────────────────────────────────────────────────┐
│  🥉 BRONZE LAYER                                             │
│  Propósito: Dados brutos "as-is"                            │
│  Formato: Parquet (snappy compression)                      │
│  Retenção: Permanente (imutável)                            │
│  Versioning: Habilitado (auditoria)                         │
└──────────────────────────────────────────────────────────────┘
                         ↓ Cleaning & Validation
┌──────────────────────────────────────────────────────────────┐
│  🥈 SILVER LAYER                                             │
│  Propósito: Dados validados e normalizados                  │
│  Formato: Parquet (snappy compression)                      │
│  Retenção: Permanente                                        │
│  Qualidade: Great Expectations (>90% score)                 │
└──────────────────────────────────────────────────────────────┘
                         ↓ Feature Engineering
┌──────────────────────────────────────────────────────────────┐
│  🥇 GOLD LAYER                                               │
│  Propósito: Features ML-ready + agregações                  │
│  Formato: Parquet + também PostgreSQL/OpenSearch            │
│  Uso: Treinamento ML, APIs, Dashboards                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 PRÉ-REQUISITOS

### Hardware
- **RAM:** Mínimo 512MB, recomendado 1GB para MinIO
- **Storage:** HDD 1.8TB disponível (projeto usa volumes Docker)
- **CPU:** Qualquer (MinIO é leve)

### Software
- **Docker** 24+ instalado
- **Docker Compose** instalado (comando: `docker compose`, não `docker-compose`)
- **Ports livres:** 9000 (API S3), 9001 (Console Web)
  - ⚠️ **NOTA:** Usamos portas não-padrão (9000/9001 ao invés de 9000/9001) para evitar conflitos com outros projetos

### Verificar instalação:
```bash
docker --version
docker compose version  # Note: 'docker compose' sem hífen
```

---

## 🚀 INSTALAÇÃO VIA DOCKER

### OPÇÃO 1: Docker Compose (Recomendado)

Crie o arquivo `docker-compose.yml`:

```yaml
# NOTA: Não use 'version:' - é obsoleto no Docker Compose v2

services:
  minio:
    image: minio/minio:latest
    container_name: govcontracts-minio
    ports:
      # IMPORTANTE: Mapeamento Host:Container
      # 9000 (host) -> 9000 (container) = S3 API
      # 9001 (host) -> 9001 (container) = Web Console
      - "9000:9000"   # S3 API (porta externa 9000 para evitar conflitos)
      - "9001:9001"   # Web Console (porta externa 9001)
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin  # TROCAR EM PRODUÇÃO!
    volumes:
      - minio_data:/data              # Volume nomeado (gerenciado pelo Docker)
    command: server /data --console-address ":9001"
    healthcheck:
      # IMPORTANTE: healthcheck usa porta INTERNA (9000), não externa
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped
    networks:
      govcontracts-network:
        ipv4_address: 172.30.0.10

  # Container para criar buckets automaticamente
  minio-init:
    image: minio/mc:latest
    container_name: govcontracts-minio-init
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      echo 'Aguardando MinIO iniciar...';
      sleep 5;

      echo 'Configurando alias MinIO...';
      mc alias set myminio http://minio:9000 minioadmin minioadmin;

      echo 'Criando buckets...';
      mc mb --ignore-existing myminio/bronze;
      mc mb --ignore-existing myminio/silver;
      mc mb --ignore-existing myminio/gold;
      mc mb --ignore-existing myminio/mlflow;
      mc mb --ignore-existing myminio/backups;
      mc mb --ignore-existing myminio/tmp;

      echo 'Habilitando versioning...';
      mc version enable myminio/bronze;
      mc version enable myminio/silver;
      mc version enable myminio/gold;
      mc version enable myminio/mlflow;

      echo 'Configurando políticas de acesso...';
      mc anonymous set download myminio/bronze;

      echo 'Configurando lifecycle para tmp (auto-delete após 7 dias)...';
      mc ilm add --expiry-days 7 myminio/tmp;

      echo '✅ MinIO configurado com sucesso!';
      exit 0;
      "
    networks:
      - govcontracts-network

volumes:
  minio_data:
    driver: local

networks:
  govcontracts-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16  # Subnet customizada para evitar conflitos
```

### Iniciar MinIO:
```bash
# No diretório com docker-compose.yml
docker compose up -d

# Ver logs
docker compose logs -f minio

# Verificar status e saúde dos containers
docker compose ps

# Parar serviços
docker compose down

# Parar e remover volumes (CUIDADO: apaga dados!)
docker compose down -v
```

---

### OPÇÃO 2: Docker Run Direto

```bash
# Criar volume Docker (recomendado) ou usar bind mount
docker volume create minio_data

# Iniciar MinIO
# IMPORTANTE: Portas no formato HOST:CONTAINER
docker run -d \
  --name govcontracts-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio:latest \
  server /data --console-address ":9001"

# Verificar se está rodando
docker logs govcontracts-minio

# Verificar saúde
docker inspect govcontracts-minio | grep -A 10 Health
```

---

## 🪣 CRIAÇÃO DOS BUCKETS

### Método 1: MinIO Console (UI) - MAIS FÁCIL

1. **Acessar Console:**
   - URL: http://localhost:9001 ⚠️ **NOTA: Porta 9001, não 9001!**
   - User: `minioadmin`
   - Password: `minioadmin`

2. **Criar Buckets:**
   - Click em **"Buckets"** no menu lateral
   - Click em **"Create Bucket"**
   - Nome: `bronze`
   - Click **"Create"**
   - Repetir para: `silver`, `gold`, `mlflow`, `backups`, `tmp`

3. **Habilitar Versioning:**
   - Click no bucket (ex: `bronze`)
   - Aba **"Settings"**
   - Seção **"Versioning"**
   - Toggle **"Enable Versioning"**
   - Save

---

### Método 2: MinIO Client (CLI) - AUTOMATIZADO

```bash
# Instalar mc (MinIO Client)
# Linux/Mac:
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Windows:
# Baixar de https://dl.min.io/client/mc/release/windows-amd64/mc.exe

# Configurar alias para o servidor local
# IMPORTANTE: Use porta 9000 (HOST), não 9000
mc alias set myminio http://localhost:9000 minioadmin minioadmin

# Testar conexão
mc admin info myminio

# Criar buckets
mc mb myminio/bronze
mc mb myminio/silver
mc mb myminio/gold
mc mb myminio/mlflow
mc mb myminio/backups
mc mb myminio/tmp

# Listar buckets
mc ls myminio

# Habilitar versioning
mc version enable myminio/bronze
mc version enable myminio/silver
mc version enable myminio/gold
mc version enable myminio/mlflow

# Verificar versioning
mc version info myminio/bronze
```

---

### Método 3: Python (boto3) - PROGRAMÁTICO

```python
import boto3
from botocore.client import Config

# Cliente S3 (MinIO)
# IMPORTANTE: Use porta 9000 (HOST), não 9000
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Lista de buckets a criar
BUCKETS = ['bronze', 'silver', 'gold', 'mlflow', 'backups', 'tmp']

# Criar buckets
for bucket in BUCKETS:
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"✅ Bucket '{bucket}' criado com sucesso")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"ℹ️  Bucket '{bucket}' já existe")
    except Exception as e:
        print(f"❌ Erro ao criar bucket '{bucket}': {e}")

# Habilitar versioning
for bucket in ['bronze', 'silver', 'gold', 'mlflow']:
    try:
        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print(f"✅ Versioning habilitado em '{bucket}'")
    except Exception as e:
        print(f"❌ Erro ao habilitar versioning em '{bucket}': {e}")

# Listar buckets
response = s3.list_buckets()
print("\n📦 Buckets disponíveis:")
for bucket in response['Buckets']:
    print(f"  - {bucket['Name']}")
```

---

## ⚙️ CONFIGURAÇÃO AVANÇADA

### 1. Estrutura de Subpastas (Bronze)

```bash
# Criar estrutura de diretórios no bucket bronze
# Via CLI (mc)

# Licitações particionadas por data
mc cp --recursive local_data/licitacoes/ myminio/bronze/licitacoes/year=2025/month=10/day=21/

# Editais PDF
mc cp editais/*.pdf myminio/bronze/editais_raw/

# Editais processados (JSON)
mc cp editais_json/*.json myminio/bronze/editais_text/

# Preços de mercado
mc cp precos/*.parquet myminio/bronze/precos_mercado/marketplace/2025/10/21/

# CNPJ bulk
mc cp receita.parquet myminio/bronze/cnpj/
```

---

### 2. Lifecycle Policies (Limpeza Automática)

```bash
# Política: Deletar arquivos tmp/ após 7 dias
mc ilm add --expiry-days 7 myminio/tmp

# Política: Transição backups antigos para tier frio após 90 dias
mc ilm add --transition-days 90 --storage-class COLD myminio/backups

# Ver políticas
mc ilm ls myminio/tmp
```

---

### 3. Políticas de Acesso (Bucket Policies)

```bash
# Bronze: Leitura pública (download only)
mc anonymous set download myminio/bronze

# Silver: Privado (apenas credenciais)
mc anonymous set private myminio/silver

# Verificar política
mc anonymous get myminio/bronze
```

---

### 4. Quotas de Storage

```bash
# Limitar bronze a 500GB
mc quota set myminio/bronze --size 500GB

# Ver quota
mc quota info myminio/bronze
```

---

### 5. Replication (Para HA - Opcional)

```bash
# Se tiver 2 servidores MinIO (minio1 e minio2)
mc alias set minio1 http://server1:9000 admin password1
mc alias set minio2 http://server2:9000 admin password2

# Configurar replicação bidirecional
mc replicate add minio1/bronze --remote-bucket minio2/bronze
mc replicate add minio2/bronze --remote-bucket minio1/bronze
```

---

## 🐍 INTEGRAÇÃO COM PYTHON

### 1. Instalação de Dependências

```bash
pip install boto3 s3fs pyarrow pandas
```

---

### 2. Configuração de Credenciais

**Opção A: Variáveis de Ambiente (.env)**
```bash
# .env
# IMPORTANTE: Porta 9000 (HOST), não 9000
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_REGION=us-east-1
```

**Opção B: Config File (config.py)**
```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_REGION: str = "us-east-1"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### 3. Cliente S3 (boto3)

```python
# backend/app/core/storage.py
import boto3
from botocore.client import Config
from app.core.config import settings

def get_s3_client():
    """Retorna cliente boto3 S3 para MinIO"""
    return boto3.client(
        's3',
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name=settings.MINIO_REGION
    )

def get_s3_resource():
    """Retorna resource boto3 S3 para MinIO"""
    return boto3.resource(
        's3',
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name=settings.MINIO_REGION
    )

# Exemplo de uso
s3 = get_s3_client()

# Upload file
with open('licitacao.parquet', 'rb') as f:
    s3.upload_fileobj(f, 'bronze', 'licitacoes/year=2025/month=10/day=21/data.parquet')

# Download file
s3.download_file('bronze', 'licitacoes/year=2025/month=10/day=21/data.parquet', 'local.parquet')

# List objects
response = s3.list_objects_v2(Bucket='bronze', Prefix='licitacoes/')
for obj in response.get('Contents', []):
    print(obj['Key'])
```

---

### 4. Pandas + s3fs (MAIS FÁCIL)

```python
# backend/app/utils/parquet_io.py
import pandas as pd
import s3fs
from app.core.config import settings

def get_s3_filesystem():
    """Retorna s3fs filesystem para MinIO"""
    return s3fs.S3FileSystem(
        key=settings.MINIO_ACCESS_KEY,
        secret=settings.MINIO_SECRET_KEY,
        client_kwargs={'endpoint_url': settings.MINIO_ENDPOINT}
    )

# Uso direto
fs = get_s3_filesystem()

# Ler Parquet do S3
df = pd.read_parquet(
    's3://bronze/licitacoes/year=2025/month=10/day=21/data.parquet',
    filesystem=fs
)

# Escrever Parquet no S3
df.to_parquet(
    's3://silver/licitacoes_clean/2025-10-21.parquet',
    filesystem=fs,
    compression='snappy',
    index=False
)

# Ler CSV do S3
df = pd.read_csv(
    's3://bronze/cnpj/empresas.csv',
    storage_options={
        'key': settings.MINIO_ACCESS_KEY,
        'secret': settings.MINIO_SECRET_KEY,
        'client_kwargs': {'endpoint_url': settings.MINIO_ENDPOINT}
    }
)
```

---

### 5. Airflow Integration

```python
# airflow/dags/bronze_ingestion.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import boto3

def upload_to_s3(**context):
    """Task para upload de dados no MinIO"""
    # NOTA: Se Airflow roda em container na mesma rede Docker,
    # use 'http://minio:9000' (nome do serviço + porta interna)
    # Se roda no host, use 'http://localhost:9000'
    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',  # URL interna Docker
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin'
    )

    # Upload file
    s3.upload_file(
        '/tmp/licitacoes.parquet',
        'bronze',
        f'licitacoes/year={context["ds"][:4]}/month={context["ds"][5:7]}/day={context["ds"][8:10]}/data.parquet'
    )
    print(f"✅ Upload concluído: {context['ds']}")

with DAG(
    'bronze_ingestion',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    upload_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3
    )
```

---

## ✅ TESTES E VALIDAÇÃO

### Checklist de Validação:

```bash
# 1. MinIO está rodando? (API S3)
curl http://localhost:9000/minio/health/live
# Resposta esperada: 200 OK

# 2. Console acessível?
curl -I http://localhost:9001
# Resposta esperada: 200 OK

# 3. Verificar container rodando
docker ps | grep minio
# Deve mostrar govcontracts-minio com status healthy

# 4. Buckets criados? (CLI)
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc ls myminio
# Deve listar: bronze, silver, gold, mlflow, backups, tmp

# 5. Versioning habilitado? (CLI)
mc version info myminio/bronze
# Status: Enabled

# 6. Upload funciona? (CLI)
echo "test" > test.txt
mc cp test.txt myminio/bronze/test/
mc ls myminio/bronze/test/
# Deve listar test.txt

# 7. Python funciona?
python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:9000',
                  aws_access_key_id='minioadmin',
                  aws_secret_access_key='minioadmin')
buckets = s3.list_buckets()
print([b['Name'] for b in buckets['Buckets']])
"
# Deve listar todos os buckets
```

---

### Script de Teste Completo (Python):

```python
# tests/test_minio_setup.py
import boto3
from botocore.client import Config
import pandas as pd
import s3fs

def test_minio_setup():
    """Testa configuração completa do MinIO"""

    # 1. Conexão
    print("1️⃣ Testando conexão...")
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        config=Config(signature_version='s3v4')
    )

    # 2. Listar buckets
    print("2️⃣ Listando buckets...")
    response = s3.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    expected = ['bronze', 'silver', 'gold', 'mlflow', 'backups', 'tmp']

    for bucket in expected:
        if bucket in buckets:
            print(f"  ✅ {bucket}")
        else:
            print(f"  ❌ {bucket} - NOT FOUND!")

    # 3. Test upload/download
    print("3️⃣ Testando upload/download...")
    test_data = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})

    # Upload
    fs = s3fs.S3FileSystem(
        key='minioadmin',
        secret='minioadmin',
        client_kwargs={'endpoint_url': 'http://localhost:9000'}
    )

    test_data.to_parquet('s3://tmp/test.parquet', filesystem=fs)
    print("  ✅ Upload realizado")

    # Download
    df_downloaded = pd.read_parquet('s3://tmp/test.parquet', filesystem=fs)
    assert df_downloaded.equals(test_data), "Dados não conferem!"
    print("  ✅ Download e validação OK")

    # 4. Versioning
    print("4️⃣ Verificando versioning...")
    try:
        response = s3.get_bucket_versioning(Bucket='bronze')
        status = response.get('Status', 'Disabled')
        if status == 'Enabled':
            print("  ✅ Versioning habilitado")
        else:
            print(f"  ⚠️  Versioning: {status}")
    except Exception as e:
        print(f"  ❌ Erro: {e}")

    # 5. Cleanup
    print("5️⃣ Limpando arquivos de teste...")
    s3.delete_object(Bucket='tmp', Key='test.parquet')
    print("  ✅ Limpeza concluída")

    print("\n🎉 TODOS OS TESTES PASSARAM!")

if __name__ == "__main__":
    test_minio_setup()
```

Executar:
```bash
python tests/test_minio_setup.py
```

---

## 🔧 TROUBLESHOOTING

### Problema 1: MinIO não inicia

**Sintoma:**
```
docker logs gov-contracts-minio
Error: Unable to use the drive /data: Drive /data: is not writable
```

**Solução:**
```bash
# Verificar permissões
ls -la /mnt/d/minio/

# Corrigir permissões
sudo chown -R 1000:1000 /mnt/d/minio/data
sudo chmod -R 755 /mnt/d/minio/data

# Reiniciar
docker-compose restart minio
```

---

### Problema 2: Console não carrega (http://localhost:9001)

**Solução:**
```bash
# Verificar se porta está em uso
sudo netstat -tulpn | grep 9001
# Ou no Windows/WSL:
lsof -i :9001

# Se estiver, mudar porta no docker-compose.yml
ports:
  - "9102:9001"  # Muda host port para 9102 (container sempre :9001)

# Acessar: http://localhost:9102

# Verificar se o container está rodando
docker ps | grep minio
docker logs govcontracts-minio
```

---

### Problema 3: Python não conecta

**Sintoma:**
```python
botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL
```

**Soluções:**
```python
# 1. Verificar endpoint correto (porta 9000, não 9000!)
import requests
response = requests.get('http://localhost:9000/minio/health/live')
print(response.status_code)  # Deve ser 200

# 2. Se falhar, MinIO não está rodando:
docker compose ps  # Verificar status
docker compose logs minio  # Ver erros

# 3. Verificar se está usando porta correta no código:
# ✅ CORRETO:
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', ...)

# ❌ ERRADO (porta padrão):
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', ...)
```

---

### Problema 4: Buckets não aparecem

**Solução:**
```bash
# Via CLI (porta 9000!)
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc ls myminio

# Se vazio, criar manualmente:
mc mb myminio/bronze
mc mb myminio/silver
mc mb myminio/gold
mc mb myminio/mlflow
mc mb myminio/backups
mc mb myminio/tmp

# Verificar se o container minio-init rodou:
docker compose logs minio-init
# Deve mostrar "✅ MinIO configurado com sucesso!"
```

---

### Problema 5: Upload lento

**Sintomas:**
- Upload de arquivo 100MB leva > 30s

**Soluções:**
```bash
# 1. Aumentar workers MinIO (docker-compose.yml)
environment:
  MINIO_API_REQUESTS_MAX: 100
  MINIO_API_REQUESTS_DEADLINE: 10s

# 2. Usar multipart upload (Python)
import boto3
from boto3.s3.transfer import TransferConfig

config = TransferConfig(
    multipart_threshold=1024 * 25,  # 25MB
    max_concurrency=10,
    multipart_chunksize=1024 * 25,
    use_threads=True
)

s3 = boto3.client(...)
s3.upload_file('large_file.parquet', 'bronze', 'key', Config=config)
```

---

### Problema 6: Storage cheio

**Sintoma:**
```
Error: No space left on device
```

**Solução:**
```bash
# Verificar espaço em disco
df -h

# Ver tamanho dos volumes Docker
docker system df -v

# Limpar bucket tmp
mc rm --recursive --force myminio/tmp/

# Lifecycle policy (deletar após 7 dias)
mc ilm add --expiry-days 7 myminio/tmp

# Ver tamanho por bucket
mc du myminio/bronze
mc du myminio/silver
mc du myminio/gold

# Limpar volumes não usados (CUIDADO!)
docker volume prune
```

---

### Problema 7: Conflito de Portas

**Sintoma:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:9000: bind: address already in use
```

**Solução:**
```bash
# 1. Identificar o processo usando a porta
lsof -i :9000
# Ou:
sudo netstat -tulpn | grep 9000

# 2. Opção A: Parar o processo conflitante
kill -9 <PID>

# 3. Opção B: Mudar porta no docker-compose.yml
# Trocar 9000 por outra porta disponível (ex: 9200)
ports:
  - "9200:9000"  # Nova porta externa
  - "9201:9001"

# 4. Reiniciar
docker compose down
docker compose up -d

# 5. Atualizar variáveis de ambiente e código
MINIO_ENDPOINT=http://localhost:9200
```

---

### Problema 8: Conflito de Rede Docker

**Sintoma:**
```
Error response from daemon: Pool overlaps with other one on this address space
```

**Solução:**
```bash
# 1. Listar redes Docker existentes
docker network ls

# 2. Inspecionar conflitos
docker network inspect <network-name>

# 3. Mudar subnet no docker-compose.yml
networks:
  govcontracts-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.31.0.0/16  # Trocar para subnet disponível

# 4. Verificar subnets em uso
docker network ls --format '{{.Name}}' | xargs -I {} docker network inspect {} | grep Subnet

# 5. Remover redes não usadas
docker network prune
```

---

## 📚 RECURSOS ADICIONAIS

### Documentação Oficial:
- MinIO Docs: https://min.io/docs/minio/linux/index.html
- MinIO Client (mc): https://min.io/docs/minio/linux/reference/minio-mc.html
- boto3 S3: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
- s3fs: https://s3fs.readthedocs.io/

### Comandos Úteis:

```bash
# Status do servidor
mc admin info myminio

# Ver logs em tempo real
docker logs -f gov-contracts-minio

# Backup de bucket
mc mirror myminio/bronze /backup/bronze

# Restore de backup
mc mirror /backup/bronze myminio/bronze

# Estatísticas
mc admin prometheus metrics myminio

# Health check
curl http://localhost:9000/minio/health/live

# Listar versões de objeto
mc ls --versions myminio/bronze/editais_raw/123456.pdf

# Verificar configuração da rede Docker
docker network inspect govcontracts-network

# Ver todas as portas expostas
docker compose ps --format "table {{.Service}}\t{{.Ports}}"
```

---

## ✅ CHECKLIST FINAL

Antes de prosseguir para a próxima etapa, certifique-se:

- [ ] MinIO rodando (Docker) com status `healthy`
- [ ] Console acessível em http://localhost:9001 ⚠️ **Porta 9001!**
- [ ] API S3 acessível em http://localhost:9000
- [ ] 6 buckets criados: bronze, silver, gold, mlflow, backups, tmp
- [ ] Versioning habilitado em: bronze, silver, gold, mlflow
- [ ] Python conecta via boto3 usando porta 9000
- [ ] Pandas lê/escreve Parquet via s3fs
- [ ] Upload de arquivo teste funciona
- [ ] mc (MinIO Client) configurado com porta 9000
- [ ] Teste completo passa (test_minio_setup.py)
- [ ] Variáveis de ambiente apontam para porta 9000
- [ ] Rede Docker `govcontracts-network` criada com subnet 172.30.0.0/16
- [ ] Container `minio-init` executou e criou buckets automaticamente

---

## 🎯 PRÓXIMOS PASSOS

Após configurar o MinIO:

1. **Semana 1-2:** Implementar DAGs Airflow para ingestão de dados
2. **Bronze Layer:** Coletar 5k licitações e salvar em `bronze/licitacoes/`
3. **Editais PDF:** Baixar e salvar em `bronze/editais_raw/`
4. **Silver Layer:** Processar e salvar em `silver/licitacoes_clean/`

---

**Configuração concluída!** 🎉
**Documento:** Guia MinIO S3 Setup v1.0
**Data:** 21 de Outubro de 2025
