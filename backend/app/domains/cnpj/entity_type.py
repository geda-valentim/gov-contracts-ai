"""
CNPJ Entity Types - Tipos de entidades CNPJ da Receita Federal.

Cada entidade representa um tipo de arquivo/tabela disponível no site da RF.
"""

from enum import Enum
from typing import List


class CNPJEntityType(Enum):
    """
    Tipos de entidades CNPJ disponíveis na Receita Federal.

    Cada entidade corresponde a um conjunto de arquivos ZIP no site:
    https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/YYYY-MM/

    Prioridades:
    - P1 (Essenciais): Empresas, Estabelecimentos, CNAEs
    - P2 (Importantes): Sócios, Simples
    - P3 (Dimensões): Tabelas de referência pequenas
    """

    # ========== PRIORIDADE 1: Essenciais ==========
    EMPRESAS = "empresas"
    """
    Dados cadastrais básicos das empresas (CNPJ Base - 8 dígitos).

    Arquivos: Empresas0.zip a Empresas9.zip (10 arquivos)
    Tamanho total: ~1.2GB comprimido

    Campos principais:
    - CNPJ Básico (8 dígitos)
    - Razão Social
    - Natureza Jurídica
    - Capital Social
    - Porte
    """

    ESTABELECIMENTOS = "estabelecimentos"
    """
    Dados de estabelecimentos/filiais (CNPJ Completo - 14 dígitos).

    Arquivos: Estabelecimentos0.zip a Estabelecimentos9.zip (10 arquivos)
    Tamanho total: ~4.9GB comprimido

    Campos principais:
    - CNPJ Completo (14 dígitos = 8 base + 4 ordem + 2 DV)
    - Nome Fantasia
    - Situação Cadastral
    - CNAE Principal e Secundários
    - Endereço Completo
    - Contatos

    **MAIS IMPORTANTE para matching com PNCP**
    """

    CNAES = "cnaes"
    """
    Tabela de códigos e descrições de atividades econômicas.

    Arquivo: Cnaes.zip (1 arquivo)
    Tamanho: ~22KB

    Essencial para categorização e análise setorial.
    """

    # ========== PRIORIDADE 2: Importantes ==========
    SOCIOS = "socios"
    """
    Quadro societário das empresas.

    Arquivos: Socios0.zip a Socios9.zip (10 arquivos)
    Tamanho total: ~590MB comprimido

    Campos principais:
    - CNPJ Base
    - Identificação do Sócio (CPF/CNPJ)
    - Nome do Sócio
    - Qualificação
    - Percentual de Participação

    Útil para:
    - Detectar conflito de interesses
    - Análise de redes societárias
    """

    SIMPLES = "simples"
    """
    Opção pelo Simples Nacional e SIMEI.

    Arquivo: Simples.zip (1 arquivo)
    Tamanho: ~258MB

    Campos principais:
    - CNPJ Base
    - Opção pelo Simples
    - Data de Opção
    - Data de Exclusão
    """

    # ========== PRIORIDADE 3: Dimensões (Tabelas de Referência) ==========
    MUNICIPIOS = "municipios"
    """
    Tabela de códigos e nomes de municípios.

    Arquivo: Municipios.zip (1 arquivo)
    Tamanho: ~42KB
    """

    NATUREZAS = "naturezas"
    """
    Tabela de códigos e descrições de naturezas jurídicas.

    Arquivo: Naturezas.zip (1 arquivo)
    Tamanho: ~1.5KB
    """

    QUALIFICACOES = "qualificacoes"
    """
    Tabela de qualificações de sócios/responsáveis.

    Arquivo: Qualificacoes.zip (1 arquivo)
    Tamanho: ~1KB
    """

    PAISES = "paises"
    """
    Tabela de códigos e nomes de países.

    Arquivo: Paises.zip (1 arquivo)
    Tamanho: ~2.7KB
    """

    MOTIVOS = "motivos"
    """
    Tabela de motivos de situação cadastral.

    Arquivo: Motivos.zip (1 arquivo)
    Tamanho: ~1.2KB
    """

    @classmethod
    def get_priority_1(cls) -> List["CNPJEntityType"]:
        """Retorna entidades de prioridade 1 (essenciais)."""
        return [cls.EMPRESAS, cls.ESTABELECIMENTOS, cls.CNAES]

    @classmethod
    def get_priority_2(cls) -> List["CNPJEntityType"]:
        """Retorna entidades de prioridade 2 (importantes)."""
        return [cls.SOCIOS, cls.SIMPLES]

    @classmethod
    def get_priority_3(cls) -> List["CNPJEntityType"]:
        """Retorna entidades de prioridade 3 (dimensões)."""
        return [
            cls.MUNICIPIOS,
            cls.NATUREZAS,
            cls.QUALIFICACOES,
            cls.PAISES,
            cls.MOTIVOS,
        ]

    @classmethod
    def get_all(cls) -> List["CNPJEntityType"]:
        """Retorna todas as entidades em ordem de prioridade."""
        return cls.get_priority_1() + cls.get_priority_2() + cls.get_priority_3()

    @classmethod
    def get_dimensoes(cls) -> List["CNPJEntityType"]:
        """
        Retorna apenas tabelas de dimensão (pequenas, de referência).

        Útil para carregar primeiro antes das tabelas grandes.
        """
        return cls.get_priority_3()

    def get_file_pattern(self) -> str:
        """
        Retorna o padrão de nome de arquivo para esta entidade.

        Returns:
            str: Padrão de arquivo (ex: "Empresas{}.zip" onde {} = 0-9)

        Examples:
            >>> CNPJEntityType.EMPRESAS.get_file_pattern()
            'Empresas{}.zip'

            >>> CNPJEntityType.CNAES.get_file_pattern()
            'Cnaes.zip'
        """
        # Entidades com múltiplos arquivos (0-9)
        if self in [
            CNPJEntityType.EMPRESAS,
            CNPJEntityType.ESTABELECIMENTOS,
            CNPJEntityType.SOCIOS,
        ]:
            return f"{self.value.capitalize()}{{}}.zip"

        # Entidades com arquivo único
        # Capitalize first letter (ex: "cnaes" -> "Cnaes")
        filename = self.value.capitalize()
        return f"{filename}.zip"

    def get_num_files(self) -> int:
        """
        Retorna o número de arquivos para esta entidade.

        Returns:
            int: 10 para entidades particionadas, 1 para demais
        """
        if self in [
            CNPJEntityType.EMPRESAS,
            CNPJEntityType.ESTABELECIMENTOS,
            CNPJEntityType.SOCIOS,
        ]:
            return 10
        return 1

    def get_estimated_size_mb(self) -> int:
        """
        Retorna o tamanho estimado em MB (comprimido).

        Baseado nos dados de outubro/2025.
        """
        size_map = {
            CNPJEntityType.EMPRESAS: 1200,  # ~1.2GB
            CNPJEntityType.ESTABELECIMENTOS: 4900,  # ~4.9GB
            CNPJEntityType.SOCIOS: 590,  # ~590MB
            CNPJEntityType.SIMPLES: 258,  # ~258MB
            CNPJEntityType.CNAES: 1,  # ~22KB
            CNPJEntityType.MUNICIPIOS: 1,  # ~42KB
            CNPJEntityType.NATUREZAS: 1,  # ~1.5KB
            CNPJEntityType.QUALIFICACOES: 1,  # ~1KB
            CNPJEntityType.PAISES: 1,  # ~2.7KB
            CNPJEntityType.MOTIVOS: 1,  # ~1.2KB
        }
        return size_map.get(self, 0)

    def is_large(self) -> bool:
        """
        Verifica se é uma entidade grande (>100MB).

        Entidades grandes precisam de processamento streaming.
        """
        return self.get_estimated_size_mb() > 100

    @property
    def descricao(self) -> str:
        """Retorna descrição amigável da entidade."""
        descriptions = {
            CNPJEntityType.EMPRESAS: "Dados cadastrais básicos (CNPJ Base)",
            CNPJEntityType.ESTABELECIMENTOS: "Filiais e estabelecimentos (CNPJ Completo)",
            CNPJEntityType.CNAES: "Códigos de atividades econômicas",
            CNPJEntityType.SOCIOS: "Quadro societário",
            CNPJEntityType.SIMPLES: "Opção pelo Simples Nacional",
            CNPJEntityType.MUNICIPIOS: "Códigos de municípios",
            CNPJEntityType.NATUREZAS: "Naturezas jurídicas",
            CNPJEntityType.QUALIFICACOES: "Qualificações de sócios",
            CNPJEntityType.PAISES: "Códigos de países",
            CNPJEntityType.MOTIVOS: "Motivos de situação cadastral",
        }
        return descriptions.get(self, self.value)
