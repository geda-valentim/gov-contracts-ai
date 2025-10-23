"""
PNCP Domain: Tipo de Benefício.

Defines benefits for small and micro enterprises (ME/EPP) in procurement.
"""

from enum import Enum


class TipoBeneficio(int, Enum):
    """
    Tipo de benefício para ME/EPP.

    Reference: PNCP API Documentation - Section 5.7
    """

    PARTICIPACAO_EXCLUSIVA = 1
    SUBCONTRATACAO = 2
    COTA_RESERVADA = 3
    SEM_BENEFICIO = 4
    NAO_SE_APLICA = 5

    @property
    def descricao(self) -> str:
        """Retorna descrição do tipo de benefício."""
        descricoes = {
            1: "Participação exclusiva para ME/EPP",
            2: "Subcontratação para ME/EPP",
            3: "Cota reservada para ME/EPP",
            4: "Sem benefício",
            5: "Não se aplica",
        }
        return descricoes[self.value]

    @property
    def has_mepp_benefit(self) -> bool:
        """Verifica se há benefício para ME/EPP."""
        return self.value in [1, 2, 3]

    @property
    def is_exclusive_mepp(self) -> bool:
        """Verifica se é exclusivo para ME/EPP."""
        return self.value == 1
