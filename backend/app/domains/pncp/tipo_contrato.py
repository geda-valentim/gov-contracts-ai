"""
PNCP Domain: Tipo de Contrato.

Defines the type of contract instrument used.
"""

from enum import Enum


class TipoContrato(int, Enum):
    """
    Tipo de contrato.

    Reference: PNCP API Documentation - Section 5.9
    """

    CONTRATO = 1
    COMODATO = 2
    ARRENDAMENTO = 3
    CONCESSAO = 4
    TERMO_ADESAO = 5
    CONVENIO = 6
    EMPENHO = 7
    OUTROS = 8
    TED = 9  # Termo de Execução Descentralizada
    ACT = 10  # Acordo de Cooperação Técnica
    TERMO_COMPROMISSO = 11
    CARTA_CONTRATO = 12

    @property
    def descricao(self) -> str:
        """Retorna descrição do tipo de contrato."""
        descricoes = {
            1: "Contrato - Acordo formal entre as partes",
            2: "Comodato - Concessão de uso gratuito",
            3: "Arrendamento - Cessão mediante pagamento",
            4: "Concessão - Execução de serviço público remunerada por tarifa",
            5: "Termo de Adesão - Cláusulas pré-definidas",
            6: "Convênio - Realização de objetivo em comum",
            7: "Empenho - Promessa de pagamento",
            8: "Outros - Outros tipos não listados",
            9: "TED - Termo de Execução Descentralizada",
            10: "ACT - Acordo de Cooperação Técnica",
            11: "Termo de Compromisso - Acordo para cumprir compromisso",
            12: "Carta Contrato - Formalização simplificada",
        }
        return descricoes[self.value]

    @property
    def is_formal_contract(self) -> bool:
        """Verifica se é um contrato formal."""
        return self.value in [1, 2, 3, 4, 5, 12]

    @property
    def is_agreement(self) -> bool:
        """Verifica se é um acordo/convênio."""
        return self.value in [6, 9, 10, 11]
