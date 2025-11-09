"""
CNPJ Ingestion Service - Ingestão de dados CNPJ para Bronze layer.

Serviço responsável por:
1. Baixar arquivos da Receita Federal
2. Processar CSVs e converter para Parquet
3. Upload para MinIO (Bronze layer)
4. Gerenciar versionamento
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from backend.app.core.cnpj_client import CNPJClient
from backend.app.core.storage_client import get_storage_client
from backend.app.domains.cnpj import CNPJEntityType


class CNPJIngestionService:
    """
    Serviço de ingestão de dados CNPJ.

    Workflow:
    1. Detectar última versão disponível
    2. Download arquivo(s) por entidade
    3. Descompactar e validar CSV
    4. Converter para Parquet
    5. Upload para MinIO Bronze
    6. Atualizar metadata
    7. Cleanup temporários
    """

    def __init__(self):
        """Inicializa o serviço de ingestão CNPJ."""
        self.client = CNPJClient()
        self.storage = get_storage_client()

    def get_latest_version(self) -> Optional[str]:
        """
        Detecta a última versão disponível na Receita Federal.

        Returns:
            str: Versão YYYY-MM (ex: "2025-10")
            None: Se falhar
        """
        return self.client.get_latest_version()

    def get_current_version(self) -> Optional[str]:
        """
        Obtém a versão atualmente no Bronze layer.

        Returns:
            str: Versão atual ou None se não houver
        """
        try:
            # Ler metadata
            metadata_key = "cnpj/_metadata/version_control.json"
            metadata_json = self.storage.read_json_from_s3(
                bucket=self.storage.BUCKET_BRONZE, key=metadata_key
            )

            return metadata_json.get("current_version")

        except Exception as e:
            logger.warning(f"⚠️  Não foi possível ler versão atual: {e}")
            return None

    def needs_update(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica se há nova versão disponível.

        Returns:
            tuple: (needs_update: bool, current_version: str, latest_version: str)

        Example:
            >>> service = CNPJIngestionService()
            >>> needs_update, current, latest = service.needs_update()
            >>> if needs_update:
            ...     print(f"Atualizar de {current} para {latest}")
        """
        current = self.get_current_version()
        latest = self.get_latest_version()

        if latest is None:
            logger.error("❌ Não foi possível detectar última versão")
            return False, current, None

        if current is None:
            logger.info(f"📥 Primeira ingestão: {latest}")
            return True, None, latest

        if current != latest:
            logger.info(f"🔄 Nova versão disponível: {current} → {latest}")
            return True, current, latest

        logger.info(f"✅ Versão atual está atualizada: {current}")
        return False, current, latest

    def ingest_entity(
        self,
        version: str,
        entity: CNPJEntityType,
        file_index: Optional[int] = None,
    ) -> dict:
        """
        Ingere uma entidade (ou arquivo de uma entidade) para o Bronze.

        Args:
            version: Versão YYYY-MM
            entity: Tipo de entidade
            file_index: Índice do arquivo (0-9) se particionado

        Returns:
            dict: Metadados da ingestão

        Workflow:
            1. Download do ZIP
            2. Extração do CSV
            3. Leitura e validação
            4. Conversão para Parquet
            5. Upload para MinIO
            6. Cleanup local
        """
        logger.info(
            f"🚀 Iniciando ingestão: {entity.value} (versão: {version}, índice: {file_index})"
        )

        try:
            # 1. Download e extração
            csv_files = self.client.download_and_extract(
                version=version,
                entity=entity,
                file_index=file_index,
                keep_zip=False,  # Remove ZIP após extrair
            )

            if not csv_files:
                logger.error(f"❌ Nenhum arquivo CSV extraído para {entity.value}")
                return {"success": False, "error": "No CSV files extracted"}

            csv_path = csv_files[0]  # Pega o primeiro CSV
            logger.info(f"📄 CSV extraído: {csv_path.name}")

            # 2. Ler CSV
            logger.info("📖 Lendo CSV...")
            df = self._read_csv(csv_path, entity)

            if df is None or df.empty:
                logger.error("❌ Falha ao ler CSV ou DataFrame vazio")
                return {"success": False, "error": "Failed to read CSV"}

            logger.info(f"✅ CSV lido: {len(df):,} linhas, {len(df.columns)} colunas")

            # 3. Upload para MinIO (diretamente do DataFrame)
            s3_key = self._get_s3_key(version, entity, file_index)
            logger.info(f"☁️  Fazendo upload para MinIO: {s3_key}")

            # Converter para Parquet em memória
            import io

            parquet_buffer = io.BytesIO()
            df.to_parquet(
                parquet_buffer,
                engine="pyarrow",
                compression="snappy",
                index=False,
            )

            parquet_size_mb = len(parquet_buffer.getvalue()) / (1024 * 1024)
            logger.info(f"✅ Parquet gerado: {parquet_size_mb:.1f} MB")

            # Upload para MinIO via MinIOClient wrapper
            parquet_buffer.seek(0)
            self.storage._client.upload_fileobj(
                file_obj=parquet_buffer,
                bucket_name=self.storage.BUCKET_BRONZE,
                object_name=s3_key,
            )

            logger.info(
                f"✅ Upload completo: s3://{self.storage.BUCKET_BRONZE}/{s3_key}"
            )

            # 4. Cleanup local
            logger.info("🗑️  Limpando arquivos temporários...")
            csv_path.unlink(missing_ok=True)

            # 6. Retornar metadata
            metadata = {
                "success": True,
                "version": version,
                "entity": entity.value,
                "file_index": file_index,
                "s3_key": s3_key,
                "row_count": len(df),
                "columns": list(df.columns),
                "size_mb": parquet_size_mb,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"🎉 Ingestão completa: {entity.value}")
            return metadata

        except Exception as e:
            logger.error(f"❌ Erro na ingestão de {entity.value}: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def _read_csv(
        self, csv_path: Path, entity: CNPJEntityType
    ) -> Optional[pd.DataFrame]:
        """
        Lê arquivo CSV com configurações específicas para CNPJ.

        Os arquivos CNPJ da RF têm características específicas:
        - Separador: ponto-e-vírgula (;)
        - Encoding: ISO-8859-1 (latin1)
        - Sem cabeçalho (primeira linha é dados)
        - Aspas: duplas (")

        Args:
            csv_path: Caminho do arquivo CSV
            entity: Tipo de entidade (para definir schema)

        Returns:
            pd.DataFrame: DataFrame com os dados
        """
        try:
            # Configurações gerais para CSVs da RF
            df = pd.read_csv(
                csv_path,
                sep=";",
                encoding="ISO-8859-1",
                header=None,  # Sem cabeçalho
                dtype=str,  # Ler tudo como string inicialmente
                na_values=["", "NULL"],
                keep_default_na=False,
                low_memory=False,
            )

            # Adicionar nomes de colunas baseado na entidade
            column_names = self._get_column_names(entity)
            if column_names and len(column_names) == len(df.columns):
                df.columns = column_names
            else:
                logger.warning(
                    f"⚠️  Schema esperado ({len(column_names)} colunas) "
                    f"não bate com CSV ({len(df.columns)} colunas). "
                    f"Usando nomes genéricos."
                )
                df.columns = [f"col_{i}" for i in range(len(df.columns))]

            return df

        except Exception as e:
            logger.error(f"❌ Erro ao ler CSV: {e}")
            return None

    def _get_column_names(self, entity: CNPJEntityType) -> list[str]:
        """
        Retorna nomes de colunas para cada entidade.

        Baseado na documentação oficial:
        https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf

        Args:
            entity: Tipo de entidade

        Returns:
            list[str]: Lista de nomes de colunas
        """
        schemas = {
            CNPJEntityType.CNAES: ["codigo", "descricao"],
            CNPJEntityType.MUNICIPIOS: ["codigo", "descricao"],
            CNPJEntityType.NATUREZAS: ["codigo", "descricao"],
            CNPJEntityType.QUALIFICACOES: ["codigo", "descricao"],
            CNPJEntityType.PAISES: ["codigo", "descricao"],
            CNPJEntityType.MOTIVOS: ["codigo", "descricao"],
            # TODO: Adicionar schemas completos para entidades grandes
            # CNPJEntityType.EMPRESAS: [...],
            # CNPJEntityType.ESTABELECIMENTOS: [...],
            # CNPJEntityType.SOCIOS: [...],
        }

        return schemas.get(entity, [])

    def _get_s3_key(
        self, version: str, entity: CNPJEntityType, file_index: Optional[int]
    ) -> str:
        """
        Constrói chave S3 para armazenamento no Bronze.

        Estrutura:
            cnpj/{entity}/version={version}/
                data.parquet                    # Se arquivo único
                part_{index}.parquet            # Se particionado

        Args:
            version: YYYY-MM
            entity: Tipo de entidade
            file_index: Índice do arquivo (se particionado)

        Returns:
            str: Chave S3 completa

        Examples:
            >>> _get_s3_key("2025-10", CNPJEntityType.CNAES, None)
            'cnpj/cnaes/version=2025-10/data.parquet'

            >>> _get_s3_key("2025-10", CNPJEntityType.EMPRESAS, 0)
            'cnpj/empresas/version=2025-10/part_0.parquet'
        """
        base_path = f"cnpj/{entity.value}/version={version}"

        if file_index is not None:
            filename = f"part_{file_index}.parquet"
        else:
            filename = "data.parquet"

        return f"{base_path}/{filename}"

    def ingest_full_entity(self, version: str, entity: CNPJEntityType) -> dict:
        """
        Ingere todos os arquivos de uma entidade.

        Para entidades particionadas (Empresas, Estabelecimentos, Sócios),
        processa todos os arquivos (0-9).

        Para entidades únicas, processa o arquivo único.

        Args:
            version: Versão YYYY-MM
            entity: Tipo de entidade

        Returns:
            dict: Resultado agregado da ingestão
        """
        logger.info(f"🚀 Ingestão completa: {entity.descricao} (versão {version})")

        num_files = entity.get_num_files()
        results = []

        if num_files == 1:
            # Arquivo único
            result = self.ingest_entity(version, entity, file_index=None)
            results.append(result)
        else:
            # Múltiplos arquivos (0-9)
            for i in range(num_files):
                logger.info(f"📦 Processando arquivo {i+1}/{num_files}...")
                result = self.ingest_entity(version, entity, file_index=i)
                results.append(result)

        # Agregar resultados
        successes = sum(1 for r in results if r.get("success"))
        failures = len(results) - successes
        total_rows = sum(r.get("row_count", 0) for r in results if r.get("success"))

        summary = {
            "entity": entity.value,
            "version": version,
            "total_files": num_files,
            "successes": successes,
            "failures": failures,
            "total_rows": total_rows,
            "results": results,
        }

        logger.info(
            f"✅ Ingestão completa: {entity.value} "
            f"({successes}/{num_files} sucesso, {total_rows:,} linhas)"
        )

        return summary
