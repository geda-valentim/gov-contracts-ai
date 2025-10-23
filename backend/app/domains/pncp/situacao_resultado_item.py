"""
PNCP Domain: Situação do Resultado do Item da Contratação.

Defines the status of the result for procurement items.
"""

from enum import Enum


class SituacaoResultadoItem(int, Enum):
    """
    Situação do resultado do item da contratação.

    Reference: PNCP API Documentation - Section 5.8
    """

    INFORMADO = 1
    CANCELADO = 2

    @property
    def descricao(self) -> str:
        """Retorna descrição da situação do resultado."""
        descricoes = {
            1: "Informado - Possui valor e fornecedor definidos",
            2: "Cancelado - Resultado cancelado conforme justificativa",
        }
        return descricoes[self.value]

    @property
    def is_valid(self) -> bool:
        """Verifica se o resultado é válido."""
        return self.value == 1
