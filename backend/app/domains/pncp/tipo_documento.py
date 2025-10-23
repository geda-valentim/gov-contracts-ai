"""
PNCP Domain: Tipo de Documento.

Defines the type of document associated with procurement processes.
"""

from enum import Enum


class TipoDocumento(int, Enum):
    """
    Tipo de documento da contratação/contrato.

    Reference: PNCP API Documentation - Section 5.12
    """

    # Documentos da contratação
    AVISO_CONTRATACAO_DIRETA = 1
    EDITAL = 2

    # Anexos
    MINUTA_CONTRATO = 3
    TERMO_REFERENCIA = 4
    ANTEPROJETO = 5
    PROJETO_BASICO = 6
    ESTUDO_TECNICO_PRELIMINAR = 7
    PROJETO_EXECUTIVO = 8
    MAPA_RISCOS = 9
    DFD = 10

    # Ata de registro de preço
    ATA_REGISTRO_PRECO = 11

    # Documentos de contrato
    CONTRATO = 12
    TERMO_RESCISAO = 13
    TERMO_ADITIVO = 14
    TERMO_APOSTILAMENTO = 15
    NOTA_EMPENHO = 17
    RELATORIO_FINAL_CONTRATO = 18

    @property
    def descricao(self) -> str:
        """Retorna descrição do tipo de documento."""
        descricoes = {
            1: "Aviso de Contratação Direta",
            2: "Edital",
            3: "Minuta do Contrato",
            4: "Termo de Referência",
            5: "Anteprojeto",
            6: "Projeto Básico",
            7: "Estudo Técnico Preliminar",
            8: "Projeto Executivo",
            9: "Mapa de Riscos",
            10: "DFD",
            11: "Ata de Registro de Preço",
            12: "Contrato",
            13: "Termo de Rescisão",
            14: "Termo Aditivo",
            15: "Termo de Apostilamento",
            17: "Nota de Empenho",
            18: "Relatório Final de Contrato",
        }
        return descricoes[self.value]

    @property
    def is_procurement_doc(self) -> bool:
        """Verifica se é documento de contratação."""
        return self.value in [1, 2]

    @property
    def is_technical_doc(self) -> bool:
        """Verifica se é documento técnico."""
        return self.value in [4, 5, 6, 7, 8, 9, 10]

    @property
    def is_contract_doc(self) -> bool:
        """Verifica se é documento de contrato."""
        return self.value in [12, 13, 14, 15, 17, 18]

    @property
    def is_amendment_doc(self) -> bool:
        """Verifica se é documento de alteração/rescisão."""
        return self.value in [13, 14, 15]
