# Convenções de Commits - Gov Contracts AI

**Versão:** 1.0
**Data:** 22 de Outubro de 2025
**Padrão:** Conventional Commits + Gitmoji

---

## 📋 Formato Padrão

```
<emoji> <tipo>(<escopo>): <descrição>

[corpo opcional]

[rodapé opcional]
```

### Estrutura

- **emoji**: Emoji visual do Gitmoji (obrigatório)
- **tipo**: Tipo do commit (obrigatório)
- **escopo**: Parte do código afetada (opcional)
- **descrição**: Resumo curto (obrigatório, máx 72 caracteres)
- **corpo**: Explicação detalhada (opcional)
- **rodapé**: Breaking changes, issues (opcional)

---

## 🎯 Tipos de Commit

### Commits de Código

| Tipo | Emoji | Uso | Exemplo |
|------|-------|-----|---------|
| `feat` | ✨ `:sparkles:` | Nova funcionalidade | `✨ feat(api): adiciona endpoint de análise de risco` |
| `fix` | 🐛 `:bug:` | Correção de bug | `🐛 fix(ml): corrige cálculo do risk_score` |
| `refactor` | ♻️ `:recycle:` | Refatoração de código | `♻️ refactor(services): reorganiza lógica de alertas` |
| `perf` | ⚡ `:zap:` | Melhoria de performance | `⚡ perf(db): adiciona índice em risk_score` |
| `style` | 💄 `:lipstick:` | Formatação, UI/UX | `💄 style(frontend): ajusta cores dos níveis de criticidade` |
| `test` | ✅ `:white_check_mark:` | Adiciona/corrige testes | `✅ test(api): adiciona testes para alertas críticos` |

### Commits de Documentação

| Tipo | Emoji | Uso | Exemplo |
|------|-------|-----|---------|
| `docs` | 📝 `:memo:` | Documentação | `📝 docs: atualiza guia de terminologia` |
| `docs` | 📚 `:books:` | Doc técnica/tutorial | `📚 docs: adiciona tutorial de deployment` |

### Commits de Infraestrutura

| Tipo | Emoji | Uso | Exemplo |
|------|-------|-----|---------|
| `build` | 🏗️ `:building_construction:` | Sistema de build | `🏗️ build: configura Docker multi-stage` |
| `ci` | 👷 `:construction_worker:` | CI/CD | `👷 ci: adiciona workflow de testes` |
| `chore` | 🔧 `:wrench:` | Config, deps | `🔧 chore: atualiza poetry dependencies` |
| `docker` | 🐳 `:whale:` | Docker | `🐳 docker: adiciona compose para dev` |

### Commits de Dados e ML

| Tipo | Emoji | Uso | Exemplo |
|------|-------|-----|---------|
| `data` | 💾 `:floppy_disk:` | Pipeline de dados | `💾 data: implementa ingestão do PNCP` |
| `ml` | 🤖 `:robot:` | ML/AI | `🤖 ml: treina modelo XGBoost v1.2` |
| `model` | 🧠 `:brain:` | Modelos ML | `🧠 model: exporta modelo para ONNX` |

### Outros Commits Importantes

| Tipo | Emoji | Uso | Exemplo |
|------|-------|-----|---------|
| `security` | 🔒 `:lock:` | Segurança | `🔒 security: adiciona rate limiting na API` |
| `init` | 🎉 `:tada:` | Commit inicial | `🎉 init: projeto Gov Contracts AI` |
| `breaking` | 💥 `:boom:` | Breaking change | `💥 feat(api)!: altera schema de alertas` |
| `wip` | 🚧 `:construction:` | Work in progress | `🚧 wip: implementando RAG pipeline` |
| `revert` | ⏪ `:rewind:` | Reverte commit | `⏪ revert: reverte commit abc1234` |
| `hotfix` | 🚑 `:ambulance:` | Correção crítica | `🚑 hotfix: corrige vazamento de memória` |

---

## 📐 Escopos Sugeridos

Use escopos para indicar a parte do código afetada:

### Backend
- `api` - Endpoints da API
- `ml` - Código de ML/inferência
- `ai` - LLMs, RAG, NLP
- `db` - Database, migrations
- `cache` - Redis, caching
- `auth` - Autenticação/autorização
- `services` - Camada de serviços

### Frontend
- `ui` - Componentes UI
- `pages` - Páginas Next.js
- `hooks` - Custom hooks
- `api-client` - Cliente da API
- `charts` - Visualizações

### Infraestrutura
- `docker` - Docker, compose
- `terraform` - IaC
- `ci` - GitHub Actions
- `monitoring` - Prometheus, Grafana

