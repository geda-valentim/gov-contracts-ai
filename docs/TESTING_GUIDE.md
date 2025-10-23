# Testing Guide - PNCP Ingestion Pipeline

## 📋 Overview

Este guia descreve como testar o pipeline de ingestão PNCP completo com State Management e Parquet.

## 🛠️ Setup Inicial

### 1. Instalar Dependências

```bash
cd backend
poetry install
```

### 2. Iniciar Infraestrutura (MinIO)

```bash
# Usando docker compose (não docker-compose)
docker compose up -d minio

# Verificar status
docker compose ps minio
```

### 3. Configurar Environment Variables

```bash
# backend/.env
STORAGE_TYPE=minio
MINIO_ENDPOINT_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## ✅ Testes Manuais

### Teste 1: Primeira Execução (Todos Novos)

**Objetivo:** Verificar que primeira execução ingere todos os registros

```bash
python scripts/run_pncp_ingestion.py \
    --mode custom \
    --date 20251022 \
    --pages 1 \
    --modalidades 1
```

**Resultado Esperado:**
```
================================================================================
STEP 2: STATE FILTERING (INCREMENTAL DEDUPLICATION)
================================================================================
📊 State Filtering: 500 input → 500 new (0 duplicates filtered)

================================================================================
STEP 4: UPLOADING TO BRONZE LAYER (PARQUET)
================================================================================
📦 Uploaded to: s3://bronze/pncp/year=2025/month=10/day=22/pncp_20251022_HHMMSS.parquet
Records uploaded: 500 (Parquet format)
Filter stats: 500 new, 0 duplicates filtered
```

**Verificar:**
- ✅ 500 registros novos
- ✅ 0 duplicatas filtradas
- ✅ Arquivo Parquet criado
- ✅ State file criado

### Teste 2: Segunda Execução (Duplicatas)

**Objetivo:** Verificar que segunda execução filtra duplicatas

```bash
# EXECUTAR O MESMO COMANDO NOVAMENTE
python scripts/run_pncp_ingestion.py \
    --mode custom \
    --date 20251022 \
    --pages 1 \
    --modalidades 1
```

**Resultado Esperado:**
```
================================================================================
STEP 2: STATE FILTERING (INCREMENTAL DEDUPLICATION)
================================================================================
📊 State Filtering: 500 input → 0 new (500 duplicates filtered)

⚠️  No new records to process (all duplicates)
```

**Verificar:**
- ✅ 0 registros novos
- ✅ 500 duplicatas filtradas
- ✅ Nenhum arquivo Parquet criado
- ✅ State file atualizado com timestamp

### Teste 3: Terceira Execução (Novos + Duplicatas)

**Objetivo:** Simular cenário misto (API retorna dados novos + antigos)

```bash
# Aumentar páginas para pegar dados novos
python scripts/run_pncp_ingestion.py \
    --mode custom \
    --date 20251022 \
    --pages 2 \
    --modalidades 1
```

**Resultado Esperado:**
```
================================================================================
STEP 2: STATE FILTERING (INCREMENTAL DEDUPLICATION)
================================================================================
📊 State Filtering: 1000 input → 500 new (500 duplicates filtered)

================================================================================
STEP 4: UPLOADING TO BRONZE LAYER (PARQUET)
================================================================================
📦 Uploaded to: s3://bronze/pncp/year=2025/month=10/day=22/pncp_20251022_HHMMSS.parquet
Records uploaded: 500 (Parquet format)
Filter stats: 500 new, 500 duplicates filtered
```

**Verificar:**
- ✅ ~500 registros novos (da página 2)
- ✅ ~500 duplicatas filtradas (da página 1)
- ✅ Novo arquivo Parquet criado (apenas com novos)
- ✅ State file atualizado com novos IDs

## 🧪 Testes Automatizados

### Teste 4: State Manager Unitário

```bash
python test_state_manager_simple.py
```

**Resultado Esperado:**
```
================================================================================
✅ ALL TESTS PASSED!
================================================================================

📋 Summary:
   ✓ State file created correctly
   ✓ Duplicate filtering works
   ✓ State persists across executions
   ✓ Execution metadata tracked
   ✓ Total count accumulates correctly
```

## 📊 Verificação de Arquivos

### Verificar Arquivos Bronze (MinIO)

```bash
# Listar arquivos Bronze
mc ls minio/bronze/pncp/year=2025/month=10/day=22/

# Output esperado:
# [2025-10-22 10:00:00] 85KB pncp_20251022_100000.parquet
# [2025-10-22 12:00:00] 42KB pncp_20251022_120000.parquet
```

### Verificar State Files

```bash
# Listar state files
mc ls minio/bronze/pncp/_state/year=2025/month=10/day=22/

# Output esperado:
# [2025-10-22 12:00:05] 2.5KB state_20251022.json
```

### Ler State File

```bash
# Download state file
mc cat minio/bronze/pncp/_state/year=2025/month=10/day=22/state_20251022.json | jq

# Output esperado:
{
  "date": "2025-10-22",
  "processed_ids": [
    "07954480000179-1-022746/2025",
    "07954480000179-1-022747/2025",
    ...
  ],
  "total_processed": 1000,
  "executions": [
    {
      "timestamp": "2025-10-22T10:00:00Z",
      "new_records": 500,
      "duplicates_filtered": 0
    },
    {
      "timestamp": "2025-10-22T12:00:00Z",
      "new_records": 500,
      "duplicates_filtered": 500
    }
  ]
}
```

### Ler Arquivo Parquet

```bash
# Baixar e ler Parquet
mc cat minio/bronze/pncp/year=2025/month=10/day=22/pncp_20251022_100000.parquet > /tmp/data.parquet

