# Scripts Utilitários

Este diretório contém scripts utilitários para operações de dados e manutenção do sistema.

## Scripts Disponíveis

### 1. `run_pncp_ingestion.py` - Ingestão Manual PNCP

Script standalone para executar a ingestão de dados do PNCP sem Airflow.

**Uso:**
```bash
# Ingerir dados de hoje (modalidade Pregão Eletrônico)
python scripts/run_pncp_ingestion.py

# Ingerir data específica
python scripts/run_pncp_ingestion.py --mode custom --date 20251023

# Ingerir múltiplas páginas
python scripts/run_pncp_ingestion.py --mode custom --date 20251023 --pages 5

# Ingerir múltiplas modalidades
python scripts/run_pncp_ingestion.py --mode custom --date 20251023 --modalidades 1,2,3
```

**Modalidades disponíveis:**
- 1: Pregão Eletrônico
- 2: Concorrência Eletrônica
- 3: Concorrência Presencial
- 4: Tomada de Preços
- 5: Convite
- 6: Dispensa Eletrônica
- 7: Dispensa Presencial
- 8: Inexigibilidade
- 9: Credenciamento
- 10: Pré-qualificação
- 11: Leilão Eletrônico

**Características:**
- ✅ Gerenciamento de estado com deduplicação
- ✅ Formato Parquet (99% compressão vs JSON)
- ✅ Upload automático para MinIO Bronze layer
- ✅ Validação de dados
- ✅ Carregamento automático de variáveis de ambiente (.env)

---

### 2. `report_pncp_bronze.py` - Relatório da Camada Bronze

Gera relatórios estatísticos sobre as licitações coletadas na camada Bronze do PNCP.

**Uso:**
```bash
# Relatório dos últimos 30 dias (padrão)
python scripts/report_pncp_bronze.py

# Período específico
python scripts/report_pncp_bronze.py --start-date 2025-10-01 --end-date 2025-10-31

# Com detalhamento diário
python scripts/report_pncp_bronze.py --detailed

# Com logs verbosos
python scripts/report_pncp_bronze.py --verbose

# Combinando opções
python scripts/report_pncp_bronze.py --start-date 2025-10-01 --detailed --verbose
```

**Saída do relatório:**

```
================================================================================
📊 PNCP Bronze Layer - Relatório de Licitações Coletadas
================================================================================

📈 Estatísticas Gerais:
   Total de arquivos Parquet: 5
   Total de registros: 9,904
   Licitações únicas (sequencialCompra): 3,056

📅 Por Ano:
   2025: 3,056 licitações únicas (9,904 registros)

📆 Por Mês:
   2025-10: 3,056 licitações únicas (9,904 registros)

📋 Por Dia:  # Apenas com --detailed
   2025-10-21: 2,317 licitações únicas (6,380 registros)
   2025-10-22: 1,055 licitações únicas (2,195 registros)
   2025-10-23: 815 licitações únicas (1,329 registros)

================================================================================
```

**Características:**
- 📊 Contagem de licitações únicas por `sequencialCompra`
- 📅 Agregação por ano, mês e dia
- 📈 Total de registros vs. licitações únicas
- 🔍 Detecção automática de colunas de ID
- 📦 Leitura direta de Parquet do MinIO
- ⚡ Performance otimizada com pandas

**Informações fornecidas:**
1. **Total de arquivos**: Número de arquivos Parquet processados
2. **Total de registros**: Soma de todas as linhas nos arquivos
3. **Licitações únicas**: Número de licitações distintas (por ID único)
4. **Agregações**:
   - Por ano (sempre)
   - Por mês (sempre)
   - Por dia (apenas com `--detailed`)

**Casos de uso:**
- Monitorar volume de dados coletados
- Identificar períodos com maior/menor atividade
- Validar processo de ingestão incremental
- Gerar métricas para dashboards
- Auditar duplicações e qualidade dos dados

---

## Estrutura de Dados

### Bronze Layer (MinIO)

```
lh-bronze/
└── pncp/
    ├── year=2025/
    │   └── month=10/
    │       ├── day=22/
    │       │   └── pncp_20251022_000000.parquet
    │       └── day=23/
    │           ├── pncp_20251023_000000.parquet
    │           ├── pncp_20251023_020000.parquet
    │           └── pncp_20251023_130000.parquet
    └── _state/
        └── year=2025/
            └── month=10/
                └── day=23/
                    └── state_20251023.json
```

### Formato dos Arquivos

**Parquet (dados):**
- Formato colunar binário
- Compressão snappy
- 35 colunas de metadados PNCP
- Particionamento por ano/mês/dia

**JSON (estado):**
- Lista de IDs processados
- Metadados de ingestão
- Timestamps de atualização

---

## Configuração

Todos os scripts carregam automaticamente o arquivo `.env` do diretório raiz do projeto.

**Variáveis necessárias:**
```bash
# MinIO (host machine)
MINIO_ENDPOINT_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Buckets
BUCKET_BRONZE=lh-bronze
BUCKET_SILVER=lh-silver
BUCKET_GOLD=lh-gold
```

**Nota:** Para scripts rodando fora de containers Docker, use `localhost:9000`.
Para DAGs do Airflow, o endpoint é `http://minio:9000` (configurado automaticamente).

---

## Dependências

### Opção 1: Ambiente Virtual Isolado (Recomendado para CLI)

```bash
# Criar ambiente virtual
python3 -m venv .venv

# Ativar (Linux/Mac)
source .venv/bin/activate

# Ativar (Windows)
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements-scripts.txt

# Rodar scripts
python scripts/report_pncp_bronze.py
python scripts/run_pncp_ingestion.py
```

### Opção 2: Poetry (Desenvolvimento Backend)

```bash
cd backend
poetry install
poetry run python ../scripts/report_pncp_bronze.py
```

### Opção 3: Docker (Airflow)

```bash
docker compose -f airflow/compose.yml exec airflow-webserver \
  python3 /opt/airflow/scripts/report_pncp_bronze.py
```

---

## Troubleshooting

### Erro: "Could not connect to MinIO"

**Solução:** Verifique se o MinIO está rodando:
```bash
docker compose ps minio
curl http://localhost:9000/minio/health/live
```

### Erro: "No module named 'backend'"

**Solução:** Execute do diretório raiz do projeto:
```bash
cd /home/gov-contracts-ai
python scripts/report_pncp_bronze.py
```

### Erro: "No Parquet files found"

**Solução:** Verifique se há dados no Bronze:
```bash
# Via MinIO Console
open http://localhost:9001

# Via script Python
python -c "from backend.app.core.minio_client import MinIOClient; \
  c = MinIOClient(); \
  print(c.list_objects('lh-bronze', prefix='pncp/'))"
```

---

## Contribuindo

Ao adicionar novos scripts:

1. Adicione shebang: `#!/usr/bin/env python3`
2. Adicione docstring com descrição e exemplos de uso
3. Suporte argumentos via `argparse`
4. Carregue `.env` com `python-dotenv`
5. Configure logging apropriado
6. Atualize este README
7. Atualize `CLAUDE.md` se necessário
