# Plano de Migração para Pendulum

## Mudanças Necessárias nas DAGs

### 1. Imports (TODAS as DAGs)

**Antes:**
```python
from datetime import UTC, datetime, timedelta
```

**Depois:**
```python
import pendulum
from datetime import timedelta  # Manter apenas timedelta
```

### 2. Start Date do DAG

**Antes:**
```python
start_date=datetime(2025, 10, 1, tzinfo=UTC)
```

**Depois:**
```python
start_date=pendulum.datetime(2025, 10, 1, tz="America/Sao_Paulo")
```

### 3. Extração do logical_date

**Antes:**
```python
execution_date = (
    context.get("logical_date")
    or context.get("data_interval_start")
    or datetime.now(UTC)
)
```

**Depois:**
```python
# logical_date JÁ é Pendulum, não precisa fallback
execution_date = context["logical_date"]

# Se precisar converter para BRT
execution_date_br = execution_date.in_timezone("America/Sao_Paulo")
```

### 4. Formatação de Data

**Antes:**
```python
execution_id = execution_date.strftime("%Y%m%d_%H%M%S")
```

**Depois:**
```python
# Pendulum usa .format() ao invés de .strftime()
execution_id = execution_date.format("YYYYMMDD_HHmmss")
```

## Mudanças no Backend

### backend/app/services/ingestion/pncp.py

**Função: `fetch_hourly_incremental` (linha 148-176)**

**Antes:**
```python
import pytz

brazil_tz = pytz.timezone("America/Sao_Paulo")

if execution_date.tzinfo is None:
    execution_date_utc = pytz.UTC.localize(execution_date)
else:
    execution_date_utc = execution_date.astimezone(pytz.UTC)

execution_date_br = execution_date_utc.astimezone(brazil_tz)
data_inicial = execution_date_br.strftime("%Y%m%d")
```

**Depois:**
```python
import pendulum

# Se execution_date é Pendulum (vindo do Airflow)
if isinstance(execution_date, pendulum.DateTime):
    execution_date_br = execution_date.in_timezone("America/Sao_Paulo")
else:
    # Converter datetime para Pendulum
    execution_date_br = pendulum.instance(execution_date).in_timezone("America/Sao_Paulo")

data_inicial = execution_date_br.format("YYYYMMDD")
```

**Função: `fetch_daily_complete` (linha 202-220)**

Mesmo padrão acima.

## Configuração do Airflow

### airflow/compose.yml

Adicionar variáveis de ambiente:

```yaml
services:
  airflow-scheduler:
    environment:
      - TZ=America/Sao_Paulo
      - AIRFLOW__CORE__DEFAULT_TIMEZONE=America/Sao_Paulo

  airflow-webserver:
    environment:
      - TZ=America/Sao_Paulo
      - AIRFLOW__CORE__DEFAULT_TIMEZONE=America/Sao_Paulo
```

## Arquivos a Modificar

1. ✅ **airflow/dags/bronze/pncp/daily_ingestion.py**
2. ✅ **airflow/dags/bronze/pncp/hourly_ingestion.py**
3. ✅ **airflow/dags/bronze/pncp/backfill.py**
4. ✅ **airflow/dags/bronze/pncp/details_daily_ingestion.py**
5. ✅ **airflow/dags/bronze/pncp/details_hourly_ingestion.py**
6. ✅ **airflow/dags/bronze/pncp/cleanup_day.py**
7. ✅ **backend/app/services/ingestion/pncp.py**
8. ✅ **backend/app/services/ingestion/pncp_details.py**
9. ✅ **airflow/compose.yml**

## Exemplo: daily_ingestion.py Correto

```python
"""Bronze Layer: PNCP Daily Ingestion DAG with Pendulum."""

import sys
sys.path.insert(0, "/opt/airflow")

import pendulum
from datetime import timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from backend.app.core.storage_client import get_storage_client
from backend.app.domains.pncp import ModalidadeContratacao
from backend.app.services import (
    DataTransformationService,
    PNCPIngestionService,
    StateManager,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

def fetch_pncp_data(**context) -> dict:
    """Fetch complete day data from PNCP API."""
    # logical_date já é Pendulum UTC
    logical_date = context["logical_date"]

    # Converter para horário de Brasília
    execution_date_br = logical_date.in_timezone("America/Sao_Paulo")

    dag_run = context.get("dag_run")
    execution_id = dag_run.run_id if dag_run else execution_date_br.format("YYYYMMDD_HHmmss")

    # Call service (passa Pendulum)
    service = PNCPIngestionService()
    result = service.fetch_daily_complete(
        execution_date=execution_date_br,  # Passa com TZ correto
        modalidades=ModalidadeContratacao.get_all(),
    )

    # Save to temp storage
    storage = get_storage_client()
    temp_key = storage.upload_temp(
        data=result["data"],
        execution_id=execution_id,
        stage="raw",
        format="parquet",
    )

    return {
        "temp_key": temp_key,
        "metadata": result["metadata"],
        "record_count": len(result["data"]),
    }

# Define DAG
with DAG(
    dag_id="bronze_pncp_daily_ingestion",
    default_args=default_args,
    description="Daily ingestion with Pendulum timezone handling",
    schedule="0 2 * * *",  # 2 AM (será interpretado como America/Sao_Paulo)
    start_date=pendulum.datetime(2025, 10, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "pncp", "ingestion", "daily"],
) as dag:
    task_fetch = PythonOperator(
        task_id="fetch_pncp_data",
        python_callable=fetch_pncp_data,
    )
```

## Vantagens

1. **Não precisa mais de conversões pytz** - Pendulum faz automaticamente
2. **Timezone sempre correto** - Menos bugs de particionamento
3. **Código mais limpo** - Menos boilerplate
4. **Compatível com Airflow 3.x** - Usa API nativa
5. **DST automático** - Horário de verão do Brasil funcionará corretamente

## Testes Necessários

Após migração:

1. **Trigger manual com data específica**
   ```bash
   airflow dags trigger bronze_pncp_daily_ingestion \
     --conf '{"execution_date": "2025-10-24"}'
   ```

2. **Verificar partição no MinIO**
   - Deve criar: `pncp/year=2025/month=10/day=24/`
   - NÃO deve criar: `pncp/year=2025/month=10/day=23/` (bug anterior)

3. **Verificar logs**
   - Confirmar que data está sendo interpretada corretamente
   - Verificar se horário de Brasília está correto

4. **Report Bronze**
   ```bash
   python scripts/report_pncp_bronze.py --date 2025-10-24
   ```
   - Deve mostrar dados corretos no dia 24

## Rollback Plan

Se houver problemas:

1. **Revert DAG files** para versão anterior
2. **Restart Airflow scheduler/webserver**
3. **Reportar issue** no GitHub do projeto

## Cronograma Sugerido

1. **Fase 1 (1h):** Migrar 1 DAG (daily_ingestion.py) e testar
2. **Fase 2 (30min):** Se OK, migrar outras DAGs
3. **Fase 3 (30min):** Atualizar backend
4. **Fase 4 (30min):** Configurar Docker timezone
5. **Fase 5 (1h):** Testes end-to-end

Total: ~3.5 horas
