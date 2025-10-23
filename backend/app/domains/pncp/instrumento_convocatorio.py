"""
PNCP Domain: Instrumento Convocatório.

Defines the type of document used to initiate procurement processes.
"""

from enum import Enum


class InstrumentoConvocatorio(int, Enum):
    """
    Instrumento convocatório usado nas licitações.

    Reference: PNCP API Documentation - Section 5.1
    """

    EDITAL = 1  # Usado em: diálogo competitivo, concurso, concorrência, pregão, etc.
    AVISO_CONTRATACAO_DIRETA = 2  # Usado em: Dispensa com Disputa
    ATO_AUTORIZACAO = 3  # Usado em: Dispensa sem Disputa ou Inexigibilidade

    @property
    def descricao(self) -> str:
        """Retorna descrição detalhada do instrumento."""
        descricoes = {
            1: "Edital - Diálogo competitivo, concurso, concorrência, pregão, etc.",
            2: "Aviso de Contratação Direta - Dispensa com Disputa",
            3: "Ato que autoriza a Contratação Direta - Dispensa/Inexigibilidade",
        }
        return descricoes[self.value]
