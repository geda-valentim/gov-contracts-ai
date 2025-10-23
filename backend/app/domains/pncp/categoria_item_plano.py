"""
PNCP Domain: Categoria do Item do Plano de Contratações.

Defines the category of items in procurement plans.
"""

from enum import Enum


class CategoriaItemPlano(int, Enum):
    """
    Categoria do item do plano de contratações.

    Reference: PNCP API Documentation - Section 5.16
    """

    MATERIAL = 1
    SERVICO = 2
    OBRAS = 3
    SERVICOS_ENGENHARIA = 4
    SOLUCOES_TIC = 5
    LOCACAO_IMOVEIS = 6
    ALIENACAO_CONCESSAO_PERMISSAO = 7
    OBRAS_SERVICOS_ENGENHARIA = 8

    @property
    def descricao(self) -> str:
        """Retorna descrição da categoria."""
        descricoes = {
            1: "Material",
            2: "Serviço",
            3: "Obras",
            4: "Serviços de Engenharia",
            5: "Soluções de TIC",
            6: "Locação de Imóveis",
            7: "Alienação/Concessão/Permissão",
            8: "Obras e Serviços de Engenharia",
        }
        return descricoes[self.value]

    @property
    def is_goods(self) -> bool:
        """Verifica se é aquisição de bens."""
        return self.value == 1

    @property
    def is_services(self) -> bool:
        """Verifica se é contratação de serviços."""
        return self.value in [2, 4]

    @property
    def is_construction(self) -> bool:
        """Verifica se envolve obras."""
        return self.value in [3, 8]

    @property
    def is_it_solution(self) -> bool:
        """Verifica se é solução de TIC."""
        return self.value == 5

    @property
    def is_real_estate(self) -> bool:
        """Verifica se envolve imóveis."""
        return self.value in [6, 7]
