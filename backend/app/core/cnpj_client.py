"""
CNPJ Client - Download de dados da Receita Federal.

Cliente HTTP para baixar dados públicos de CNPJ do site da Receita Federal.
"""

import re
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from loguru import logger

from backend.app.domains.cnpj import CNPJEntityType


class CNPJClient:
    """
    Cliente para download de dados CNPJ da Receita Federal.

    URL Base: https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/

    Funcionalidades:
    - Detectar última versão disponível (YYYY-MM)
    - Baixar arquivos ZIP por entidade
    - Descompactar arquivos CSV
    - Validar integridade
    """

    BASE_URL = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/"

    def __init__(self, timeout: int = 300):
        """
        Inicializa o cliente CNPJ.

        Args:
            timeout: Timeout para requests HTTP em segundos (default: 5min)
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; GovContractsAI/1.0; +https://github.com/gov-contracts-ai)"
            }
        )

    def get_latest_version(self) -> Optional[str]:
        """
        Detecta a última versão disponível no site da Receita Federal.

        Faz scraping do HTML do diretório raiz e extrai a pasta mais recente.

        Returns:
            str: Versão no formato "YYYY-MM" (ex: "2025-10")
            None: Se não conseguir detectar

        Example:
            >>> client = CNPJClient()
            >>> client.get_latest_version()
            '2025-10'
        """
        try:
            logger.info("🔍 Detectando última versão CNPJ na Receita Federal...")

            response = self.session.get(self.BASE_URL, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML para encontrar pastas YYYY-MM/
            # Pattern: <a href="YYYY-MM/">YYYY-MM/</a>
            pattern = r'<a href="(\d{4}-\d{2})/">(\d{4}-\d{2})/</a>'
            matches = re.findall(pattern, response.text)

            if not matches:
                logger.error("❌ Nenhuma pasta YYYY-MM/ encontrada no site da RF")
                return None

            # Pega todas as versões e ordena (mais recente primeiro)
            versions = sorted([match[0] for match in matches], reverse=True)

            latest = versions[0]
            logger.info(f"✅ Última versão detectada: {latest}")
            logger.debug(f"📋 Versões disponíveis: {versions[:5]}...")  # Mostra top 5

            return latest

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao acessar site da Receita Federal: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao detectar versão: {e}")
            return None

    def download_file(
        self,
        version: str,
        entity: CNPJEntityType,
        file_index: Optional[int] = None,
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Baixa um arquivo ZIP da Receita Federal.

        Args:
            version: Versão no formato "YYYY-MM" (ex: "2025-10")
            entity: Tipo de entidade a baixar
            file_index: Índice do arquivo (0-9) para entidades particionadas
                        None para entidades com arquivo único
            output_dir: Diretório de destino (default: tempdir)

        Returns:
            Path: Caminho do arquivo baixado
            None: Se falhar

        Example:
            >>> client = CNPJClient()
            >>> # Baixar CNAEs (arquivo único)
            >>> path = client.download_file("2025-10", CNPJEntityType.CNAES)

            >>> # Baixar Empresas0.zip (primeiro arquivo)
            >>> path = client.download_file("2025-10", CNPJEntityType.EMPRESAS, file_index=0)
        """
        try:
            # Validar file_index
            num_files = entity.get_num_files()
            if num_files > 1 and file_index is None:
                raise ValueError(
                    f"Entidade {entity.value} requer file_index (0-{num_files-1})"
                )
            if num_files == 1 and file_index is not None:
                logger.warning(
                    f"⚠️  Entidade {entity.value} não usa file_index, ignorando"
                )
                file_index = None

            # Construir nome do arquivo
            file_pattern = entity.get_file_pattern()
            if file_index is not None:
                filename = file_pattern.format(file_index)
            else:
                filename = file_pattern

            # Construir URL
            url = urljoin(self.BASE_URL, f"{version}/{filename}")

            # Definir output path
            if output_dir is None:
                output_dir = Path(tempfile.gettempdir()) / "cnpj_downloads" / version
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / filename

            # Verificar se já foi baixado
            if output_path.exists():
                logger.info(f"📦 Arquivo já existe: {output_path.name}")
                return output_path

            # Download
            logger.info(f"⬇️  Baixando {filename} de {version}...")
            logger.debug(f"URL: {url}")

            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Pegar tamanho total
            total_size = int(response.headers.get("content-length", 0))
            total_mb = total_size / (1024 * 1024)

            logger.info(f"📊 Tamanho: {total_mb:.1f} MB")

            # Baixar com progresso
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Log progresso a cada 100MB
                        if downloaded % (100 * 1024 * 1024) == 0:
                            progress_mb = downloaded / (1024 * 1024)
                            logger.info(f"  ⏳ Progresso: {progress_mb:.1f} MB...")

            logger.info(f"✅ Download completo: {output_path.name}")
            return output_path

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"❌ Arquivo não encontrado: {url}")
            else:
                logger.error(f"❌ Erro HTTP ao baixar: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao baixar arquivo: {e}")
            return None

    def extract_zip(
        self, zip_path: Path, output_dir: Optional[Path] = None
    ) -> list[Path]:
        """
        Descompacta arquivo ZIP.

        Args:
            zip_path: Caminho do arquivo ZIP
            output_dir: Diretório de destino (default: mesmo dir do ZIP)

        Returns:
            list[Path]: Lista de arquivos extraídos

        Example:
            >>> client = CNPJClient()
            >>> zip_path = Path("/tmp/Cnaes.zip")
            >>> extracted = client.extract_zip(zip_path)
            >>> # [Path("/tmp/Cnaes.csv")]
        """
        try:
            if output_dir is None:
                output_dir = zip_path.parent

            logger.info(f"📦 Descompactando {zip_path.name}...")

            extracted_files = []

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Listar arquivos
                file_list = zip_ref.namelist()
                logger.info(f"📋 Arquivos no ZIP: {len(file_list)}")

                # Extrair todos
                for file_info in zip_ref.infolist():
                    extracted_path = output_dir / file_info.filename
                    zip_ref.extract(file_info, output_dir)
                    extracted_files.append(extracted_path)
                    logger.debug(f"  ✅ Extraído: {file_info.filename}")

            logger.info(
                f"✅ Descompactação completa: {len(extracted_files)} arquivo(s)"
            )
            return extracted_files

        except zipfile.BadZipFile:
            logger.error(f"❌ Arquivo ZIP corrompido: {zip_path}")
            return []
        except Exception as e:
            logger.error(f"❌ Erro ao descompactar: {e}")
            return []

    def download_and_extract(
        self,
        version: str,
        entity: CNPJEntityType,
        file_index: Optional[int] = None,
        output_dir: Optional[Path] = None,
        keep_zip: bool = False,
    ) -> list[Path]:
        """
        Baixa e descompacta arquivo em uma operação.

        Args:
            version: Versão YYYY-MM
            entity: Tipo de entidade
            file_index: Índice do arquivo (se particionado)
            output_dir: Diretório de saída
            keep_zip: Se True, mantém o ZIP após extrair (default: False)

        Returns:
            list[Path]: Lista de arquivos CSV extraídos

        Example:
            >>> client = CNPJClient()
            >>> csv_files = client.download_and_extract("2025-10", CNPJEntityType.CNAES)
            >>> # [Path("/tmp/cnpj_downloads/2025-10/Cnaes.csv")]
        """
        # Download
        zip_path = self.download_file(version, entity, file_index, output_dir)

        if zip_path is None:
            return []

        # Extract
        extracted_files = self.extract_zip(zip_path)

        # Cleanup ZIP se solicitado
        if not keep_zip and zip_path.exists():
            logger.info(f"🗑️  Removendo ZIP: {zip_path.name}")
            zip_path.unlink()

        return extracted_files

    def cleanup_downloads(self, version: str, output_dir: Optional[Path] = None):
        """
        Remove todos os arquivos baixados de uma versão.

        Args:
            version: Versão YYYY-MM
            output_dir: Diretório base (default: tempdir)
        """
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "cnpj_downloads" / version
        else:
            output_dir = output_dir / version

        if not output_dir.exists():
            logger.info(f"✅ Diretório já limpo: {output_dir}")
            return

        try:
            import shutil

            logger.info(f"🗑️  Removendo diretório: {output_dir}")
            shutil.rmtree(output_dir)
            logger.info("✅ Limpeza completa")
        except Exception as e:
            logger.error(f"❌ Erro ao limpar diretório: {e}")
