# Gov Contracts AI - Product Requirements Document (PRD)
## Sistema de Análise de Riscos e Alertas em Licitações Governamentais

**Versão:** 2.2
**Data:** 22 de Outubro de 2025
**Status:** Aprovado para Implementação
**Licença:** GPL v3.0 (Software Livre)
**Autor:** Gabriel (ML/AI Engineer)

---

## 📋 Índice

1. [Visão Geral](#1-visão-geral)
2. [Objetivos e Métricas de Sucesso](#2-objetivos-e-métricas-de-sucesso)
3. [Contexto e Problema](#3-contexto-e-problema)
4. [Personas e Stakeholders](#4-personas-e-stakeholders)
5. [Requisitos Funcionais](#5-requisitos-funcionais)
6. [Requisitos Não-Funcionais](#6-requisitos-não-funcionais)
7. [Arquitetura Técnica](#7-arquitetura-técnica)
8. [Tech Stack](#8-tech-stack)
9. [Cronograma e Fases](#9-cronograma-e-fases)
10. [Riscos e Mitigação](#10-riscos-e-mitigação)
11. [Métricas e KPIs](#11-métricas-e-kpis)
12. [Roadmap Futuro](#12-roadmap-futuro)

---

## 1. Visão Geral

### 1.1 Elevator Pitch

**Gov Contracts AI** é uma plataforma open source de auditoria automatizada em licitações governamentais brasileiras, combinando Machine Learning tradicional (XGBoost) com IA Generativa (Llama 3.1) para identificar achados de auditoria, padrões suspeitos e gerar explicações em linguagem natural das irregularidades encontradas.

### 1.2 Proposta de Valor

```
┌────────────────────────────────────────────────────────────────┐
│  PROBLEMA                                                      │
│  • R$ 100+ bilhões perdidos em irregularidades/ano (TCU)      │
│  • Auditores sobrecarregados (análise manual)                 │
│  • Identificação tardia de irregularidades                    │
│  • Editais direcionados difíceis de identificar               │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│  SOLUÇÃO                                                       │
│  • Auditoria automatizada de 50k+ licitações                  │
│  • Análise proativa (antes da homologação)                    │
│  • Explicações em português sobre irregularidades             │
│  • 100% open source (auditável, transparente)                 │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│  IMPACTO                                                       │
│  • 85%+ precisão nos achados de auditoria                     │
│  • Economia estimada: R$ 50M+/ano (se adotado)                │
│  • Redução 90% do tempo de análise                            │
│  • Priorização inteligente para auditores                     │
└────────────────────────────────────────────────────────────────┘
```

### 1.3 Diferenciação

| Aspecto | Soluções Existentes | Gov Contracts AI |
|---------|---------------------|------------------|
| **Open Source** | ❌ Proprietário | ✅ GPL v3.0 |
| **Soberania** | ❌ Cloud externas | ✅ On-premises |
| **IA Generativa** | ❌ Apenas ML | ✅ LLM + ML híbrido |
| **Editais PDF** | ❌ Não analisa | ✅ NLP avançado |
| **Preços Mercado** | ❌ Sem referência | ✅ Web scraping |
| **Explicabilidade** | ⚠️ Básica | ✅ SHAP + LLM |
| **Custo** | 💰 Alto | ✅ Zero licenças |

---

## 2. Objetivos e Métricas de Sucesso

### 2.1 Objetivo Principal

**Gerar achados de auditoria automatizados em licitações com 85%+ de precisão, priorizando casos críticos para investigação humana.**

### 2.2 Objetivos Secundários

1. **Transparência:** Sistema auditável e explicável
2. **Eficiência:** Analisar 500+ licitações/dia automaticamente
3. **Proatividade:** Alertar antes da homologação (saving potential)
4. **Escalabilidade:** Suportar 500k+ licitações históricos
5. **Soberania:** Zero dependência de clouds externas

### 2.3 Métricas de Sucesso (6 meses)

| Métrica | Meta | Método de Medição |
|---------|------|-------------------|
| **Precision** | ≥ 85% | Validação manual top 100 |
| **Recall** | ≥ 70% | Casos confirmados vs detectados |
| **F1-Score** | ≥ 0.75 | Harmonic mean P/R |
| **Throughput** | 500 licitações/dia | Logs Airflow |
| **Latência API** | < 200ms p95 | Prometheus metrics |
| **Uptime** | > 99% | Grafana dashboards |
| **TCO** | < R$ 5k/mês | Custos infraestrutura |

### 2.4 Success Criteria (Adoption)

**MVP Success (Mês 3):**
- ✅ Sistema rodando 24/7
- ✅ 10k+ licitações analisadas
- ✅ 50+ casos suspeitos identificados
- ✅ 20+ casos validados manualmente
- ✅ Dashboard funcional

**Production Success (Mês 6):**
- ✅ 50k+ licitações no sistema
- ✅ 85%+ precision confirmada
- ✅ API pública documentada
- ✅ Código 100% open source
- ✅ 1+ artigo técnico publicado

---

## 3. Contexto e Problema

### 3.1 Contexto Brasil

**Volume de Licitações (2024):**
- Federal: ~15k/ano
- Estadual: ~50k/ano
- Municipal: ~500k/ano
- **Total: ~565k licitações/ano**

**Valor Total:**
- R$ 500+ bilhões em contratos públicos/ano
- R$ 100+ bilhões estimados em fraudes (20%)

**Tipos de Irregularidades Comuns (Achados de Auditoria):**

```
┌─────────────────────────────────────────────────────────────┐
│  1. SOBREPREÇO (40% dos casos)                             │
│  └─ Preços 2-3x acima do mercado                           │
│     Exemplo: Notebook i5 por R$ 12k (mercado: R$ 3.5k)     │
│                                                             │
│  2. DIRECIONAMENTO (30%)                                    │
│  └─ Edital com cláusulas restritivas                       │
│     • Prazo < 5 dias                                        │
│     • Marca específica citada                               │
│     • Certificações raras exigidas                          │
│                                                             │
│  3. CONLUIO (15%)                                           │
│  └─ Cartel entre empresas                                   │
│     • Mesmos sócios em empresas "concorrentes"             │
│     • Rodízio de vitórias                                   │
│     • Preços idênticos em propostas                         │
│                                                             │
│  4. SUPERFATURAMENTO (10%)                                  │
│  └─ Aditivos contratuais excessivos                        │
│     Exemplo: Contrato R$ 1M → R$ 5M em aditivos            │
│                                                             │
│  5. IRREGULARIDADE DOCUMENTAL (5%)                          │
│  └─ Documentos incompletos, inconsistências                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Problema Atual

**Análise Manual:**
- ⏱️ 2-4 horas/licitação (auditor experiente)
- 👥 Equipes de auditoria sobrecarregadas (~565k licitações/ano)
- 📊 Cobertura: < 1% analisado
- 🎯 Sem priorização inteligente

**Limitações Técnicas:**
- ❌ Editais em PDF (não estruturados)
- ❌ Falta de preços de referência atualizados
- ❌ Dados espalhados em múltiplas APIs
- ❌ Sem análise de redes de empresas

### 3.3 Oportunidade

```
┌─────────────────────────────────────────────────────────────┐
│  DADOS PÚBLICOS DISPONÍVEIS                                 │
├─────────────────────────────────────────────────────────────┤
│  ✅ Portal da Transparência (API REST)                      │
│  ✅ PNCP - Plataforma Nacional (API REST)                   │
│  ✅ Receita Federal (CNPJ bulk download)                    │
│  ✅ CEIS/CNEP (empresas punidas)                            │
│  ✅ TCU (auditorias anteriores)                             │
│  ✅ Editais PDF (links públicos)                            │
│  ✅ Preços Mercado (APIs Mercado Livre, etc)                │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│  TECNOLOGIAS MADURAS                                         │
├─────────────────────────────────────────────────────────────┤
│  ✅ XGBoost (SOTA para dados tabulares)                     │
│  ✅ Llama 3.1 (LLM open source local)                       │
│  ✅ OpenSearch (full-text + semantic search)                │
│  ✅ Docling (PDF → structured data)                         │
│  ✅ Airflow (orquestração)                                  │
└─────────────────────────────────────────────────────────────┘
              ↓
     🚀 SOLUÇÃO VIÁVEL
```

---

## 4. Personas e Stakeholders

### 4.1 Personas Primárias

#### **P1: Ana - Auditora do TCU**
```
Perfil:
├─ Idade: 35 anos
├─ Experiência: 10 anos em auditoria
├─ Formação: Direito + Especialização Controle
└─ Tech-savviness: Médio

Dores:
├─ Sobrecarga: 500+ processos na fila
├─ Priorização: Não sabe por onde começar
├─ Tempo: 80% gasto lendo editais manualmente
└─ Evidências: Difícil encontrar jurisprudência

Necessidades:
├─ Lista priorizada de casos suspeitos
├─ Evidências claras e explicáveis
├─ Comparação automática de preços
└─ Acesso a contratos similares

Como o sistema ajuda:
✅ Dashboard com top 100 suspeitas (risk_score)
✅ Explicação em português de cada irregularidade
✅ Comparação automática com mercado
✅ Busca semântica de editais similares
```

#### **P2: Carlos - Gestor de Compras Municipal**
```
Perfil:
├─ Idade: 42 anos
├─ Cargo: Secretário de Administração
├─ Experiência: 15 anos setor público
└─ Tech-savviness: Baixo

Dores:
├─ Pressão: Precisa homologar rápido
├─ Risco: Medo de aprovar licitação irregular
├─ Benchmarking: Não sabe preços de mercado
└─ Compliance: Editais com cláusulas questionáveis

Necessidades:
├─ Alertas proativos antes de homologar
├─ Preços de referência atualizados
├─ Validação automática de editais
└─ Relatórios simples para prestação de contas

Como o sistema ajuda:
✅ API: POST /validate_edital → score restritivo
✅ Preços de referência por categoria
✅ Flags automáticos (prazo curto, marca específica)
✅ Relatório PDF para justificar decisões
```

#### **P3: Júlia - Jornalista Investigativa**
```
Perfil:
├─ Idade: 28 anos
├─ Meio: Portal de notícias
├─ Experiência: 5 anos cobrindo corrupção
└─ Tech-savviness: Alto

Dores:
├─ Fontes: Difícil obter dados estruturados
├─ Análise: Não tem ferramentas técnicas
├─ Patterns: Redes de corrupção invisíveis
└─ Tempo: Deadlines apertados

Necessidades:
├─ Exportação de dados (CSV, JSON)
├─ Visualizações prontas (grafos, rankings)
├─ API pública para investigações
└─ Casos com maior impacto jornalístico

Como o sistema ajuda:
✅ API pública REST (GET /contracts?risk_score>0.9)
✅ Exports em múltiplos formatos
✅ Grafos de redes de empresas (futuro v2.0)
✅ Ranking por valor total (maior impacto)
```

### 4.2 Stakeholders Secundários

- **Desenvolvedores Open Source:** Código GPL, docs técnicas
- **Pesquisadores Acadêmicos:** Datasets, papers, metodologia
- **Ministério Público:** Evidências para processos
- **Cidadãos:** Transparência, dados abertos

---

## 5. Requisitos Funcionais

### 5.1 RF-001: Coleta Automatizada de Dados

**Descrição:** Sistema deve coletar diariamente dados de múltiplas fontes governamentais e comerciais.

**Fontes:**
1. **Portal da Transparência** (API REST)
   - Endpoint: `/api/licitacoes`
   - Frequência: Diária (2 AM)
   - Volume: ~500 licitações/dia

2. **PNCP** (API REST)
   - Endpoint: `/pncp-api/v1/contratos`
   - Frequência: Diária (2 AM)
   - Volume: ~500 licitações/dia

3. **Receita Federal - CNPJ**
   - Método: Bulk download mensal
   - Volume: ~5M empresas ativas

4. **CEIS/CNEP**
   - Método: Download mensal
   - Volume: ~10k empresas punidas

5. **Editais PDF**
   - Via: Links das APIs acima
   - Processamento: Ingestify.ai
   - Volume: ~500 PDFs/dia

6. **Preços Mercado**
   - Mercado Livre (API oficial)
   - Magazine Luiza (API)
   - Amazon (scraping)
   - Frequência: Semanal
   - Volume: ~10k produtos/semana

**Acceptance Criteria:**
- [ ] DAG Airflow executando 2 AM daily
- [ ] Logs de sucesso/falha por fonte
- [ ] Retry automático (3x) em caso de falha
- [ ] Alertas Slack se falha > 3x
- [ ] Dados salvos em Bronze layer (Parquet)

### 5.2 RF-002: Processamento de Editais PDF

**Descrição:** Extrair texto estruturado e tabelas de editais PDF usando Ingestify.ai.

**Workflow:**
```
1. Download PDF (via PNCP link)
2. POST /upload para Ingestify.ai
3. Aguardar processamento (polling ou webhook)
4. GET /document/{job_id} para obter resultado
5. Salvar JSON estruturado no Bronze
```

**Processamento Ingestify.ai:**
- Engine: **Docling (rule-based, não Granite)**
- OCR: Tesseract (se necessário)
- Workers: 12 paralelo (i5 threads)
- Timeout: 10 min/edital
- Output: JSON com:
  - `texto_completo`
  - `secoes` (objeto, habilitação, julgamento)
  - `tabelas` (itens, valores)
  - `entidades` (valores, datas, CNPJs)

**Acceptance Criteria:**
- [ ] 95%+ accuracy em texto (vs manual)
- [ ] 90%+ accuracy em tabelas simples
- [ ] 70%+ accuracy em tabelas complexas
- [ ] < 1 min de processamento médio/edital
- [ ] Suporte a OCR quando necessário

### 5.3 RF-003: Análise de Editais (Cláusulas Restritivas)

**Descrição:** Detectar cláusulas direcionadas ou restritivas em editais.

**Regras (Rule-Based):**
1. **Prazo Curto:** < 5 dias → flag_prazo_curto
2. **Marca Específica:** Regex detecta marcas → flag_marca_especifica
3. **Certificações Raras:** Lista de certs → flag_requisitos_excessivos
4. **Valores Inconsistentes:** Item sem preço → flag_valores_inconsistentes

**Score:** `score_restritivo_regras = sum(flags) / total_flags`

**LLM Analysis (Llama 3.1):**
- Prompt: "Analise este edital e identifique cláusulas potencialmente direcionadas"
- Output: JSON com problemas + severidade
- Score: `score_restritivo_llm = 0-1`

**Score Final:**
```python
score_restritivo_final = (
    0.7 * score_restritivo_regras +
    0.3 * score_restritivo_llm
)
```

**Acceptance Criteria:**
- [ ] Análise completa em < 60s/edital
- [ ] Identificar 80%+ cláusulas restritivas (vs manual)
- [ ] JSON estruturado com problemas + evidências
- [ ] Batch processing (500 editais/dia)

### 5.4 RF-004: Feature Engineering (30+ Features)

**Descrição:** Gerar features para ML a partir de dados integrados.

**Grupos de Features:**

```python
# 1. PREÇO (8 features)
- log_valor_total
- preco_vs_media_categoria
- preco_vs_mediana_categoria
- zscore_preco
- percentile_preco
- preco_vs_mercado  # NEW: comparação com marketplace
- preco_vs_p95_mercado
- desvio_preco_historico_orgao

# 2. TEMPORAL (6 features)
- dia_semana
- mes
- trimestre
- ano
- dias_duracao
- dias_ate_inicio

# 3. EMPRESA (8 features)
- num_licitacoes_anteriores
- valor_total_historico
- taxa_vitoria
- tempo_desde_fundacao
- num_socios
- capital_social
- flag_empresa_punida
- num_contratos_ativos

# 4. ÓRGÃO (5 features)
- num_licitacoes_orgao
- valor_medio_orgao
- taxa_suspeita_historica_orgao
- esfera_encoded (0=Fed, 1=Est, 2=Mun)
- regiao_encoded

# 5. MODALIDADE (3 features)
- modalidade_encoded
- tipo_licitacao_encoded
- criterio_julgamento_encoded

# 6. EDITAL (5 features) - NEW
- edital_score_restritivo
- edital_num_problemas
- edital_prazo_curto_flag
- edital_requisitos_excessivos_flag
- edital_marca_especifica_flag
```

**Acceptance Criteria:**
- [ ] 35+ features calculadas
- [ ] Sem nulls em features críticas
- [ ] Validação Great Expectations
- [ ] Parquet salvo em Gold layer
- [ ] < 30 min para 50k licitações

### 5.5 RF-005: Treinamento de Modelo ML

**Descrição:** Treinar modelo XGBoost para classificação binária (irregularidade/normal).

**Modelo:**
- Algoritmo: **XGBoost (CPU-optimized)**
- Alternativas: LightGBM, Random Forest (baselines)
- Hiperparâmetros: GridSearch com 5-fold CV

**Training Pipeline:**
```python
1. Load Gold features (Parquet)
2. Split: 70% train, 15% val, 15% test
3. Weak supervision para labels:
   - CEIS/CNEP → label=1 (irregularidade)
   - Auditoria TCU → label=1 se irregularidade
   - Score restritivo > 0.8 → label=1
   - Sobrepreço > 2x → label=1
4. Handle imbalance (SMOTE ou class_weight)
5. Train XGBoost
6. Evaluate: Precision, Recall, F1, ROC-AUC
7. SHAP explanations
8. Save to MLflow Registry
```

**Acceptance Criteria:**
- [ ] Precision ≥ 85% no test set
- [ ] Recall ≥ 70% no test set
- [ ] F1-Score ≥ 0.75
- [ ] ROC-AUC ≥ 0.85
- [ ] SHAP values para todas features
- [ ] Modelo versionado no MLflow

### 5.6 RF-006: Inferência e Scoring

**Descrição:** Aplicar modelo treinado em novas licitações diariamente.

**Workflow:**
```
1. Carrega features Gold do dia
2. Load modelo from MLflow (production tag)
3. Batch predict: audit_score = model.predict_proba()[:,1]
4. SHAP para top 100 suspeitas
5. Update PostgreSQL: licitacoes_gold.audit_score
6. Update OpenSearch: contratos_index.audit_score
```

**Acceptance Criteria:**
- [ ] Inferência em < 10 min para 500 licitações
- [ ] SHAP top 5 features por contrato
- [ ] Scores salvos em DB + OpenSearch
- [ ] Pipeline Airflow diário (5 AM)

### 5.7 RF-007: Geração de Explicações (LLM)

**Descrição:** Gerar explicações em português para casos suspeitos usando Llama 3.1.

**Critério de Seleção:**
- `audit_score > 0.8` (top achados)
- Limit: 20 explicações/dia (LLM é lento)

**Prompt Template:**
```
Contexto:
- Licitação: {numero_licitacao}/{ano}
- Órgão: {orgao_nome}
- Valor: R$ {valor_total:,.2f}
- Empresa: {empresa_nome}
- Audit Score: {audit_score:.2f}

SHAP Top 5 Features:
{shap_values}

Edital Analysis:
{edital_problemas}

Contratos Similares (RAG):
{similar_contracts}

TASK: Explique em 2-3 parágrafos os achados de auditoria desta licitação.
Use linguagem clara, cite evidências, recomende próximos passos.
```

**Acceptance Criteria:**
- [ ] Explicações em português natural
- [ ] Cita evidências específicas (SHAP, edital)
- [ ] Recomenda ação (investigar/monitorar/aprovar)
- [ ] < 15s por explicação
- [ ] Salva em PostgreSQL: licitacoes_gold.explanation_text

### 5.8 RF-008: Busca Semântica (OpenSearch + Embeddings)

**Descrição:** Permitir busca por contratos similares usando embeddings.

**Modelo de Embeddings:**
- **multilingual-e5-small (384 dims)**
- Alternativas rejeitadas: BERTimbau (768), e5-base (768)
- Justificativa: 2x mais rápido, metade storage, 95% qualidade

**Indexação:**
```python
1. Encode texto_completo com e5-small
2. Batch: 32 editais/vez
3. Store em OpenSearch: contratos_index.embedding
4. Indexação k-NN (HNSW):
   - space_type: cosinesimil
   - ef_construction: 128
   - m: 24
```

**Query API:**
```python
POST /api/search/similar
{
  "licitacao_id": "123456",  # ou
  "query_text": "contratação de notebooks",
  "top_k": 10
}

# Retorna: 10 contratos mais similares (score 0-1)
```

**Acceptance Criteria:**
- [ ] Índice de 50k contratos em < 1h
- [ ] Query < 200ms p95
- [ ] Recall@10 ≥ 80% (vs ground truth)
- [ ] Suporte a full-text + semantic search

### 5.9 RF-009: API REST

**Descrição:** Expor funcionalidades via API REST documentada (OpenAPI 3.0).

**Endpoints:**

```python
# CONSULTA DE CONTRATOS
GET /api/contracts
  ?audit_score_min=0.8
  &limit=100
  &offset=0
  &sort_by=audit_score
  &order=desc

GET /api/contracts/{licitacao_id}
  # Retorna: contrato + audit_score + explanation + SHAP

# BUSCA
GET /api/search/text?q=notebook
POST /api/search/similar
  Body: {licitacao_id: "123456", top_k: 10}

# VALIDAÇÃO DE EDITAIS
POST /api/edital/analyze
  Body: {pdf_file: <binary>}
  # Retorna: score_restritivo + problemas + flags

# PREÇOS DE REFERÊNCIA
GET /api/prices/reference?categoria=ti&item=notebook

# ESTATÍSTICAS
GET /api/stats/summary
GET /api/stats/by-orgao
GET /api/stats/by-modalidade

# EXPORTAÇÃO
GET /api/export/contracts?format=csv&audit_score_min=0.8
```

**Autenticação:**
- JWT tokens
- Rate limiting: 100 req/min (public), 1000 req/min (authenticated)

**Acceptance Criteria:**
- [ ] OpenAPI 3.0 docs (Swagger UI)
- [ ] Todos endpoints < 200ms p95
- [ ] CORS habilitado
- [ ] Logs estruturados (JSON)
- [ ] Prometheus metrics

### 5.10 RF-010: Dashboard Web

**Descrição:** Interface web para visualização e análise de licitações suspeitas.

**Páginas:**

```
1. HOME / OVERVIEW
   ├─ KPIs: Total contratos, % suspeitas, valor total
   ├─ Gráficos: Timeline, top órgãos, top modalidades
   └─ Top 10 suspeitas (cards com score)

2. LISTA DE CONTRATOS
   ├─ Tabela paginada (filtros: score, órgão, valor, data)
   ├─ Sort por qualquer coluna
   └─ Click → abre detalhe

3. DETALHE DO CONTRATO
   ├─ Info básica (órgão, empresa, valor, datas)
   ├─ Audit Score (gauge 0-1)
   ├─ SHAP Waterfall Chart
   ├─ Explicação LLM (texto)
   ├─ Edital analysis (problemas + flags)
   ├─ Comparação preços mercado
   ├─ Contratos similares (embedding search)
   └─ Download edital PDF

4. BUSCA AVANÇADA
   ├─ Full-text search
   ├─ Semantic search
   ├─ Filtros combinados
   └─ Exportação resultados

5. ANÁLISE DE EDITAL
   ├─ Upload PDF
   ├─ Processing status (polling)
   ├─ Resultado: score + problemas
   └─ Download relatório

6. ESTATÍSTICAS
   ├─ Dashboards interativos (Recharts)
   ├─ Distribuições (scores, valores, modalidades)
   └─ Time series
```

**Tech Stack:**
- Frontend: **Next.js 14** (App Router)
- UI: **Tailwind CSS + Radix UI**
- Charts: **Recharts**
- State: **Zustand** ou **TanStack Query**

**Acceptance Criteria:**
- [ ] Responsive (mobile, tablet, desktop)
- [ ] Lighthouse score > 90
- [ ] SSR para SEO
- [ ] Loading states + error boundaries
- [ ] Dark mode

---

## 6. Requisitos Não-Funcionais

### 6.1 RNF-001: Performance

| Métrica | Requisito | Medição |
|---------|-----------|---------|
| **API Latência (p50)** | < 100ms | Prometheus |
| **API Latência (p95)** | < 200ms | Prometheus |
| **API Latência (p99)** | < 500ms | Prometheus |
| **Throughput** | 1k req/min | Locust tests |
| **ML Inference** | 500 pred/dia | Airflow logs |
| **PDF Processing** | 500 editais/dia | Ingestify.ai logs |
| **Search Query** | < 200ms | OpenSearch metrics |
| **Dashboard Load** | < 3s (FCP) | Lighthouse |

### 6.2 RNF-002: Escalabilidade

**Capacidade Atual (Single Machine):**
- 50k-500k licitações
- Hardware: i5 + 48GB RAM + SSD 480GB + HDD 1.8TB

**Vertical Scaling (se > 500k):**
- RAM: 48GB → 128GB
- SSD: 480GB → 2TB
- HDD: 1.8TB → 8TB
- Capacidade: 500k → 2M licitações

**Horizontal Scaling (se > 2M):**
- Cluster Airflow (3-5 workers)
- PostgreSQL Master-Replica
- OpenSearch 3-node cluster
- Capacidade: 2M → 10M+ licitações

### 6.3 RNF-003: Disponibilidade

- **Uptime:** > 99% (SLA)
- **Backup:** Diário (PostgreSQL), Semanal (Gold layer)
- **Recovery:** RTO < 1h, RPO < 24h
- **Monitoring:** Grafana + Prometheus
- **Alerting:** Slack notifications

### 6.4 RNF-004: Segurança

- **Dados:** Não contêm informações sensíveis (tudo é público)
- **API:** JWT authentication, rate limiting
- **Network:** Firewall (apenas portas necessárias)
- **Logs:** Sem PII, rotação a cada 30 dias
- **Secrets:** Vault ou .env (nunca no código)

### 6.5 RNF-005: Auditabilidade

- **Código:** 100% open source (GitHub)
- **Logs:** Estruturados (JSON), searchable (OpenSearch)
- **Versionamento:** Git (código), DVC (dados), MLflow (modelos)
- **Reproducibilidade:** Docker Compose, seeds fixos
- **Documentação:** README, API docs, architecture diagrams

### 6.6 RNF-006: Soberania Tecnológica

- **On-premises:** Zero dependência de clouds externas
- **Open Source:** 100% software livre (Apache 2.0, MIT, GPL)
- **No Vendor Lock-in:** Sem licenças proprietárias
- **Dados Locais:** Tudo no servidor próprio

### 6.7 RNF-007: Usabilidade

- **Dashboard:** Intuitivo para não-técnicos
- **API:** Documentação clara (Swagger)
- **Explicações:** Português natural (não jargão)
- **Onboarding:** < 10 min para primeiros insights

---

## 7. Arquitetura Técnica

### 7.1 Visão Geral: Lakehouse Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    LAKEHOUSE ARCHITECTURE                      │
│                                                                │
│  Data Lake (MinIO S3)  +  Data Warehouse (PostgreSQL)  +  Search (OpenSearch) │
│    Object Storage              SSD                              SSD      │
│  S3-Compatible            Structured                       Searchable   │
│   ML Training            API Queries                     Semantic Search│
└────────────────────────────────────────────────────────────────┘
```

**Por Quê Lakehouse?**
- **Data Lake só:** Queries lentas, sem estrutura para APIs
- **Data Warehouse só:** Caro, inflexível, ruim para ML
- **Search Engine só:** Não é transacional, difícil para analytics
- **Lakehouse:** Melhor dos 3 mundos para este caso de uso

### 7.2 Medallion Architecture (Bronze → Silver → Gold)

```
FONTES EXTERNAS (APIs, PDFs, Scraping)
         ↓
🥉 BRONZE LAYER (Raw Data - MinIO S3)
├─ Storage: MinIO (S3-compatible object storage)
├─ Format: Parquet (snappy compression)
├─ Dados as-is (sem validação)
├─ Particionado por data (s3://bronze/year=2025/month=10/)
├─ Imutável (append-only)
├─ Versioning habilitado
└─ Retenção: Permanente

         ↓ Cleaning & Validation

🥈 SILVER LAYER (Clean Data - MinIO S3)
├─ Storage: MinIO (S3-compatible object storage)
├─ Format: Parquet (snappy compression)
├─ Validado (Great Expectations)
├─ Deduplicado
├─ Normalizado (tipos, formatos)
├─ Joined (múltiplas fontes)
├─ Particionado por data + categoria
└─ Retenção: Permanente

         ↓ Feature Engineering

🥇 GOLD LAYER (ML-Ready - Multi-storage)
├─ Analytics: Parquet em MinIO S3
│  ├─ 35+ features engineered
│  ├─ Otimizado para leitura (columnar)
│  └─ Cache local SSD para hot data
├─ Query Layer: PostgreSQL (SSD)
│  └─ Structured, indexed, transacional
└─ Search Layer: OpenSearch (SSD)
   └─ Full-text + semantic search + k-NN
```

### 7.3 Componentes Principais

```
┌────────────────────────────────────────────────────────────────┐
│                      SYSTEM COMPONENTS                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. DATA INGESTION                                             │
│  ├─ Airflow DAG: Bronze Ingestion (daily 2 AM)                │
│  ├─ APIs: Portal Transparência, PNCP                          │
│  ├─ Scraping: Mercado Livre, Magazine Luiza                   │
│  └─ Output: Bronze Parquet → MinIO S3 (s3://bronze/)          │
│                                                                │
│  2. PDF PROCESSING (Microservice)                             │
│  ├─ Ingestify.ai (FastAPI + Celery)                           │
│  ├─ Docling (rule-based extraction)                           │
│  ├─ Tesseract OCR (fallback)                                  │
│  ├─ Input: PDFs from MinIO S3                                 │
│  ├─ Storage: Processed JSON → MinIO S3 (s3://bronze/editais/) │
│  └─ Output: JSON (texto + tabelas + entidades)                │
│                                                                │
│  3. DATA CLEANING & VALIDATION                                │
│  ├─ Airflow DAG: Silver Processing                            │
│  ├─ Great Expectations (26+ checks)                           │
│  ├─ Deduplication, normalization                              │
│  ├─ Input: Bronze from MinIO S3 (s3://bronze/)                │
│  └─ Output: Silver Parquet → MinIO S3 (s3://silver/)          │
│                                                                │
│  4. EDITAL ANALYSIS                                            │
│  ├─ Rule-based detection (flags)                              │
│  ├─ NER: spaCy pt_core_news_lg                                │
│  ├─ LLM: Llama 3.1 8B Q4 (batch)                             │
│  └─ Output: score_restritivo + problemas                      │
│                                                                │
│  5. FEATURE ENGINEERING                                        │
│  ├─ Airflow DAG: Gold Features                                │
│  ├─ 35+ features (preço, temporal, empresa, edital)           │
│  ├─ Matching com preços mercado                               │
│  ├─ Input: Silver from MinIO S3 (s3://silver/)                │
│  └─ Output: Parquet → MinIO S3 (s3://gold/) + PostgreSQL      │
│                                                                │
│  6. EMBEDDINGS GENERATION                                      │
│  ├─ Model: multilingual-e5-small (384 dims)                   │
│  ├─ Batch: 32 editais/vez                                     │
│  ├─ Duration: ~33 min para 50k                                │
│  └─ Output: OpenSearch (k-NN index)                           │
│                                                                │
│  7. ML TRAINING                                                │
│  ├─ Model: XGBoost (CPU-optimized)                            │
│  ├─ Weak supervision para labels                              │
│  ├─ SHAP explainability                                       │
│  ├─ Input: Gold features from MinIO S3 (s3://gold/)           │
│  ├─ MLflow tracking + registry                                │
│  └─ Output: Model artifact → MLflow (stored in MinIO S3)      │
│                                                                │
│  8. ML INFERENCE                                               │
│  ├─ Airflow DAG: Batch Predict (daily 5 AM)                   │
│  ├─ XGBoost.predict_proba() → risk_score                     │
│  ├─ SHAP values (top 100)                                     │
│  └─ Output: PostgreSQL + OpenSearch updates                   │
│                                                                │
│  9. LLM EXPLANATIONS                                           │
│  ├─ Llama 3.1 8B Q4 (local, CPU)                             │
│  ├─ RAG: Similar contracts from OpenSearch                    │
│  ├─ Batch: 20 explicações/dia                                 │
│  └─ Output: explanation_text (PostgreSQL)                     │
│                                                                │
│  10. API REST                                                  │
│  ├─ FastAPI + SQLAlchemy (async)                              │
│  ├─ Endpoints: contracts, search, edital, prices, stats       │
│  ├─ Auth: JWT + rate limiting                                 │
│  └─ Docs: OpenAPI 3.0 (Swagger UI)                           │
│                                                                │
│  11. DASHBOARD WEB                                             │
│  ├─ Next.js 14 (App Router, SSR)                              │
│  ├─ UI: Tailwind CSS + Radix UI                               │
│  ├─ Charts: Recharts                                           │
│  └─ State: TanStack Query                                     │
│                                                                │
│  12. MONITORING & LOGGING                                      │
│  ├─ Metrics: Prometheus + Grafana                             │
│  ├─ Logs: OpenSearch (ELK pattern)                            │
│  └─ Alerts: Slack webhooks                                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 7.4 Fluxo de Dados End-to-End

```
DIA 0: Licitação Publicada (PNCP)
         ↓
DIA 1 - 02:00: Bronze Ingestion (30 min)
├─ Fetch licitações (Portal + PNCP)
├─ Download editais PDF
├─ Scrape preços mercado (weekly)
└─ Save: Bronze Parquet → MinIO S3 (s3://bronze/)

         ↓
DIA 1 - 02:35: PDF Processing (22 min)
├─ Ingestify.ai (Docling)
├─ Parallel: 12 workers
├─ Extract: texto + tabelas
└─ Save: JSON → MinIO S3 (s3://bronze/editais/) + OpenSearch index

         ↓
DIA 1 - 03:00: Silver Cleaning (55 min)
├─ Read: Bronze from MinIO S3
├─ Validate (Great Expectations)
├─ Deduplicate & normalize
├─ Parse editais (NER, regex)
├─ Analyze (rules + LLM)
└─ Save: Silver Parquet → MinIO S3 (s3://silver/)

         ↓
DIA 1 - 04:00: Gold Features (37 min)
├─ Read: Silver from MinIO S3
├─ Engineer 35+ features
├─ Match com preços mercado
├─ Generate embeddings (e5-small)
├─ Save: Parquet → MinIO S3 (s3://gold/)
└─ Update: PostgreSQL + OpenSearch

         ↓
DIA 1 - 04:40: ML Inference (12 min)
├─ Load XGBoost model (MLflow)
├─ Batch predict (risk_score)
├─ SHAP values (top 100)
├─ LLM explanations (top 20)
└─ Update: PostgreSQL + OpenSearch

         ↓
DIA 1 - 05:00: ✅ DISPONÍVEL PARA CONSULTA
├─ Dashboard: Top 100 suspeitas
├─ API: GET /contracts?risk_score>0.8
├─ OpenSearch: Semantic search
└─ PostgreSQL: Queries rápidas

TOTAL DURATION: ~3 horas (automático)
```

---

## 8. Tech Stack

### 8.1 Stack Completo (100% Open Source)

```
DATA LAYER
├─ MinIO (🆓 AGPL v3) - S3-compatible object storage
├─ PostgreSQL 16 (🆓 PostgreSQL License)
├─ OpenSearch 2.11+ (🆓 Apache 2.0)
├─ Redis 7 (🆓 BSD 3-Clause)
└─ Parquet Files in MinIO (🆓 Apache 2.0)

ORCHESTRATION
├─ Apache Airflow 2.8+ (🆓 Apache 2.0)
└─ Celery (🆓 BSD)

PDF PROCESSING
├─ Ingestify.ai (Custom microservice)
│  ├─ FastAPI (🆓 MIT)
│  ├─ Celery workers
│  ├─ Docling (🆓 MIT) - rule-based
│  └─ Tesseract OCR (🆓 Apache 2.0)
└─ Storage: MinIO S3-compatible (PDFs + JSON outputs)

MACHINE LEARNING
├─ XGBoost 2.0+ (🆓 Apache 2.0)
├─ Scikit-learn 1.4+ (🆓 BSD)
├─ SHAP 0.44+ (🆓 MIT)
├─ MLflow 2.10+ (🆓 Apache 2.0)
├─ DVC 3.0+ (🆓 Apache 2.0)
└─ Great Expectations 0.18+ (🆓 Apache 2.0)

AI GENERATIVA (Local)
├─ Ollama (🆓 MIT)
├─ Llama 3.1 8B Instruct Q4 (🆓 Meta License)
├─ multilingual-e5-small (🆓 MIT)
└─ spaCy pt_core_news_lg (🆓 MIT)

BACKEND
├─ FastAPI 0.109+ (🆓 MIT)
├─ SQLAlchemy 2.0 (🆓 MIT)
└─ Pydantic V2 (🆓 MIT)

FRONTEND
├─ Next.js 14 (🆓 MIT)
├─ TypeScript 5+ (🆓 Apache 2.0)
├─ Tailwind CSS 3.4+ (🆓 MIT)
├─ Radix UI (🆓 MIT)
└─ Recharts (🆓 MIT)

MONITORING
├─ Prometheus 2.48+ (🆓 Apache 2.0)
├─ Grafana 10+ (🆓 AGPL v3)
└─ OpenSearch (logs)

INFRASTRUCTURE
├─ Docker 24+ (🆓 Apache 2.0)
├─ Docker Compose (🆓 Apache 2.0)
└─ Nginx 1.24+ (🆓 BSD 2-Clause)
```

### 8.2 Decisões Técnicas Críticas

| Decisão | Escolhido | Alternativa Rejeitada | Justificativa |
|---------|-----------|----------------------|---------------|
| **Search Engine** | OpenSearch | Elasticsearch | License (Apache vs Elastic) |
| **Vector DB** | OpenSearch (built-in) | Qdrant standalone | Elimina redundância |
| **Embeddings** | multilingual-e5-small (384) | BERTimbau (768) | 2x mais rápido, metade storage |
| **PDF Processing** | Docling (rule-based) | Granite-Docling-258M | 10x mais rápido, CPU-friendly |
| **Data Lake Format** | Parquet | Delta Lake | Append-only (não precisa ACID) |
| **Object Storage** | Filesystem local | MinIO | Simplicidade v1.0 |
| **LLM** | Llama 3.1 8B Q4 | Claude/GPT API | Zero custo, soberania |
| **ML Model** | XGBoost (CPU) | Neural Networks (GPU) | Sem GPU, SOTA tabular |

---

## 9. Cronograma e Fases

### 9.1 Timeline Geral (5 meses = 20 semanas)

```
┌─────────────────────────────────────────────────────────────────┐
│  MONTH 1 (Semanas 1-4): Data Pipeline                          │
│  ├─ Bronze Layer (coleta de dados)                             │
│  ├─ Silver Layer (cleaning + validation)                        │
│  ├─ Ingestify.ai (PDF processing)                              │
│  └─ Airflow (orquestração)                                     │
│  Entregável: 10k licitações no Silver                          │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  MONTH 2 (Semanas 5-8): Feature Engineering + Gold             │
│  ├─ Gold Layer (features)                                       │
│  ├─ PostgreSQL schema                                           │
│  ├─ OpenSearch setup + embeddings                              │
│  └─ Preços mercado scraping                                    │
│  Entregável: 35+ features, embeddings indexados                │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  MONTH 3 (Semanas 9-12): Machine Learning                      │
│  ├─ Weak supervision (labels)                                   │
│  ├─ XGBoost training                                            │
│  ├─ SHAP explainability                                         │
│  ├─ MLflow setup                                                │
│  └─ Batch inference pipeline                                    │
│  Entregável: Modelo com 85%+ precision                         │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  MONTH 4 (Semanas 13-16): API + Dashboard                      │
│  ├─ FastAPI (endpoints)                                         │
│  ├─ Next.js dashboard                                           │
│  ├─ Llama 3.1 explicações                                       │
│  └─ Testes end-to-end                                           │
│  Entregável: Sistema funcional completo                        │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  MONTH 5 (Semanas 17-20): Production + Docs                    │
│  ├─ Monitoring (Grafana + Prometheus)                          │
│  ├─ Deploy final                                                │
│  ├─ Documentação técnica                                        │
│  ├─ Blog posts + artigo                                         │
│  └─ Portfolio presentation                                      │
│  Entregável: Sistema em produção + docs                        │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Detalhamento por Semana (Exemplo: Mês 1)

#### **Semana 1-2: Bronze Layer**
- [X] Setup ambiente (Docker Compose)
- [X] Configurar MinIO S3 (buckets: bronze/, silver/, gold/)
- [ ] DAG Bronze Ingestion (Portal + PNCP)
- [ ] Parquet storage (particionado)
- [ ] Coleta inicial: 5k licitações
- [ ] Logs estruturados

#### **Semana 3: Silver Layer**
- [ ] DAG Silver Processing
- [ ] Great Expectations (validação)
- [ ] Deduplication + normalization
- [ ] Join com CNPJ data

#### **Semana 4: PDF Processing**
- [ ] Setup Ingestify.ai (microservice)
- [ ] Integração Airflow ↔ Ingestify
- [ ] Docling configuration
- [ ] Processar 500 editais

### 9.3 Milestones

| Milestone | Data | Critério de Aceitação |
|-----------|------|-----------------------|
| **M1: Bronze Ready** | Semana 2 | 5k licitações coletadas |
| **M2: Silver Ready** | Semana 4 | 5k licitações validadas + 500 editais processados |
| **M3: Gold Ready** | Semana 8 | 35+ features, embeddings OK |
| **M4: Model Trained** | Semana 12 | 85%+ precision no test set |
| **M5: MVP Launch** | Semana 16 | Sistema funcional, dashboard live |
| **M6: Production** | Semana 20 | 50k licitações, monitoring, docs |

---

## 10. Riscos e Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **APIs governamentais instáveis** | Alta | Alto | Retry logic (3x), cache Redis, fallback manual |
| **PDFs ilegíveis (OCR falha)** | Média | Médio | Tesseract fallback, manual review queue |
| **Modelo com baixa precision** | Média | Alto | Weak supervision robusta, SMOTE, ensemble |
| **Hardware insuficiente** | Baixa | Alto | Vertical scaling (RAM/SSD), cloud migration |
| **Falta de labels** | Alta | Alto | Weak supervision multi-fonte, active learning |
| **Complexidade Airflow** | Média | Médio | Docs detalhadas, DAG templates, testes |
| **LLM lento (CPU)** | Média | Baixo | Batch processing, limit 20/dia, quantização Q4 |
| **Storage cheio** | Baixa | Médio | Monitoring, cleanup old files, HDD upgrade |

---

## 11. Métricas e KPIs

### 11.1 KPIs de Negócio

| KPI | Fórmula | Meta (6 meses) | Frequência |
|-----|---------|----------------|------------|
| **Taxa de Detecção** | Irregularidades identificadas / Total irregularidades | 85% | Mensal |
| **Economia Estimada** | Σ valor_licitacoes_com_achados | R$ 10M+ | Trimestral |
| **Coverage** | Licitações analisadas / Total disponível | 100% | Diário |
| **Tempo de Análise** | Média horas/licitação | < 5 min | Semanal |

### 11.2 KPIs Técnicos

| KPI | Meta | Medição |
|-----|------|---------|
| **Model Precision** | ≥ 85% | Test set (manual validation) |
| **Model Recall** | ≥ 70% | Test set |
| **API Uptime** | > 99% | Prometheus |
| **API Latency (p95)** | < 200ms | Prometheus |
| **Pipeline Success Rate** | > 95% | Airflow logs |
| **Data Quality Score** | > 90% | Great Expectations |

### 11.3 Dashboards de Monitoramento

**Grafana Dashboard 1: Operations**
- Pipeline status (Bronze/Silver/Gold)
- DAG success/failure rates
- Processing times (avg, p95, p99)
- Error logs (últimas 24h)

**Grafana Dashboard 2: ML Performance**
- Precision/Recall/F1 over time
- Audit score distribution
- SHAP feature importance
- Model drift detection

**Grafana Dashboard 3: Business Metrics**
- Total contratos analisados
- Taxa de irregularidades identificadas
- Valor total com achados de auditoria
- Top órgãos com irregularidades
- Top empresas com achados

---

## 12. Roadmap Futuro

### 12.1 Versão 2.0 (Mês 7-12)

**Análise de Redes:**
- Construir grafo de empresas + sócios
- Detectar conluios e cartéis
- Visualizações interativas (Gephi, Cytoscape)
- Features de grafo no ML (PageRank, betweenness)

**Expansão de Fontes:**
- Diários Oficiais (scraping)
- Dados TCU (auditorias passadas)
- Contratos firmados (execução)
- Aditivos contratuais

**ML Avançado:**
- Deep Learning para editais (Transformers)
- Fine-tuning Llama 3 com casos reais
- Active Learning (solicitar labels humanos)
- Detecção de anomalias multi-variadas

### 12.2 Versão 3.0 (Mês 13-18)

**Alertas Proativos:**
- Email/SMS para auditores
- Integração com sistemas de auditoria
- API pública para jornalistas

**Mobile App:**
- iOS/Android (React Native)
- Notificações push
- Offline mode

**Governança:**
- Sistema de feedback (auditor marca false positives)
- Re-treinamento automático
- A/B testing de modelos

---

## 13. Conclusão

Este PRD define um **sistema completo e viável** de auditoria automatizada em licitações governamentais, combinando:

✅ **Arquitetura Moderna:** Lakehouse (Lake + Warehouse + Search)
✅ **100% Open Source:** Zero vendor lock-in
✅ **ML + IA Híbrido:** XGBoost + Llama 3.1
✅ **Explicabilidade:** SHAP + LLM explanations
✅ **Escalabilidade:** 50k → 500k → 2M+ licitações
✅ **Soberania:** On-premises, sem clouds externas
✅ **Impacto Social:** Transparência, economia pública

**Next Steps:**
1. Aprovação dos stakeholders
2. Setup ambiente de desenvolvimento
3. Início da implementação (Mês 1 - Data Pipeline)

---

**Documento aprovado para implementação.**
**Versão:** 2.2
**Data:** 22 de Outubro de 2025

---

## Apêndices

### A. Glossário

- **Lakehouse:** Arquitetura que combina Data Lake + Data Warehouse
- **Medallion:** Padrão de camadas (Bronze/Silver/Gold)
- **Weak Supervision:** Labeling automático usando regras heurísticas
- **SHAP:** SHapley Additive exPlanations (explainability)
- **Embeddings:** Representações vetoriais de texto (semantic search)
- **RAG:** Retrieval-Augmented Generation (LLM + busca)

### B. Referências

1. Portal da Transparência: https://portaldatransparencia.gov.br
2. PNCP: https://pncp.gov.br
3. TCU Relatórios: https://portal.tcu.gov.br
4. Docling GitHub: https://github.com/DS4SD/docling
5. multilingual-e5: https://huggingface.co/intfloat/multilingual-e5-small
6. OpenSearch: https://opensearch.org

### C. Contato

**Autor:** Gabriel
**Role:** ML/AI Engineer
**GitHub:** [repositório do projeto]
**Email:** [contato]
**LinkedIn:** [perfil]
