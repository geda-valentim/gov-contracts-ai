"""
PNCP Domain: Porte da Empresa.

Defines the size classification of companies.
"""

from enum import Enum


class PorteEmpresa(int, Enum):
    """
    Porte da empresa.

    Reference: PNCP API Documentation - Section 5.14
    """

    ME = 1  # Microempresa
    EPP = 2  # Empresa de Pequeno Porte
    DEMAIS = 3  # Demais empresas
    NAO_SE_APLICA = 4  # Pessoa física
    NAO_INFORMADO = 5  # Não informado

    @property
    def descricao(self) -> str:
        """Retorna descrição do porte."""
        descricoes = {
            1: "ME - Microempresa",
            2: "EPP - Empresa de Pequeno Porte",
            3: "Demais - Demais empresas",
            4: "Não se aplica - Pessoa física",
            5: "Não informado",
        }
        return descricoes[self.value]

    @property
    def is_small_business(self) -> bool:
        """Verifica se é ME ou EPP."""
        return self.value in [1, 2]

    @property
    def is_large_company(self) -> bool:
        """Verifica se é grande empresa."""
        return self.value == 3

    @property
    def is_individual(self) -> bool:
        """Verifica se é pessoa física."""
        return self.value == 4
