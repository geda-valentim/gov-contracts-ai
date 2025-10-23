"""
PNCP Domain: Modalidade de Contratação.

Defines the procurement method used for the bidding process.
"""

from enum import Enum


class ModalidadeContratacao(int, Enum):
    """
    Modalidade de contratação conforme Lei 14.133/2021.

    Reference: PNCP API Documentation - Section 5.2
    """

    LEILAO_ELETRONICO = 1
    DIALOGO_COMPETITIVO = 2
    CONCURSO = 3
    CONCORRENCIA_ELETRONICA = 4
    CONCORRENCIA_PRESENCIAL = 5
    PREGAO_ELETRONICO = 6
    PREGAO_PRESENCIAL = 7
    DISPENSA_LICITACAO = 8
    INEXIGIBILIDADE = 9
    MANIFESTACAO_INTERESSE = 10
    PRE_QUALIFICACAO = 11
    CREDENCIAMENTO = 12
    LEILAO_PRESENCIAL = 13

    @property
    def descricao(self) -> str:
        """Retorna descrição legível da modalidade."""
        return self.name.replace("_", " ").title()

    @property
    def is_electronic(self) -> bool:
        """Verifica se a modalidade é eletrônica."""
        return self.value in [1, 4, 6]

    @property
    def is_presencial(self) -> bool:
        """Verifica se a modalidade é presencial."""
        return self.value in [5, 7, 13]

    @property
    def permite_disputa(self) -> bool:
        """Verifica se a modalidade permite disputa de preços."""
        return self.value not in [8, 9]  # Dispensa e Inexigibilidade

    @classmethod
    def get_all(cls) -> list["ModalidadeContratacao"]:
        """Retorna todas as modalidades."""
        return list(cls)

    @classmethod
    def get_common(cls) -> list["ModalidadeContratacao"]:
        """Retorna modalidades mais comuns (~95% do volume)."""
        return [
            cls.PREGAO_ELETRONICO,  # ~70% do volume
            cls.DISPENSA_LICITACAO,  # ~20% do volume
            cls.INEXIGIBILIDADE,  # ~5% do volume
        ]

    @classmethod
    def get_electronic(cls) -> list["ModalidadeContratacao"]:
        """Retorna apenas modalidades eletrônicas."""
        return [m for m in cls if m.is_electronic]
