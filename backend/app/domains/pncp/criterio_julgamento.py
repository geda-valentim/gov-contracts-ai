"""
PNCP Domain: Critério de Julgamento.

Defines how bids will be evaluated and winner determined.
"""

from enum import Enum


class CriterioJulgamento(int, Enum):
    """
    Critério de julgamento das propostas.

    Reference: PNCP API Documentation - Section 5.4
    Note: Código 3 não existe na API oficial.
    """

    MENOR_PRECO = 1
    MAIOR_DESCONTO = 2
    TECNICA_E_PRECO = 4  # Note: código 3 não existe na API
    MAIOR_LANCE = 5
    MAIOR_RETORNO_ECONOMICO = 6
    NAO_SE_APLICA = 7
    MELHOR_TECNICA = 8
    CONTEUDO_ARTISTICO = 9

    @property
    def descricao(self) -> str:
        """Retorna descrição do critério."""
        descricoes = {
            1: "Menor Preço",
            2: "Maior Desconto",
            4: "Técnica e Preço",
            5: "Maior Lance",
            6: "Maior Retorno Econômico",
            7: "Não se aplica",
            8: "Melhor Técnica",
            9: "Conteúdo Artístico",
        }
        return descricoes[self.value]

    @property
    def is_price_based(self) -> bool:
        """Verifica se o critério é baseado em preço."""
        return self.value in [1, 2, 4, 6]

    @property
    def requires_technical_evaluation(self) -> bool:
        """Verifica se requer avaliação técnica."""
        return self.value in [4, 8, 9]
