"""
PNCP Domain: Situação do Item da Contratação.

Defines the status of individual items within a procurement process.
"""

from enum import Enum


class SituacaoItemContratacao(int, Enum):
    """
    Situação do item da contratação.

    Reference: PNCP API Documentation - Section 5.6
    """

    EM_ANDAMENTO = 1
    HOMOLOGADO = 2
    ANULADO_REVOGADO_CANCELADO = 3
    DESERTO = 4
    FRACASSADO = 5

    @property
    def descricao(self) -> str:
        """Retorna descrição da situação do item."""
        descricoes = {
            1: "Em Andamento - Disputa/seleção não finalizada",
            2: "Homologado - Resultado definido com fornecedor",
            3: "Anulado/Revogado/Cancelado - Item cancelado",
            4: "Deserto - Sem fornecedores interessados",
            5: "Fracassado - Fornecedores desclassificados/inabilitados",
        }
        return descricoes[self.value]

    @property
    def has_winner(self) -> bool:
        """Verifica se o item tem vencedor definido."""
        return self.value == 2  # Homologado

    @property
    def is_unsuccessful(self) -> bool:
        """Verifica se o item não teve sucesso."""
        return self.value in [3, 4, 5]  # Cancelado, Deserto ou Fracassado
