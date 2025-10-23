"""
PNCP Domain: Tipo de Termo de Contrato.

Defines the type of contract amendment or termination.
"""

from enum import Enum


class TipoTermoContrato(int, Enum):
    """
    Tipo de termo de contrato (alterações/rescisão).

    Reference: PNCP API Documentation - Section 5.10
    """

    TERMO_RESCISAO = 1
    TERMO_ADITIVO = 2
    TERMO_APOSTILAMENTO = 3

    @property
    def descricao(self) -> str:
        """Retorna descrição do tipo de termo."""
        descricoes = {
            1: "Termo de Rescisão - Encerramento antes da data final",
            2: "Termo Aditivo - Prorrogação, reajuste, acréscimo ou supressão",
            3: "Termo de Apostilamento - Atualização de valor",
        }
        return descricoes[self.value]

    @property
    def is_termination(self) -> bool:
        """Verifica se é rescisão."""
        return self.value == 1

    @property
    def is_amendment(self) -> bool:
        """Verifica se é alteração."""
        return self.value in [2, 3]
