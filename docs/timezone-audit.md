# Auditoria de Timezone e Datas

## Problemas Identificados

### 1. Docker Timezone Confuso
```bash
$ docker exec govcontracts-airflow-scheduler date
Thu Oct 23 23:58:29 -03 2025  # Mostra -03 (BRT)

$ docker exec govcontracts-airflow-scheduler cat /etc/timezone
Etc/UTC  # Mas diz UTC!
```

**Problema:** Inconsistência entre timezone configurado e timezone efetivo.

### 2. DAGs Usam `datetime` em vez de `pendulum`

**Atual:**
```python
from datetime import UTC, datetime, timedelta

execution_date = context.get("logical_date") or datetime.now(UTC)
```

**Problema:**
- `logical_date` retorna um objeto **Pendulum**, não `datetime`
- Pendulum é timezone-aware por padrão
- Misturar `datetime` e `Pendulum` causa bugs sutis

**Correto (Pendulum):**
```python
import pendulum

execution_date = context.get("logical_date")  # Já é Pendulum!
# ou
execution_date = pendulum.now("America/Sao_Paulo")
```

### 3. Backend Faz Conversão Manual Duplicada

**Código atual (pncp.py:208-217):**
```python
import pytz

brazil_tz = pytz.timezone("America/Sao_Paulo")

if execution_date.tzinfo is None:
    execution_date_utc = pytz.UTC.localize(execution_date)
else:
    execution_date_utc = execution_date.astimezone(pytz.UTC)

execution_date_br = execution_date_utc.astimezone(brazil_tz)
target_date = execution_date_br
```

**Problema:**
- Se `execution_date` vem do Airflow como **Pendulum**, já tem timezone!
- Conversão para `pytz` é desnecessária
- Pendulum tem `.in_timezone()` mais simples

**Correto (Pendulum):**
```python
# Se execution_date é Pendulum (vindo do Airflow)
if hasattr(execution_date, 'in_timezone'):
    # É Pendulum
    target_date = execution_date.in_timezone("America/Sao_Paulo")
else:
    # É datetime, converter para Pendulum
    import pendulum
    target_date = pendulum.instance(execution_date).in_timezone("America/Sao_Paulo")
```

### 4. Particionamento Usa Data Errada

**Problema anterior (JÁ CORRIGIDO):**
```python
# ERRADO (causava data em partição errada)
target_date = execution_date - timedelta(days=1)  # Subtraía mais 1 dia!
```

**Atual (CORRETO):**
```python
# Airflow execution_date já é D-1, não precisa subtrair
target_date = execution_date_br  # Usa diretamente
```

## Solução Proposta

### Fase 1: Padronizar uso de Pendulum nas DAGs

1. **Remover imports de datetime**
2. **Adicionar import de pendulum**
3. **Usar Pendulum para todas as operações de data**

```python
import pendulum
from airflow import DAG

# Start date com Pendulum
start_date = pendulum.datetime(2025, 10, 1, tz="America/Sao_Paulo")

# No DAG context
def my_task(**context):
    logical_date = context["logical_date"]  # Já é Pendulum!

    # Conversão para BRT (se necessário)
    br_date = logical_date.in_timezone("America/Sao_Paulo")

    # Formatação
    date_str = br_date.format("YYYYMMDD")
```

### Fase 2: Simplificar Backend

**Opção A - Backend espera Pendulum:**
```python
def fetch_daily_complete(self, execution_date: pendulum.DateTime, ...):
    # execution_date já vem com timezone correto
    target_date = execution_date.in_timezone("America/Sao_Paulo")
    data_inicial = target_date.format("YYYYMMDD")
```

**Opção B - Backend aceita ambos (compatibilidade):**
```python
import pendulum
from typing import Union
from datetime import datetime

def fetch_daily_complete(
    self,
    execution_date: Union[pendulum.DateTime, datetime],
    ...
):
    # Normalizar para Pendulum
    if isinstance(execution_date, pendulum.DateTime):
        dt = execution_date
    else:
        dt = pendulum.instance(execution_date)

    # Garantir timezone BR
    target_date = dt.in_timezone("America/Sao_Paulo")
    data_inicial = target_date.format("YYYYMMDD")
```

### Fase 3: Configurar Timezone do Airflow

**airflow/compose.yml:**
```yaml
services:
  airflow-scheduler:
    environment:
      - TZ=America/Sao_Paulo
      - AIRFLOW__CORE__DEFAULT_TIMEZONE=America/Sao_Paulo
```

**airflow.cfg:**
```ini
[core]
default_timezone = America/Sao_Paulo
```

## Benefícios do Pendulum

1. **Timezone-aware por padrão** - Nunca esquece de adicionar timezone
2. **DST automático** - Lida com horário de verão do Brasil automaticamente
3. **API intuitiva** - `.in_timezone()`, `.add(days=1)`, etc.
4. **Nativo do Airflow** - `logical_date` já é Pendulum
5. **Serialização correta** - JSON, pickle, etc.

## Exemplo Completo de DAG Corrigida

```python
import pendulum
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

def process_data(**context):
    # logical_date já é Pendulum com UTC
    logical_date = context["logical_date"]

    # Converter para horário de Brasília
    br_date = logical_date.in_timezone("America/Sao_Paulo")

    # Operações de data são simples
    yesterday = br_date.subtract(days=1)
    tomorrow = br_date.add(days=1)

    # Formatação intuitiva
    date_str = br_date.format("YYYY-MM-DD")
    datetime_str = br_date.to_datetime_string()  # "2025-10-23 00:00:00"

    print(f"Processando data: {date_str} (horário de Brasília)")

    # Passar para backend (já está no timezone correto)
    service.process(execution_date=br_date)

with DAG(
    dag_id="example_pendulum",
    start_date=pendulum.datetime(2025, 10, 1, tz="America/Sao_Paulo"),
    schedule="0 2 * * *",  # 2 AM BRT
    catchup=False,
    default_args={
        "owner": "data-engineering",
    },
) as dag:
    task = PythonOperator(
        task_id="process",
        python_callable=process_data,
    )
```

## Checklist de Implementação

- [ ] Auditar todas as DAGs em `airflow/dags/bronze/pncp/`
- [ ] Substituir `datetime` por `pendulum` nas DAGs
- [ ] Simplificar conversão de timezone no backend
- [ ] Configurar timezone do Docker/Airflow
- [ ] Testar com data manual (trigger com conf)
- [ ] Validar particionamento correto no MinIO
- [ ] Documentar padrões de data no CLAUDE.md

## Referências

- [Pendulum Documentation](https://pendulum.eustace.io/)
- [Airflow Timezone Guide](https://airflow.apache.org/docs/apache-airflow/stable/timezone.html)
- [Airflow 3.x Migration - Pendulum](https://airflow.apache.org/docs/apache-airflow/stable/upgrading-to-3.html#pendulum-3)
