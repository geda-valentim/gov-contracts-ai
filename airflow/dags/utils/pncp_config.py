"""
PNCP Configuration and Constants.

Centralized configuration for PNCP data ingestion.
"""

import sys

sys.path.insert(0, "/opt/airflow")

from backend.app.domains.pncp import ModalidadeContratacao

# All 13 modalidades defined by PNCP API
ALL_MODALIDADES = [
    ModalidadeContratacao.LEILAO_ELETRONICO,  # 1
    ModalidadeContratacao.DIALOGO_COMPETITIVO,  # 2
    ModalidadeContratacao.CONCURSO,  # 3
    ModalidadeContratacao.CONCORRENCIA_ELETRONICA,  # 4
    ModalidadeContratacao.CONCORRENCIA_PRESENCIAL,  # 5
    ModalidadeContratacao.PREGAO_ELETRONICO,  # 6 - MOST COMMON
    ModalidadeContratacao.PREGAO_PRESENCIAL,  # 7
    ModalidadeContratacao.DISPENSA_LICITACAO,  # 8
    ModalidadeContratacao.INEXIGIBILIDADE,  # 9
    ModalidadeContratacao.MANIFESTACAO_INTERESSE,  # 10
    ModalidadeContratacao.PRE_QUALIFICACAO,  # 11
    ModalidadeContratacao.CREDENCIAMENTO,  # 12
    ModalidadeContratacao.LEILAO_PRESENCIAL,  # 13
]


# Most common modalidades (use for faster testing/development)
COMMON_MODALIDADES = [
    ModalidadeContratacao.PREGAO_ELETRONICO,  # ~70% of all procurements
    ModalidadeContratacao.CONCORRENCIA_ELETRONICA,  # ~15%
    ModalidadeContratacao.DISPENSA_LICITACAO,  # ~10%
]


# Electronic modalidades (higher data quality)
ELECTRONIC_MODALIDADES = [m for m in ALL_MODALIDADES if m.is_electronic]


def get_modalidades_for_env(env: str = "production") -> list:
    """
    Get modalidades based on environment.

    Args:
        env: Environment name (development, staging, production)

    Returns:
        List of ModalidadeContratacao enums
    """
    if env == "development":
        return COMMON_MODALIDADES
    elif env == "staging":
        return ELECTRONIC_MODALIDADES
    else:  # production
        return ALL_MODALIDADES


def get_modalidades_description_list() -> list[str]:
    """Get list of modalidade descriptions for logging."""
    return [m.descricao for m in ALL_MODALIDADES]
