# 2025-10-23: Correção de Timezone e Pendulum nas DAGs

## Problema Identificado

Estávamos tendo vários problemas com datas nas DAGs:

1. **Uso inconsistente de timezones**: Mistura de UTC, naive datetimes e timezone local
2. **Salvamento de arquivos com datas erradas**: Particionamento inconsistente (UTC vs São Paulo)
3. **Confusão entre `execution_date` e `logical_date`**: Airflow 3.x mudou para `logical_date`
4. **Falta de padronização**: Cada DAG e serviço usava uma abordagem diferente

## Solução Implementada

### 1. Padronização com Pendulum

**Por que Pendulum?**
- Airflow internamente usa Pendulum para `logical_date`
- Melhor tratamento de timezone que `datetime` nativo
- API consistente e intuitiva
- Lida corretamente com horário de verão (DST)

**Exemplo:**
```python
import pendulum

# Criar datetime timezone-aware
dt = pendulum.datetime(2025, 10, 23, 15, 30, tz="America/Sao_Paulo")

# Converter UTC para São Paulo
utc_dt = pendulum.datetime(2025, 10, 23, 18, 30, tz="UTC")
sp_dt = utc_dt.in_timezone("America/Sao_Paulo")  # 15:30 -03:00

# Formatar datas
date_str = sp_dt.format("YYYYMMDD")  # "20251023"

# Aritmética de datas (respeita DST)
tomorrow = sp_dt.add(days=1)
```

### 2. Módulos Utilitários Criados

#### Backend: `backend/app/core/datetime_utils.py`

Funções para gerenciar datas com timezone:

```python
from backend.app.core.datetime_utils import (
    get_now_sao_paulo,    # Hora atual em São Paulo
    to_sao_paulo,          # Converter qualquer datetime para SP
    format_date,           # Formatar como YYYYMMDD
    format_datetime,       # Formatar como YYYYMMDD_HHMMSS
    get_partition_path,    # Obter year/month/day
    parse_date_str,        # Parse de string YYYYMMDD
)
```

#### Airflow: `airflow/dags/utils/dates.py`

Funções específicas para DAGs:

```python
from utils.dates import (
    to_sao_paulo,                   # Converter para SP
    get_date_range_for_execution,   # Range de datas
    get_yesterday,                  # Ontem em SP
    get_last_n_days,                # Últimos N dias
    get_now_sao_paulo,              # Hora atual em SP
    format_date,                    # Formatar YYYYMMDD
)
```

### 3. Configuração do Airflow

Atualizado `infrastructure/docker/airflow/compose.yml`:

```yaml
x-airflow-common-env: &airflow-common-env
  # Timezone configuration
  AIRFLOW__CORE__DEFAULT_TIMEZONE: 'America/Sao_Paulo'
  AIRFLOW__CORE__DEFAULT_UI_TIMEZONE: 'America/Sao_Paulo'
  TZ: 'America/Sao_Paulo'
```

**O que isso faz:**
- `DEFAULT_TIMEZONE`: Airflow interpreta datetimes naive como SP
- `DEFAULT_UI_TIMEZONE`: UI do Airflow mostra horários em SP
- `TZ`: Timezone do sistema do container

### 4. Correções no Storage Client

Atualizado `backend/app/core/storage_client.py`:

**Antes:**
```python
if date is None:
    date = datetime.now()  # ❌ Naive datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # ❌ Naive
```

**Depois:**
```python
if date is None:
    date = get_now_sao_paulo()  # ✅ Timezone-aware
else:
    date = to_sao_paulo(date)   # ✅ Converte para SP

timestamp = format_datetime(date)  # ✅ Usa timezone SP
```

### 5. Correções nas DAGs

#### Backfill DAG

**Antes:**
```python
from datetime import datetime, timedelta

end_date = datetime.now()  # ❌ Naive
start_date = end_date - timedelta(days=days_back)

while current_date <= end_date:
    date_str = current_date.strftime("%Y%m%d")
    # ...
    current_date += timedelta(days=1)  # ❌ Não respeita DST
```

**Depois:**
```python
import pendulum

end_date = pendulum.now("America/Sao_Paulo")  # ✅ Timezone-aware
start_date = end_date.subtract(days=days_back)

while current_date <= end_date:
    date_str = current_date.format("YYYYMMDD")
    # ...
    current_date = current_date.add(days=1)  # ✅ Respeita DST
```

#### DAGs de Ingestão

**Antes:**
```python
execution_date = context.get("logical_date")
date_str = execution_date.strftime("%Y%m%d")  # ❌ UTC date!
```

**Depois:**
```python
from utils.dates import to_sao_paulo, format_date

execution_date = context.get("logical_date")  # UTC
sp_date = to_sao_paulo(execution_date)        # ✅ Convert to SP
date_str = format_date(sp_date)               # ✅ SP date
```

## Particionamento de Dados

Agora todos os dados são particionados usando **data de São Paulo**:

