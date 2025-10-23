"""
PNCP Domain: Natureza Jurídica.

Defines the legal nature of entities participating in procurement processes.
"""

from enum import Enum


class NaturezaJuridica(int, Enum):
    """
    Natureza jurídica da entidade.

    Reference: PNCP API Documentation - Section 5.13
    """

    # Não informado
    NAO_INFORMADA = 0
    NAO_INFORMADA_ALT = 8885

    # Poder Executivo
    EXECUTIVO_FEDERAL = 1015
    EXECUTIVO_ESTADUAL_DF = 1023
    EXECUTIVO_MUNICIPAL = 1031

    # Poder Legislativo
    LEGISLATIVO_FEDERAL = 1040
    LEGISLATIVO_ESTADUAL_DF = 1058
    LEGISLATIVO_MUNICIPAL = 1066

    # Poder Judiciário
    JUDICIARIO_FEDERAL = 1074
    JUDICIARIO_ESTADUAL = 1082

    # Autarquias
    AUTARQUIA_FEDERAL = 1104
    AUTARQUIA_ESTADUAL_DF = 1112
    AUTARQUIA_MUNICIPAL = 1120

    # Fundações Públicas de Direito Público
    FUNDACAO_PUBLICA_DIREITO_PUBLICO_FEDERAL = 1139
    FUNDACAO_PUBLICA_DIREITO_PUBLICO_ESTADUAL_DF = 1147
    FUNDACAO_PUBLICA_DIREITO_PUBLICO_MUNICIPAL = 1155

    # Órgãos Autônomos
    ORGAO_AUTONOMO_FEDERAL = 1163
    ORGAO_AUTONOMO_ESTADUAL_DF = 1171
    ORGAO_AUTONOMO_MUNICIPAL = 1180

    # Outros entes públicos
    COMISSAO_POLINACIONAL = 1198
    CONSORCIO_PUBLICO_DIREITO_PUBLICO = 1210
    CONSORCIO_PUBLICO_DIREITO_PRIVADO = 1228
    ESTADO_DF = 1236
    MUNICIPIO = 1244

    # Fundações Públicas de Direito Privado
    FUNDACAO_PUBLICA_DIREITO_PRIVADO_FEDERAL = 1252
    FUNDACAO_PUBLICA_DIREITO_PRIVADO_ESTADUAL_DF = 1260
    FUNDACAO_PUBLICA_DIREITO_PRIVADO_MUNICIPAL = 1279

    # Fundos Públicos
    FUNDO_PUBLICO_INDIRETA_FEDERAL = 1287
    FUNDO_PUBLICO_INDIRETA_ESTADUAL_DF = 1295
    FUNDO_PUBLICO_INDIRETA_MUNICIPAL = 1309
    FUNDO_PUBLICO_DIRETA_FEDERAL = 1317
    FUNDO_PUBLICO_DIRETA_ESTADUAL_DF = 1325
    FUNDO_PUBLICO_DIRETA_MUNICIPAL = 1333

    # União
    UNIAO = 1341

    # Empresas Estatais
    EMPRESA_PUBLICA = 2011
    SOCIEDADE_ECONOMIA_MISTA = 2038

    # Sociedades Empresárias
    SOCIEDADE_ANONIMA_ABERTA = 2046
    SOCIEDADE_ANONIMA_FECHADA = 2054
    SOCIEDADE_EMPRESARIA_LIMITADA = 2062
    SOCIEDADE_EMPRESARIA_NOME_COLETIVO = 2070
    SOCIEDADE_EMPRESARIA_COMANDITA_SIMPLES = 2089
    SOCIEDADE_EMPRESARIA_COMANDITA_ACOES = 2097
    SOCIEDADE_MERCANTIL_CAPITAL_INDUSTRIA = 2100
    SOCIEDADE_CONTA_PARTICIPACAO = 2127
    EMPRESARIO_INDIVIDUAL = 2135

    # Cooperativas e Consórcios
    COOPERATIVA = 2143
    CONSORCIO_SOCIEDADES = 2151
    GRUPO_SOCIEDADES = 2160

    # Entidades Estrangeiras
    ESTABELECIMENTO_SOCIEDADE_ESTRANGEIRA = 2178
    ESTABELECIMENTO_EMPRESA_BINACIONAL_ARG_BR = 2194
    EMPRESA_DOMICILIADA_EXTERIOR = 2216

    # Investimentos e Sociedades Simples
    CLUBE_FUNDO_INVESTIMENTO = 2224
    SOCIEDADE_SIMPLES_PURA = 2232
    SOCIEDADE_SIMPLES_LIMITADA = 2240
    SOCIEDADE_SIMPLES_NOME_COLETIVO = 2259
    SOCIEDADE_SIMPLES_COMANDITA_SIMPLES = 2267
    EMPRESA_BINACIONAL = 2275

    # Consórcios e EIRELIs
    CONSORCIO_EMPREGADORES = 2283
    CONSORCIO_SIMPLES = 2291
    EIRELI_EMPRESARIA = 2305
    EIRELI_SIMPLES = 2313
    SOCIEDADE_UNIPESSOAL_ADVOCACIA = 2321

    # Cooperativas e Inovação
    COOPERATIVA_CONSUMO = 2330
    INOVA_SIMPLES = 2348
    INVESTIDOR_NAO_RESIDENTE = 2356

    # Serviços e Fundações Privadas
    CARTORIO = 3034
    FUNDACAO_PRIVADA = 3069
    SERVICO_SOCIAL_AUTONOMO = 3077
    CONDOMINIO_EDILICIO = 3085

    # Entidades de Mediação e Sindicais
    COMISSAO_CONCILIACAO_PREVIA = 3107
    ENTIDADE_MEDIACAO_ARBITRAGEM = 3115
    ENTIDADE_SINDICAL = 3131

    # Fundações/Associações Estrangeiras
    ESTABELECIMENTO_FUNDACAO_ASSOCIACAO_ESTRANGEIRA = 3204
    FUNDACAO_ASSOCIACAO_DOMICILIADA_EXTERIOR = 3212

    # Entidades Religiosas e Indígenas
    ORGANIZACAO_RELIGIOSA = 3220
    COMUNIDADE_INDIGENA = 3239

    # Fundos e Partidos Políticos
    FUNDO_PRIVADO = 3247
    PARTIDO_POLITICO_NACIONAL = 3255
    PARTIDO_POLITICO_REGIONAL = 3263
    PARTIDO_POLITICO_LOCAL = 3271
    COMITE_FINANCEIRO_PARTIDO = 3280
    FRENTE_PLEBISCITARIA_REFERENDARIA = 3298

    # Organizações Sociais
    ORGANIZACAO_SOCIAL = 3301
    PLANO_PREVIDENCIA_COMPLEMENTAR = 3328
    ASSOCIACAO_PRIVADA = 3999

    # Outros
    EMPRESA_INDIVIDUAL_IMOBILIARIA = 4014
    CANDIDATO_POLITICO = 4090
    PRODUTOR_RURAL = 4120

    # Entidades Internacionais
    ORGANIZACAO_INTERNACIONAL = 5010
    REPRESENTACAO_DIPLOMATICA_ESTRANGEIRA = 5029
    INSTITUICOES_EXTRATERRITORIAIS = 5037

    @property
    def descricao(self) -> str:
        """Retorna descrição simplificada da natureza jurídica."""
        return self.name.replace("_", " ").title()

    @property
    def is_public_entity(self) -> bool:
        """Verifica se é entidade pública."""
        public_codes = list(range(1015, 1342))  # Códigos 1xxx
        return self.value in public_codes

    @property
    def is_private_entity(self) -> bool:
        """Verifica se é entidade privada."""
        private_codes = list(range(2011, 5038))  # Códigos 2xxx-5xxx
        return self.value in private_codes

    @property
    def is_federal(self) -> bool:
        """Verifica se é entidade federal."""
        federal_keywords = ["FEDERAL", "UNIAO"]
        return any(keyword in self.name for keyword in federal_keywords)

    @property
    def is_state(self) -> bool:
        """Verifica se é entidade estadual/DF."""
        return "ESTADUAL_DF" in self.name or self.value == 1236  # Estado ou DF

    @property
    def is_municipal(self) -> bool:
        """Verifica se é entidade municipal."""
        return "MUNICIPAL" in self.name or self.value == 1244  # Município

    @property
    def is_company(self) -> bool:
        """Verifica se é empresa/sociedade."""
        company_keywords = ["EMPRESA", "SOCIEDADE", "EMPRESARIO"]
        return any(keyword in self.name for keyword in company_keywords)