### ML/Data
- `pipeline` - Pipelines de dados
- `features` - Feature engineering
- `training` - Treinamento de modelos
- `evaluation` - Avaliação de modelos
- `mlflow` - MLflow tracking

### Geral
- `deps` - Dependências
- `config` - Configurações
- `scripts` - Scripts utilitários
- `tests` - Testes

---

## ✍️ Exemplos Completos

### Exemplo 1: Nova Feature Simples
```bash
git commit -m "✨ feat(api): adiciona endpoint de alertas críticos"
```

### Exemplo 2: Bug Fix com Corpo
```bash
git commit -m "🐛 fix(ml): corrige normalização de features

O preprocessamento estava usando scale errado, causando
risk_scores inconsistentes. Agora usa StandardScaler
consistente com o treinamento.

Fixes #123"
```

### Exemplo 3: Breaking Change
```bash
git commit -m "💥 feat(api)!: altera schema de resposta de alertas

BREAKING CHANGE: O campo 'fraud_score' foi renomeado para
'risk_score' em todos os endpoints. Clientes precisam
atualizar suas integrações.

Migração:
- GET /alerts: response.fraud_score -> response.risk_score
- POST /analyze: response.is_fraud -> response.has_critical_alerts"
```

### Exemplo 4: Documentação
```bash
git commit -m "📝 docs: adiciona guia de terminologia oficial

Documenta todos os termos aprovados baseados na Alice (CGU)
e fornece checklist de conformidade."
```

### Exemplo 5: Docker/Infra
```bash
git commit -m "🐳 docker: adiciona serviços MinIO e PostgreSQL

- MinIO para Data Lake (S3-compatible)
- PostgreSQL 16 com pg_vector
- Redis para cache
- Healthchecks configurados"
```

### Exemplo 6: ML Model
```bash
git commit -m "🤖 ml(training): implementa pipeline de treinamento XGBoost

- Cross-validation 5-fold
- Hyperparameter tuning com Optuna
- SHAP explainer
- MLflow tracking automático

Resultados:
- Precision: 0.87
- Recall: 0.82
- F1-Score: 0.84"
```

### Exemplo 7: Performance
```bash
git commit -m "⚡ perf(db): adiciona índices em tabelas de alertas

Adiciona índices compostos em:
- (risk_score, analyzed_at)
- (alert_level, process_id)

Reduz tempo de query de 2.5s para 120ms (p95)"
```

### Exemplo 8: Testes
```bash
git commit -m "✅ test(api): adiciona testes de integração para alertas

Coverage:
- POST /analyze: 95%
- GET /alerts: 92%
- GET /alerts/{id}/justification: 88%

Total coverage: 91%"
```

---

## 🚫 Anti-Padrões (Evitar)

### ❌ Commits Ruins

```bash
# Muito vago
git commit -m "fix stuff"
git commit -m "updates"
git commit -m "changes"

# Sem emoji/tipo
git commit -m "adiciona api endpoint"

# Muito longo (>72 chars na primeira linha)
git commit -m "adiciona endpoint de análise de risco que processa licitações e emite alertas"

# Mistura de tipos
git commit -m "feat: adiciona API e corrige bug e atualiza docs"

# Typo no tipo
git commit -m "✨ feature: adiciona endpoint"  # 'feature' em vez de 'feat'
```

### ✅ Commits Bons (Corretos)

```bash
# Específico e claro
git commit -m "🐛 fix(api): corrige validação de CNPJ"

# Com emoji e tipo
git commit -m "✨ feat(ml): adiciona detecção de sobrepreço"

# Primeira linha curta
git commit -m "⚡ perf(db): otimiza query de alertas"

# Separa mudanças em commits
git commit -m "✨ feat(api): adiciona endpoint de análise"
git commit -m "🐛 fix(db): corrige migration de alertas"
git commit -m "📝 docs: atualiza API documentation"
```

---

## 🔀 Workflow de Commits

### Commits Atômicos

Cada commit deve conter **uma mudança lógica**:

```bash
# ❌ Ruim - mistura várias mudanças
git add .
git commit -m "feat: várias melhorias"

# ✅ Bom - commits separados
git add backend/app/api/endpoints/alerts.py
git commit -m "✨ feat(api): adiciona endpoint GET /alerts"

git add backend/app/services/alert_service.py
git commit -m "♻️ refactor(services): extrai lógica de alertas"

git add backend/tests/test_alerts.py
git commit -m "✅ test(api): adiciona testes para alertas"
```

### Commits Frequentes