```
bronze/
  pncp/
    year=2025/
      month=10/
        day=23/          # ✅ Data de São Paulo (não UTC)
          pncp_20251023_153045.parquet
```

**Por que isso importa:**
- Uma DAG rodando às 2 AM de São Paulo processa dados de 23 de outubro
- Sem conversão de timezone, criaria partição de 22 de outubro (UTC)
- Queries esperando dados de 23 de outubro falhariam

## Casos de Uso Comuns

### Caso 1: DAG com execution_date

```python
def my_task(**context):
    # Airflow passa logical_date em UTC
    execution_date = context.get("logical_date")

    # Converter para São Paulo
    from utils.dates import to_sao_paulo, format_date
    sp_date = to_sao_paulo(execution_date)
    date_str = format_date(sp_date)  # "20251023"

    # Usar data convertida
    storage.upload_to_bronze(data, date=sp_date)
```

### Caso 2: Serviço backend com hora atual

```python
from backend.app.core.datetime_utils import get_now_sao_paulo

class MyService:
    def process_data(self):
        # Obter hora atual em São Paulo
        now = get_now_sao_paulo()

        # Usar em uploads
        self.storage.upload_to_bronze(data, date=now)
```

### Caso 3: Backfill de range de datas

```python
import pendulum

end_date = pendulum.now("America/Sao_Paulo")
start_date = end_date.subtract(days=90)

current_date = start_date
while current_date <= end_date:
    date_str = current_date.format("YYYYMMDD")
    # Processar data
    current_date = current_date.add(days=1)  # ✅ Respeita DST
```

## Armadilhas Evitadas

### ❌ EVITAR: datetime.now() sem timezone

```python
from datetime import datetime
date = datetime.now()  # ❌ Naive datetime
```

### ✅ USAR: Pendulum com timezone

```python
import pendulum
date = pendulum.now("America/Sao_Paulo")  # ✅ Timezone-aware
```

---

### ❌ EVITAR: timedelta para aritmética

```python
current_date += timedelta(days=1)  # ❌ Não respeita DST
```

### ✅ USAR: Pendulum add/subtract

```python
current_date = current_date.add(days=1)  # ✅ Respeita DST
```

---

### ❌ EVITAR: Usar execution_date direto

```python
execution_date = context["execution_date"]
date_str = execution_date.strftime("%Y%m%d")  # ❌ UTC date!
```

### ✅ USAR: Converter para São Paulo

```python
from utils.dates import to_sao_paulo, format_date
sp_date = to_sao_paulo(execution_date)
date_str = format_date(sp_date)  # ✅ SP date
```

## Testes Realizados

### Teste 1: Conversão UTC → São Paulo

```python
import pendulum
from utils.dates import to_sao_paulo

utc_dt = pendulum.datetime(2025, 10, 24, 3, 0, tz="UTC")
sp_dt = to_sao_paulo(utc_dt)

assert sp_dt.hour == 0  # UTC 03:00 = SP 00:00
assert sp_dt.day == 24  # Ainda 24 de outubro
```

### Teste 2: Formatação de data

```python
from utils.dates import format_date
import pendulum

dt = pendulum.datetime(2025, 10, 23, 15, 30, tz="America/Sao_Paulo")
date_str = format_date(dt)

assert date_str == "20251023"
```

### Teste 3: Storage Client

```python
from app.core.datetime_utils import get_now_sao_paulo
from app.core.storage_client import get_storage_client

now = get_now_sao_paulo()
storage = get_storage_client()

# Upload deve usar timezone SP para particionamento
storage.upload_to_bronze(data, source="test", date=now)
```

## Resultados

✅ Todas as DAGs carregadas com sucesso
✅ Timezone utilities funcionando no Airflow
✅ Storage client usando timezone-aware dates
✅ Documentação completa criada ([docs/timezone-handling.md](../timezone-handling.md))

## Arquivos Modificados

### Criados
- `backend/app/core/datetime_utils.py` - Utilities de timezone para backend
- `docs/timezone-handling.md` - Documentação completa

### Modificados
- `airflow/dags/utils/dates.py` - Migrado para Pendulum
- `airflow/dags/bronze/pncp/backfill.py` - Usa Pendulum
- `backend/app/core/storage_client.py` - Usa timezone-aware dates
- `infrastructure/docker/airflow/compose.yml` - Configuração de timezone

## Próximos Passos

1. ✅ Testar DAG de backfill com timezone correto
2. ✅ Verificar particionamento de arquivos no MinIO
3. ⏳ Migrar demais DAGs para usar Pendulum (se necessário)
4. ⏳ Atualizar scripts standalone para usar datetime_utils

## Referências

- [Documentação Pendulum](https://pendulum.eustace.io/)
- [Guia de Timezone do Airflow](https://airflow.apache.org/docs/apache-airflow/stable/timezone.html)
- [docs/timezone-handling.md](../timezone-handling.md) - Guia completo
