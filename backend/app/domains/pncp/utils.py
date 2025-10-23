"""
PNCP Domain Utilities.

Helper functions for working with PNCP domain enums.
"""

from enum import Enum
from typing import Optional

from .criterio_julgamento import CriterioJulgamento
from .instrumento_convocatorio import InstrumentoConvocatorio
from .modalidade_contratacao import ModalidadeContratacao
from .modo_disputa import ModoDisputa


def get_enum_by_code(enum_class: type[Enum], code: int) -> Optional[Enum]:
    """
    Retorna enum pelo código, ou None se não existir.

    Args:
        enum_class: Classe do Enum (ex: ModalidadeContratacao)
        code: Código numérico da API

    Returns:
        Instância do Enum ou None

    Example:
        >>> get_enum_by_code(ModalidadeContratacao, 6)
        <ModalidadeContratacao.PREGAO_ELETRONICO: 6>
    """
    try:
        return enum_class(code)
    except ValueError:
        return None


def get_enum_description(enum_instance: Enum) -> str:
    """
    Retorna descrição do enum (usa .descricao se existir, senão .name).

    Args:
        enum_instance: Instância de qualquer Enum deste módulo

    Returns:
        String com descrição legível
    """
    if hasattr(enum_instance, "descricao"):
        return enum_instance.descricao
    return enum_instance.name.replace("_", " ").title()


def validate_domain_code(enum_class: type[Enum], code: int) -> bool:
    """
    Valida se um código existe no domínio.

    Args:
        enum_class: Classe do Enum
        code: Código a validar

    Returns:
        True se código válido, False caso contrário

    Example:
        >>> validate_domain_code(ModoDisputa, 1)
        True
        >>> validate_domain_code(ModoDisputa, 99)
        False
    """
    return get_enum_by_code(enum_class, code) is not None


def build_modalidade_filter(modalidades: list[ModalidadeContratacao]) -> str:
    """
    Constrói string de filtro para query de modalidades.

    Args:
        modalidades: Lista de enums ModalidadeContratacao

    Returns:
        String formatada para query param da API

    Example:
        >>> build_modalidade_filter([ModalidadeContratacao.PREGAO_ELETRONICO])
        "6"
        >>> build_modalidade_filter([
        ...     ModalidadeContratacao.PREGAO_ELETRONICO,
        ...     ModalidadeContratacao.CONCORRENCIA_ELETRONICA
        ... ])
        "6,4"
    """
    return ",".join(str(m.value) for m in modalidades)


def parse_api_response_codes(data: dict) -> dict:
    """
    Converte códigos de resposta da API em enums legíveis.

    Args:
        data: Dict com resposta da API (contendo códigos numéricos)

    Returns:
        Dict com enums mapeados

    Example:
        >>> parse_api_response_codes({
        ...     "modalidadeId": 6,
        ...     "modoDisputaId": 1,
        ...     "criterioJulgamentoId": 1
        ... })
        {
            'modalidade': <ModalidadeContratacao.PREGAO_ELETRONICO: 6>,
            'modoDisputa': <ModoDisputa.ABERTO: 1>,
            'criterioJulgamento': <CriterioJulgamento.MENOR_PRECO: 1>
        }
    """
    result = {}

    if "modalidadeId" in data:
        result["modalidade"] = get_enum_by_code(
            ModalidadeContratacao, data["modalidadeId"]
        )

    if "modoDisputaId" in data:
        result["modoDisputa"] = get_enum_by_code(ModoDisputa, data["modoDisputaId"])

    if "criterioJulgamentoId" in data:
        result["criterioJulgamento"] = get_enum_by_code(
            CriterioJulgamento, data["criterioJulgamentoId"]
        )

    if "instrumentoConvocatorioId" in data:
        result["instrumentoConvocatorio"] = get_enum_by_code(
            InstrumentoConvocatorio, data["instrumentoConvocatorioId"]
        )

    return result
