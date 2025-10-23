"""
PNCP Domain Utilities.

Helper functions for working with PNCP domain enums.
"""

from enum import Enum
from typing import Optional

from .categoria_item_plano import CategoriaItemPlano
from .criterio_julgamento import CriterioJulgamento
from .instrumento_convocatorio import InstrumentoConvocatorio
from .modalidade_contratacao import ModalidadeContratacao
from .modo_disputa import ModoDisputa
from .situacao_item_contratacao import SituacaoItemContratacao
from .situacao_resultado_item import SituacaoResultadoItem
from .tipo_documento import TipoDocumento


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


def parse_item_response_codes(item: dict) -> dict:
    """
    Converte códigos de resposta da API de itens em enums legíveis.

    Args:
        item: Dict com resposta da API de itens

    Returns:
        Dict com enums mapeados e descrições

    Example:
        >>> parse_item_response_codes({
        ...     "itemCategoriaId": 1,
        ...     "situacaoCompraItem": 2,
        ...     "criterioJulgamentoId": 1
        ... })
        {
            'categoria': <CategoriaItemPlano.MATERIAL: 1>,
            'categoria_descricao': 'Material',
            'situacao': <SituacaoItemContratacao.HOMOLOGADO: 2>,
            'situacao_descricao': 'Homologado - Resultado definido com fornecedor',
            'criterio_julgamento': <CriterioJulgamento.MENOR_PRECO: 1>
        }
    """
    result = {}

    # Categoria do item
    if "itemCategoriaId" in item:
        cat_enum = get_enum_by_code(CategoriaItemPlano, item["itemCategoriaId"])
        result["categoria"] = cat_enum
        if cat_enum:
            result["categoria_descricao"] = cat_enum.descricao

    # Situação do item na contratação
    if "situacaoCompraItem" in item:
        sit_enum = get_enum_by_code(SituacaoItemContratacao, item["situacaoCompraItem"])
        result["situacao"] = sit_enum
        if sit_enum:
            result["situacao_descricao"] = sit_enum.descricao
            result["situacao_has_winner"] = sit_enum.has_winner

    # Critério de julgamento
    if "criterioJulgamentoId" in item:
        result["criterio_julgamento"] = get_enum_by_code(
            CriterioJulgamento, item["criterioJulgamentoId"]
        )

    # Material ou Serviço (M ou S)
    if "materialOuServico" in item:
        result["tipo_material_servico"] = (
            "Material" if item["materialOuServico"] == "M" else "Serviço"
        )

    return result


def parse_arquivo_response_codes(arquivo: dict) -> dict:
    """
    Converte códigos de resposta da API de arquivos em enums legíveis.

    Args:
        arquivo: Dict com resposta da API de arquivos

    Returns:
        Dict com enums mapeados e descrições

    Example:
        >>> parse_arquivo_response_codes({
        ...     "tipoDocumentoId": 2,
        ...     "titulo": "EDITAL"
        ... })
        {
            'tipo_documento': <TipoDocumento.EDITAL: 2>,
            'tipo_documento_descricao': 'Edital'
        }
    """
    result = {}

    # Tipo de documento
    if "tipoDocumentoId" in arquivo:
        tipo_enum = get_enum_by_code(TipoDocumento, arquivo["tipoDocumentoId"])
        result["tipo_documento"] = tipo_enum
        if tipo_enum:
            result["tipo_documento_descricao"] = tipo_enum.descricao

    # Status ativo
    if "statusAtivo" in arquivo:
        result["arquivo_ativo"] = arquivo["statusAtivo"]

    return result
