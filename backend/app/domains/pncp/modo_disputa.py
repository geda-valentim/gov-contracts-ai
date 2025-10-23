"""
PNCP Domain: Modo de Disputa.

Defines how the bidding competition will be conducted.
"""

from enum import Enum


class ModoDisputa(int, Enum):
    """
    Modo de disputa da licitação.

    Reference: PNCP API Documentation - Section 5.3
    """

    ABERTO = 1
    FECHADO = 2
    ABERTO_FECHADO = 3
    DISPENSA_COM_DISPUTA = 4
    NAO_SE_APLICA = 5
    FECHADO_ABERTO = 6

    @property
    def descricao(self) -> str:
        """Retorna descrição do modo de disputa."""
        descricoes = {
            1: "Aberto - Lances em tempo real",
            2: "Fechado - Propostas sigilosas",
            3: "Aberto-Fechado - Combinação sequencial",
            4: "Dispensa com Disputa - Cotação eletrônica",
            5: "Não se aplica",
            6: "Fechado-Aberto - Inverso da opção 3",
        }
        return descricoes[self.value]

    @property
    def permite_lances(self) -> bool:
        """Verifica se o modo permite lances em tempo real."""
        return self.value in [1, 3, 6]
