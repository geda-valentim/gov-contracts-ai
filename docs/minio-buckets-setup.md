# MinIO Buckets Setup - Gov Contracts AI

Este documento explica como funcionam os buckets MinIO no projeto e como gerenciá-los.

## 📦 Arquitetura de Buckets (Medallion Architecture)

O projeto usa a **Medallion Architecture** com três camadas de dados:

| Bucket | Camada | Descrição | Versionamento | Lifecycle |
|--------|--------|-----------|---------------|-----------|
| `gov-lh-bronze` | Bronze | Dados brutos do PNCP | ✅ Habilitado | - |
| `gov-lh-silver` | Silver | Dados limpos e validados | ✅ Habilitado | - |
| `gov-lh-gold` | Gold | Features para ML | ✅ Habilitado | - |
| `gov-mlflow` | - | Artefatos do MLflow | ❌ Não | - |
| `gov-backups` | - | Backups do sistema | ❌ Não | - |
| `gov-tmp` | - | Arquivos temporários | ❌ Não | 7 dias |

### Estrutura do Bucket Bronze

```
gov-lh-bronze/
├── licitacoes/           # Dados de licitações do PNCP
├── editais_raw/          # PDFs dos editais
├── editais_text/         # Texto extraído dos PDFs
├── precos_mercado/       # Preços de referência
└── cnpj/                 # Dados de empresas
```

## 🚀 Inicialização dos Buckets

### Automática (Recomendado)

Ao rodar `make up-smart`, os buckets são verificados e criados automaticamente se necessário:

```bash
make up-smart
```

Saída esperada:
```
🪣 Checking MinIO buckets...
  ✅ All buckets already exist
```

Ou, se buckets estiverem faltando:
```
🪣 Checking MinIO buckets...
  🔧 Initializing missing buckets...
  ✅ Buckets initialized!
```

### Manual

Se você precisar inicializar os buckets manualmente:

```bash
make init-buckets
```

Este comando:
1. Detecta qual MinIO está rodando (local ou compartilhado)
2. Conecta-se à rede correta
3. Cria todos os buckets definidos no `.env`
4. Configura versionamento e lifecycle policies
5. Cria a estrutura de pastas no bucket bronze

## 🔧 Configuração

### Definindo Nomes dos Buckets

Os nomes dos buckets são configurados no arquivo `.env`:

```bash
# Data Lake Buckets (Medallion Architecture)
BUCKET_BRONZE=gov-lh-bronze
BUCKET_SILVER=gov-lh-silver
BUCKET_GOLD=gov-lh-gold
BUCKET_MLFLOW=gov-mlflow
BUCKET_BACKUPS=gov-backups
BUCKET_TMP=gov-tmp
```

**Importante:** Após alterar os nomes no `.env`, execute:
```bash
make init-buckets
```

### MinIO Compartilhado vs Local

O projeto suporta dois cenários:

#### Cenário 1: MinIO Compartilhado (shared-minio)

Usado quando você tem um MinIO compartilhado entre múltiplos projetos:

- Container: `shared-minio`
- Rede: `shared-dev-network`
- Porta: `9000`
- Console: `9001`

Vantagens:
- ✅ Compartilhamento de recursos
- ✅ Um único MinIO para vários projetos
- ✅ Economia de memória

**Nota:** Com MinIO compartilhado, o serviço `minio-init` local não é executado. Por isso, é essencial rodar `make init-buckets` manualmente ou usar `make up-smart`.

#### Cenário 2: MinIO Local (govcontracts-minio)

Quando você inicia o MinIO localmente com o projeto:

- Container: `govcontracts-minio`
- Rede: `gov-contracts-ai_govcontracts-network`
- Porta: `9000`
- Console: `9001`

Vantagens:
- ✅ Isolamento completo
- ✅ Configuração independente
- ✅ Inicialização automática via docker-compose

## 🔍 Verificação e Troubleshooting

### Verificar se buckets existem

```bash
# Script de verificação rápida
./scripts/check-buckets.sh && echo "✅ OK" || echo "❌ Buckets faltando"

# Listar buckets manualmente
docker exec shared-minio mc ls local/  # Para shared-minio
# ou
docker exec govcontracts-minio mc ls local/  # Para MinIO local
```

### Ver estrutura de um bucket

```bash
docker exec shared-minio mc tree local/gov-lh-bronze
```

### Recriar todos os buckets

Se você quiser recriar tudo do zero:

```bash
# Deletar buckets (CUIDADO! Isso apaga todos os dados)
docker exec shared-minio mc rb --force --dangerous local/gov-lh-bronze
docker exec shared-minio mc rb --force --dangerous local/gov-lh-silver
docker exec shared-minio mc rb --force --dangerous local/gov-lh-gold
docker exec shared-minio mc rb --force --dangerous local/gov-mlflow
docker exec shared-minio mc rb --force --dangerous local/gov-backups
docker exec shared-minio mc rb --force --dangerous local/gov-tmp

# Recriar
make init-buckets
```

### Verificar versionamento

```bash
docker exec shared-minio mc version info local/gov-lh-bronze
docker exec shared-minio mc version info local/gov-lh-silver
docker exec shared-minio mc version info local/gov-lh-gold
```

Saída esperada:
```
local/gov-lh-bronze versioning is enabled
```

### Verificar lifecycle policy (tmp bucket)

```bash
docker exec shared-minio mc ilm ls local/gov-tmp
```

Saída esperada:
```
     ID     | Expiration |  Date/Days   | ...
expire-tmp  | Enabled    | 7 day(s)     | ...
```

## 🛠️ Scripts Auxiliares

### check-buckets.sh

Verifica se todos os buckets necessários existem:

```bash
./scripts/check-buckets.sh
echo $?  # 0 = todos existem, 1 = algum faltando
```

### init-buckets.sh

Script completo de inicialização (executado via `make init-buckets`):

Localizado em: `infrastructure/docker/minio/init-buckets.sh`

Funções:
- ✅ Cria buckets se não existirem
- ✅ Configura versionamento para bronze/silver/gold
- ✅ Configura lifecycle de 7 dias para tmp
- ✅ Cria estrutura de pastas no bronze
- ✅ Valida a criação com relatório final

## 📝 Comandos Make Relacionados

```bash
# Verificar disponibilidade do MinIO
make check-minio

# Verificar todos os serviços
make check-services

# Inicializar buckets
make init-buckets

# Startup inteligente (verifica e cria buckets)
make up-smart

# Corrigir conectividade Airflow-MinIO
make fix-minio-network
```

## 🔐 Credenciais

As credenciais do MinIO estão definidas no `.env`:

```bash
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

**Console Web:** http://localhost:9001

## 🌐 Acesso via Navegador

1. Abra http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Navegue pelos buckets criados
4. Visualize objetos, versões e configurações

## ⚠️ Importante

1. **Não comite dados sensíveis** nos buckets
2. **Use .gitignore** para pastas de dados locais
3. **Em produção**, use credenciais fortes e AWS Secrets Manager
4. **Buckets versionados** mantêm histórico de mudanças (bronze/silver/gold)
5. **Bucket tmp** tem retenção de 7 dias (limpeza automática)

## 📚 Referências

- [MinIO Client Guide](https://min.io/docs/minio/linux/reference/minio-mc.html)
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Object Versioning](https://min.io/docs/minio/linux/administration/object-management/object-versioning.html)
- [Lifecycle Management](https://min.io/docs/minio/linux/administration/object-management/object-lifecycle-management.html)

---

**Última atualização:** 2025-11-09
**Autor:** Gov Contracts AI Bot
