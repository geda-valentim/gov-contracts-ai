"""
PNCP Domain: Categoria do Processo.

Defines the category/type of the procurement process.
"""

from enum import Enum


class CategoriaProcesso(int, Enum):
    """
    Categoria do processo de contratação.

    Reference: PNCP API Documentation - Section 5.11
    """

    CESSAO = 1
    COMPRAS = 2
    INFORMATICA_TIC = 3
    INTERNACIONAL = 4
    LOCACAO_IMOVEIS = 5
    MAO_DE_OBRA = 6
    OBRAS = 7
    SERVICOS = 8
    SERVICOS_ENGENHARIA = 9
    SERVICOS_SAUDE = 10
    ALIENACAO_BENS = 11

    @property
    def descricao(self) -> str:
        """Retorna descrição da categoria."""
        descricoes = {
            1: "Cessão",
            2: "Compras",
            3: "Informática (TIC)",
            4: "Internacional",
            5: "Locação de Imóveis",
            6: "Mão de Obra",
            7: "Obras",
            8: "Serviços",
            9: "Serviços de Engenharia",
            10: "Serviços de Saúde",
            11: "Alienação de bens móveis/imóveis",
        }
        return descricoes[self.value]

    @property
    def is_goods(self) -> bool:
        """Verifica se é compra de bens."""
        return self.value in [2, 3]  # Compras, Informática

    @property
    def is_services(self) -> bool:
        """Verifica se é contratação de serviços."""
        return self.value in [6, 8, 9, 10]  # Mão de Obra, Serviços, etc.

    @property
    def is_construction(self) -> bool:
        """Verifica se é obra."""
        return self.value == 7