python -c "
import pandas as pd
df = pd.read_parquet('/tmp/data.parquet')
print(f'Shape: {df.shape}')
print(f'Columns: {list(df.columns)}')
print(f'Sample:\\n{df.head()}')
"
```

## 🔍 Verificações de Qualidade

### Verificar Compressão Parquet

```bash
# Comparar tamanhos JSON vs Parquet
# (simulado - precisa ter ambos os formatos)

# Tamanho JSON esperado: ~500KB (500 registros)
# Tamanho Parquet esperado: ~85KB (500 registros)
# Redução: ~83%
```

### Verificar Tipos de Dados

```python
import pandas as pd

# Ler Parquet
df = pd.read_parquet('data.parquet')

# Verificar tipos
print(df.dtypes)

# Esperado:
# numeroControlePNCP        object
# valorTotalEstimado       float64
# dataPublicacaoPncp        datetime64[ns]
# orgaoEntidade_cnpj        object
# ...
```

## 📈 Testes de Performance

### Benchmark: JSON vs Parquet

```bash
# Criar arquivo JSON para comparação
python scripts/run_pncp_ingestion.py \
    --mode custom \
    --date 20251023 \
    --pages 10 \
    --modalidades 1

# Isso criará ~5000 registros

# Medir tempo de leitura (Python)
python -c "
import time
import pandas as pd

# JSON
start = time.time()
df_json = pd.read_json('data.json')
json_time = time.time() - start

# Parquet
start = time.time()
df_parquet = pd.read_parquet('data.parquet')
parquet_time = time.time() - start

print(f'JSON: {json_time:.3f}s')
print(f'Parquet: {parquet_time:.3f}s')
print(f'Speedup: {json_time/parquet_time:.1f}x')
"
```

**Resultado Esperado:**
```
JSON: 0.850s
Parquet: 0.045s
Speedup: 18.9x
```

## 🎯 Cenários de Teste Completos

### Cenário 1: Pipeline Hourly Completo

```bash
# Execução 1 - 08:00
python scripts/run_pncp_ingestion.py --mode hourly --modalidades 3 --pages 5

# Esperar alguns minutos (simula próxima hora)

# Execução 2 - 12:00 (mesmo dia)
python scripts/run_pncp_ingestion.py --mode hourly --modalidades 3 --pages 5

# Verificar:
# - Exec 1: Todos novos
# - Exec 2: Mix de novos e duplicatas
# - State file: Acumula IDs de ambas execuções
```

### Cenário 2: Cross-Day Boundary

```bash
# Dia 1
python scripts/run_pncp_ingestion.py --mode hourly --date 20251022

# Dia 2 (novo state file deve ser criado)
python scripts/run_pncp_ingestion.py --mode hourly --date 20251023

# Verificar:
# - 2 state files diferentes (um por dia)
# - Nenhuma interferência entre dias
```

### Cenário 3: Backfill Histórico

```bash
# Backfill de 1 semana
python scripts/run_pncp_ingestion.py \
    --mode backfill \
    --start-date 20251015 \
    --end-date 20251022 \
    --modalidades 2

# Verificar:
# - Arquivos Bronze criados para cada dia
# - State files criados para cada dia
# - Sem duplicatas entre dias
```

## ❌ Testes de Erro

### Teste 1: API Indisponível

```bash
# Desligar MinIO
docker compose stop minio

# Executar pipeline
python scripts/run_pncp_ingestion.py --mode hourly

# Esperado: Erro claro sobre conexão MinIO
```

### Teste 2: State File Corrompido

```bash
# Corromper state file manualmente
mc cat minio/bronze/pncp/_state/.../state_20251022.json | \
    sed 's/{/INVALID/' | \
    mc pipe minio/bronze/pncp/_state/.../state_20251022.json

# Executar pipeline
python scripts/run_pncp_ingestion.py --mode hourly

# Esperado: StateManager recria state file
```

## 📝 Checklist de Validação

Após cada teste, verificar:

- [ ] Logs mostram filtros de estado corretos
- [ ] Arquivos Parquet criados no Bronze
- [ ] State file atualizado com novos IDs
- [ ] Metadata de execução registrada
- [ ] Nenhum erro ou warning inesperado
- [ ] Tamanhos de arquivo razoáveis (~80-90% menor que JSON)
- [ ] Tipos de dados preservados no Parquet
- [ ] Particionamento Hive correto (year/month/day)

## 🔧 Troubleshooting

### Problema: ModuleNotFoundError

**Solução:**
```bash
cd backend
poetry install
poetry shell
```

### Problema: MinIO connection refused

**Solução:**
```bash
docker compose up -d minio
docker compose ps minio  # Verificar status
```

### Problema: State file não encontrado

**Causa:** Primeira execução (esperado)
**Ação:** Nada - StateManager cria automaticamente

### Problema: Todos registros duplicados (inesperado)

**Causa:** State file com IDs de execução anterior
**Solução:** Deletar state file para reprocessar
```bash
mc rm minio/bronze/pncp/_state/year=2025/month=10/day=22/state_20251022.json
```

## 🎓 Próximos Passos

Após validação manual:

1. **Integrar com Airflow** - Testar DAGs
2. **Monitoramento** - Adicionar métricas
3. **Alertas** - Configurar notificações
4. **Performance** - Benchmark em produção
5. **Scale** - Testar com volume completo

---

**Autor:** Claude Code + Gabriel
**Data:** 23 de Outubro de 2025
**Versão:** 1.0
