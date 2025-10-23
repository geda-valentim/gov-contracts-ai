"""
PNCP Domain: Situação da Contratação.

Defines the current status of the procurement process.
"""

from enum import Enum


class SituacaoContratacao(int, Enum):
    """
    Situação da contratação no PNCP.

    Reference: PNCP API Documentation - Section 5.5
    """

    DIVULGADA_PNCP = 1
    REVOGADA = 2
    ANULADA = 3
    SUSPENSA = 4

    @property
    def descricao(self) -> str:
        """Retorna descrição da situação."""
        descricoes = {
            1: "Divulgada no PNCP - Situação inicial da contratação",
            2: "Revogada - Contratação revogada conforme justificativa",
            3: "Anulada - Contratação anulada conforme justificativa",
            4: "Suspensa - Contratação suspensa conforme justificativa",
        }
        return descricoes[self.value]

    @property
    def is_active(self) -> bool:
        """Verifica se a contratação está ativa."""
        return self.value in [1, 4]  # Divulgada ou Suspensa

    @property
    def is_cancelled(self) -> bool:
        """Verifica se a contratação foi cancelada."""
        return self.value in [2, 3]  # Revogada ou Anulada
