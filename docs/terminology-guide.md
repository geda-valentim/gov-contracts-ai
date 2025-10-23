# Guia de Terminologia Oficial - Gov Contracts AI

**Versão:** 1.0
**Data:** 22 de Outubro de 2025
**Baseado em:** Alice (CGU), TCU, NAT (Normas de Auditoria do Tribunal)

---

## 📌 Objetivo

Este documento define a terminologia oficial utilizada no Gov Contracts AI, alinhada com as práticas da **Alice (Analisador de Licitações, Contratos e Editais)** da CGU e órgãos de controle.

**Princípio fundamental:** O sistema é uma ferramenta de **apoio à análise de riscos**, não substitui o julgamento humano e não emite acusações diretas.

---

## ✅ Terminologia Aprovada

### Análise e Detecção

| ❌ Evitar | ✅ Usar | Contexto |
|-----------|---------|----------|
| Detecção de fraudes | **Análise de riscos** | Descrição do sistema |
| Fraud detection | **Risk analysis** | Documentação em inglês |
| Identificar fraudes | **Identificar fragilidades** | Objetivos do sistema |
| Licitação fraudulenta | **Licitação com alertas críticos** | Classificação de processos |
| Casos suspeitos | **Processos sinalizados** | Lista de resultados |

### Scoring e Classificação

| ❌ Evitar | ✅ Usar | Implementação |
|-----------|---------|---------------|
| `fraud_score` | **`risk_score`** | Variável de risco (0-1) |
| `is_fraud` | **`has_critical_alerts`** | Flag booleano |
| Fraud probability | **Nível de criticidade** | Descrição textual |
| Suspeita alta | **Criticidade alta** | Categorização |

### Alertas e Notificações

| Termo | Definição | Uso no Sistema |
|-------|-----------|----------------|
| **Alerta** | Notificação automática de risco identificado | "Sistema emitiu 120 alertas" |
| **Criticidade** | Nível de severidade do risco (baixa/média/alta/crítica) | "Alerta de criticidade alta" |
| **Fragilidade** | Ponto de vulnerabilidade no processo | "Identificadas 3 fragilidades" |
| **Risco** | Potencial de problema na contratação | "Risco de sobrepreço detectado" |
| **Fundamentação** | Justificativa técnica do alerta | "Fundamentação baseada em SHAP" |

### Tipos de Riscos (baseados na Alice/CGU)

| Tipo de Risco | Descrição | Exemplo |
|---------------|-----------|---------|
| **Sobrepreço** | Valores acima do praticado no mercado | "Preço 150% acima da mediana" |
| **Direcionamento** | Cláusulas que restringem competição | "Prazo de 3 dias para participação" |
| **Especificação inadequada** | Requisitos excessivos ou desnecessários | "Certificação rara não justificada" |
| **Inconsistência documental** | Erros ou omissões em documentos | "Valores divergentes entre edital e planilha" |
| **Desnecessidade** | Contratação sem justificativa clara | "Item duplicado em contrato vigente" |

### Resultados e Impacto

| ❌ Evitar | ✅ Usar | Justificativa |
|-----------|---------|---------------|
| Economia gerada | **Benefícios preventivos** | Não há certeza de economia |
| Fraude evitada | **Processo cancelado/ajustado** | Foco na ação, não acusação |
| Taxa de detecção | **Taxa de assertividade dos alertas** | Métrica de qualidade |
| Precisão na detecção | **Precisão na emissão de alertas** | Métrica técnica |

---

## 🎯 Frases Modelo

### Descrição do Sistema

**❌ Evitar:**
> "Sistema que detecta fraudes em licitações usando IA"

**✅ Usar:**
> "Sistema de análise de riscos em processos licitatórios com emissão automatizada de alertas preventivos"

### Objetivo Principal

**❌ Evitar:**
> "Identificar licitações fraudulentas com 85% de precisão"

**✅ Usar:**
> "Analisar processos licitatórios e emitir alertas de risco com 85% de precisão, priorizando casos críticos para atuação das equipes de controle"

### Resultados

**❌ Evitar:**
> "Detectamos 50 fraudes totalizando R$ 10 milhões"

**✅ Usar:**
> "Emitimos 50 alertas críticos sobre processos que totalizam R$ 10 milhões, permitindo atuação preventiva antes da homologação"

### Explicação de Alerta

**❌ Evitar:**
> "Esta licitação é fraudulenta porque..."

**✅ Usar:**
> "Este processo apresenta os seguintes riscos: [lista]. Recomenda-se análise detalhada pela equipe de controle."

---

## 📊 Níveis de Criticidade

Baseado na análise de risco (`risk_score` de 0 a 1):

| Nível | risk_score | Cor | Ação Recomendada |
|-------|-----------|-----|------------------|
| **Baixo** | 0.0 - 0.3 | 🟢 Verde | Monitoramento de rotina |
| **Médio** | 0.3 - 0.6 | 🟡 Amarelo | Análise mais detalhada |
| **Alto** | 0.6 - 0.8 | 🟠 Laranja | Priorizar para revisão |
| **Crítico** | 0.8 - 1.0 | 🔴 Vermelho | Atuação preventiva imediata |

---

## 🔍 Fundamentação de Alertas

Toda emissão de alerta deve incluir:

1. **Tipo de risco identificado** (sobrepreço, direcionamento, etc.)
2. **Evidências quantitativas** (valores SHAP, comparações)
3. **Evidências qualitativas** (análise do edital via LLM)
4. **Processos similares** (RAG - casos comparáveis)
5. **Recomendação** (ação sugerida para equipe de controle)

### Exemplo de Fundamentação

