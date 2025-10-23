"""
PNCP (Portal Nacional de Contratações Públicas) Domain Models.

This package contains all domain enums and utilities for working with the PNCP API.

Usage:
    >>> from backend.app.domains.pncp import ModalidadeContratacao, build_modalidade_filter
    >>> modalidades = [ModalidadeContratacao.PREGAO_ELETRONICO]
    >>> filter_str = build_modalidade_filter(modalidades)
    >>> print(filter_str)
    "6"
"""

# Core procurement domains
from .amparo_legal import AmparoLegal
from .categoria_item_plano import CategoriaItemPlano
from .categoria_processo import CategoriaProcesso
from .criterio_julgamento import CriterioJulgamento
from .instrumento_convocatorio import InstrumentoConvocatorio
from .modalidade_contratacao import ModalidadeContratacao
from .modo_disputa import ModoDisputa

# Status domains
from .situacao_contratacao import SituacaoContratacao
from .situacao_item_contratacao import SituacaoItemContratacao
from .situacao_resultado_item import SituacaoResultadoItem

# Contract domains
from .tipo_beneficio import TipoBeneficio
from .tipo_contrato import TipoContrato
from .tipo_documento import TipoDocumento
from .tipo_termo_contrato import TipoTermoContrato

# Entity domains
from .natureza_juridica import NaturezaJuridica
from .porte_empresa import PorteEmpresa

# Utilities
from .utils import (
    build_modalidade_filter,
    get_enum_by_code,
    get_enum_description,
    parse_api_response_codes,
    validate_domain_code,
)

__all__ = [
    # Core procurement enums
    "AmparoLegal",
    "CategoriaItemPlano",
    "CategoriaProcesso",
    "CriterioJulgamento",
    "InstrumentoConvocatorio",
    "ModalidadeContratacao",
    "ModoDisputa",
    # Status enums
    "SituacaoContratacao",
    "SituacaoItemContratacao",
    "SituacaoResultadoItem",
    # Contract enums
    "TipoBeneficio",
    "TipoContrato",
    "TipoDocumento",
    "TipoTermoContrato",
    # Entity enums
    "NaturezaJuridica",
    "PorteEmpresa",
    # Utilities
    "build_modalidade_filter",
    "get_enum_by_code",
    "get_enum_description",
    "parse_api_response_codes",
    "validate_domain_code",
]
