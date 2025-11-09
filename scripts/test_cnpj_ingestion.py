#!/usr/bin/env python3
"""
Script de teste para ingestão CNPJ.

Testa o download, extração e upload de arquivos pequenos (CNAEs).
"""

import sys
from pathlib import Path

# Adiciona o backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)

from loguru import logger

from backend.app.domains.cnpj import CNPJEntityType
from backend.app.services.ingestion.cnpj import CNPJIngestionService


def test_detect_version():
    """Testa detecção de última versão."""
    logger.info("=" * 60)
    logger.info("TEST 1: Detectar última versão disponível")
    logger.info("=" * 60)

    service = CNPJIngestionService()

    latest = service.get_latest_version()
    if latest:
        logger.info(f"✅ Última versão detectada: {latest}")
        return latest
    else:
        logger.error("❌ Falha ao detectar versão")
        return None


def test_check_update(latest_version: str):
    """Testa verificação de atualização."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Verificar se há atualização necessária")
    logger.info("=" * 60)

    service = CNPJIngestionService()

    needs_update, current, latest = service.needs_update()

    logger.info(f"Versão atual no Bronze: {current or 'Nenhuma'}")
    logger.info(f"Última versão disponível: {latest}")
    logger.info(f"Requer atualização: {needs_update}")


def test_ingest_cnaes(version: str):
    """Testa ingestão de CNAEs (arquivo pequeno)."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Ingestão de CNAEs (arquivo pequeno ~22KB)")
    logger.info("=" * 60)

    service = CNPJIngestionService()

    result = service.ingest_full_entity(version, CNPJEntityType.CNAES)

    logger.info("")
    logger.info("📊 Resultado da ingestão:")
    logger.info(f"  Entidade: {result['entity']}")
    logger.info(f"  Versão: {result['version']}")
    logger.info(f"  Arquivos processados: {result['successes']}/{result['total_files']}")
    logger.info(f"  Total de linhas: {result['total_rows']:,}")

    if result["successes"] > 0:
        logger.info("")
        logger.info("✅ TESTE PASSOU: Ingestão de CNAEs completa!")
        logger.info("")
        logger.info("📦 Verifique no MinIO:")
        logger.info(f"  Bucket: lh-bronze")
        logger.info(f"  Caminho: cnpj/cnaes/version={version}/data.parquet")
    else:
        logger.error("❌ TESTE FALHOU: Nenhum arquivo processado com sucesso")

    return result


def test_ingest_municipios(version: str):
    """Testa ingestão de Municípios (outro arquivo pequeno)."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 4: Ingestão de Municípios (arquivo pequeno ~42KB)")
    logger.info("=" * 60)

    service = CNPJIngestionService()

    result = service.ingest_full_entity(version, CNPJEntityType.MUNICIPIOS)

    logger.info("")
    logger.info("📊 Resultado da ingestão:")
    logger.info(f"  Entidade: {result['entity']}")
    logger.info(f"  Total de linhas: {result['total_rows']:,}")

    if result["successes"] > 0:
        logger.info("✅ TESTE PASSOU: Ingestão de Municípios completa!")
    else:
        logger.error("❌ TESTE FALHOU")

    return result


def main():
    """Executa todos os testes."""
    logger.info("🚀 Iniciando testes de ingestão CNPJ")
    logger.info("")

    # Check if required services are available
    from backend.app.core.health_checks import check_services_or_exit
    check_services_or_exit(["MinIO"], script_name="CNPJ Ingestion Test")

    # Test 1: Detectar versão
    latest_version = test_detect_version()
    if not latest_version:
        logger.error("❌ Não foi possível continuar sem versão")
        sys.exit(1)

    # Test 2: Verificar atualização
    test_check_update(latest_version)

    # Test 3: Ingestão CNAEs
    result_cnaes = test_ingest_cnaes(latest_version)

    # Test 4: Ingestão Municípios
    result_municipios = test_ingest_municipios(latest_version)

    # Sumário final
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 SUMÁRIO DOS TESTES")
    logger.info("=" * 60)
    logger.info(f"✅ CNAEs: {result_cnaes['total_rows']:,} linhas processadas")
    logger.info(f"✅ Municípios: {result_municipios['total_rows']:,} linhas processadas")
    logger.info("")
    logger.info("🎉 Todos os testes completados!")
    logger.info("")
    logger.info("📝 Próximos passos:")
    logger.info("  1. Verifique os arquivos Parquet no MinIO")
    logger.info("  2. Teste ingestão de arquivo grande (Empresas0)")
    logger.info("  3. Implemente DAG Airflow para automação")


if __name__ == "__main__":
    main()