```
ALERTA DE CRITICIDADE ALTA

Processo: Pregão Eletrônico 001/2025
Órgão: Prefeitura Municipal de [Nome]
Objeto: Aquisição de notebooks
Valor: R$ 500.000,00

RISCOS IDENTIFICADOS:

1. SOBREPREÇO (Criticidade: Alta)
   - Valor unitário: R$ 4.800,00
   - Mediana de mercado: R$ 3.200,00
   - Desvio: +50%
   - Fonte: Análise de 120 processos similares

2. DIRECIONAMENTO (Criticidade: Média)
   - Prazo para participação: 4 dias
   - Referência: NAT recomenda mínimo 8 dias
   - Especificação de marca específica detectada (item 3.2)

FUNDAMENTAÇÃO TÉCNICA:
- Modelo ML: risk_score = 0.87 (crítico)
- Features principais (SHAP): preço_vs_mercado (+0.45), prazo_curto (+0.25)
- Análise LLM: Identificadas 2 cláusulas potencialmente restritivas

PROCESSOS SIMILARES:
- [Link] Pregão 045/2024 - mesmo órgão, sobrepreço confirmado
- [Link] Pregão 132/2024 - especificação similar, ajustado após alerta

RECOMENDAÇÃO:
Sugerimos análise detalhada do processo, com atenção especial para:
- Justificativa dos valores estimados
- Ampliação do prazo de participação
- Revisão das especificações técnicas (item 3.2)
```

---

## 🚫 Termos a Evitar Completamente

| Termo | Por quê evitar | Alternativa |
|-------|----------------|-------------|
| Fraude | Acusação legal, requer prova judicial | Risco, fragilidade, alerta |
| Fraudulento | Presume má-fé | Com alertas críticos |
| Corrupto | Acusação criminal | Processo com riscos |
| Ilegal | Juízo legal definitivo | Não conforme, irregular |
| Culpado | Presume responsabilidade | Órgão responsável pelo processo |
| Suspeito | Conotação policial | Sinalizado, com alertas |

---

## 📝 Variáveis e Campos no Código

### Banco de Dados

```sql
-- ✅ Nomenclatura aprovada
CREATE TABLE procurement_analysis (
    id SERIAL PRIMARY KEY,
    process_id VARCHAR(50),
    risk_score DECIMAL(3,2),           -- 0.00 a 1.00
    alert_level VARCHAR(20),            -- 'low', 'medium', 'high', 'critical'
    has_critical_alerts BOOLEAN,
    alert_types TEXT[],                 -- ['overpricing', 'restrictive_clauses']
    justification TEXT,                 -- Fundamentação do alerta
    recommended_action TEXT,            -- Ação recomendada
    analyzed_at TIMESTAMP
);
```

### API Endpoints

```python
# ✅ Nomenclatura aprovada
@app.post("/api/v1/analyze")
async def analyze_procurement(request: AnalysisRequest):
    """Analisa processo licitatório e emite alertas de risco"""
    pass

@app.get("/api/v1/alerts")
async def list_alerts(
    min_risk_score: float = 0.0,
    alert_level: str = None
):
    """Lista alertas emitidos com filtros"""
    pass

@app.get("/api/v1/alerts/{process_id}/justification")
async def get_alert_justification(process_id: str):
    """Retorna fundamentação detalhada do alerta"""
    pass
```

### Frontend

```typescript
// ✅ Nomenclatura aprovada
interface ProcurementAlert {
  processId: string;
  riskScore: number;            // 0-1
  alertLevel: 'low' | 'medium' | 'high' | 'critical';
  alertTypes: RiskType[];
  justification: string;
  recommendedAction: string;
}

type RiskType =
  | 'overpricing'
  | 'restrictive_clauses'
  | 'inadequate_specification'
  | 'document_inconsistency'
  | 'unjustified_need';
```

---

## 🎓 Referências Oficiais

### Documentos Base

1. **Alice (CGU)** - Analisador de Licitações, Contratos e Editais
   - Descrição oficial: "Identifica possíveis falhas que possam comprometer os objetivos do processo licitatório"
   - Terminologia: alertas, riscos, fragilidades, atuação preventiva

2. **TCU** - Normas de Auditoria do Tribunal
   - NAT: Terminologia oficial de auditoria governamental
   - Conceitos: achados, evidências, recomendações

3. **CGU** - Controladoria-Geral da União
   - Manual de Auditoria: Classificação de riscos
   - Guia de Controle Interno: Níveis de criticidade

### Links

- Alice: https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice
- TCU NAT: https://portal.tcu.gov.br/normas-e-jurisprudencia/
- CGU Manuais: https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao

---

## 🔄 Atualização deste Guia

Este guia deve ser atualizado quando:

1. Nova terminologia for adotada pela CGU/TCU
2. Alterações regulatórias relevantes
3. Feedback de órgãos de controle usuários do sistema
4. Evolução das funcionalidades do sistema

**Responsável:** Equipe de Desenvolvimento
**Revisão:** Trimestral
**Última atualização:** 22/10/2025

---

## ✅ Checklist de Conformidade

Antes de publicar documentação ou código, verifique:

- [ ] Não usa o termo "fraude" ou derivados
- [ ] Usa "risco", "alerta", "fragilidade" apropriadamente
- [ ] Variáveis seguem padrão `risk_score`, `alert_level`
- [ ] Descrições focam em análise, não acusação
- [ ] Inclui fundamentação clara dos alertas
- [ ] Recomenda ação humana, não decisão automática
- [ ] Linguagem técnica e objetiva
- [ ] Alinhado com terminologia da Alice (CGU)

---

*Gov Contracts AI - Análise de Riscos em Licitações*
*Sistema de apoio à atuação preventiva em processos licitatórios*