Faça commits pequenos e frequentes:

```bash
# Durante desenvolvimento
git commit -m "🚧 wip: implementando análise de editais"
git commit -m "✨ feat(nlp): adiciona extração de cláusulas"
git commit -m "✅ test(nlp): testa extração de cláusulas"
git commit -m "📝 docs(nlp): documenta pipeline de análise"
```

---

## 📚 Referências Rápidas

### Tabela de Emojis mais Usados

| Emoji | Código | Uso |
|-------|--------|-----|
| ✨ | `:sparkles:` | Nova feature |
| 🐛 | `:bug:` | Bug fix |
| 📝 | `:memo:` | Documentação |
| ♻️ | `:recycle:` | Refatoração |
| ⚡ | `:zap:` | Performance |
| 🎨 | `:art:` | Estrutura/formato |
| 🔥 | `:fire:` | Remove código |
| ✅ | `:white_check_mark:` | Testes |
| 🔒 | `:lock:` | Segurança |
| ⬆️ | `:arrow_up:` | Upgrade deps |
| ⬇️ | `:arrow_down:` | Downgrade deps |
| 🔧 | `:wrench:` | Config |
| 🌐 | `:globe_with_meridians:` | i18n |
| 💄 | `:lipstick:` | UI/Style |
| 🚀 | `:rocket:` | Deploy |
| 🐳 | `:whale:` | Docker |

### Template de Commit Completo

```bash
git commit -m "✨ feat(escopo): descrição curta (max 72 chars)

Corpo do commit explicando o contexto e motivação da mudança.
Pode ter múltiplas linhas.

- Lista de mudanças importantes
- Outra mudança
- Mais uma

Refs: #123, #456
Fixes: #789

BREAKING CHANGE: Descrição do breaking change se aplicável"
```

---

## 🛠️ Ferramentas

### Pre-commit Hook

O projeto já tem pre-commit configurado que valida:
- ✅ Linting (ruff)
- ✅ Formatação (ruff-format)
- ✅ Type checking (mypy)
- ✅ Trailing whitespace
- ✅ YAML syntax

### Commitizen (Opcional)

Para ajudar na criação de commits:

```bash
# Instalar
pip install commitizen

# Usar
cz commit

# Gera commit interativo seguindo convenções
```

### Commitlint (Opcional)

Para validar mensagens de commit:

```bash
# .commitlintrc.json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]
    ]
  }
}
```

---

## 🔍 Verificação Antes do Commit

Antes de fazer commit, verifique:

- [ ] Commit é atômico (uma mudança lógica)
- [ ] Mensagem segue formato `<emoji> <tipo>(<escopo>): <descrição>`
- [ ] Descrição é clara e concisa (<72 chars)
- [ ] Emoji corresponde ao tipo de mudança
- [ ] Tipo está correto (feat, fix, docs, etc.)
- [ ] Pre-commit hooks passaram
- [ ] Testes estão passando (`make test`)
- [ ] Código está formatado (`make format`)

---

## 📖 Exemplos do Projeto

### Histórico Real

```bash
# Commits recentes do projeto
7eaaaa4 ♻️  docs: Revisão de documentação
e0d7207 📝 docs: remove referência à CGU
4d4b2af 📝 docs: update day 1 log with comprehensive accomplishments summary
1329bc3 🔧 chore: enhance Makefile with improved test commands
1ef3f15 ✅ test: configure pytest with fixtures and coverage
0982d6a 📝 docs: add documentation index and navigation guide
f864e73 📝 docs: add comprehensive technology decisions
```

### Padrões do Projeto

Commits recentes mostram bom uso de:
- ✅ Emojis consistentes
- ✅ Tipos apropriados
- ✅ Descrições claras
- ✅ Commits atômicos

---

## 🎓 Recursos

### Conventional Commits
- Spec: https://www.conventionalcommits.org/
- Exemplos: https://www.conventionalcommits.org/en/v1.0.0/#examples

### Gitmoji
- Site: https://gitmoji.dev/
- Lista completa: https://gitmoji.dev/#search

### Commitizen
- Docs: https://commitizen-tools.github.io/commitizen/

---

## 🔄 Revisão deste Guia

Este guia deve ser revisado quando:
1. Novos padrões forem adotados pela equipe
2. Ferramentas de automação mudarem
3. Feedback da equipe sobre melhorias

**Última atualização:** 22/10/2025
**Mantido por:** Equipe de Desenvolvimento

---

*Gov Contracts AI - Boas Práticas de Versionamento*
*Commits claros = Histórico compreensível = Projeto mantível*
