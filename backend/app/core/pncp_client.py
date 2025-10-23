"""Cliente para PNCP API com retry logic e rate limiting"""

import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from ..domains.pncp import (
    ModalidadeContratacao,
    build_modalidade_filter,
    parse_api_response_codes,
)

logger = logging.getLogger(__name__)


class PNCPClient:
    """Cliente para consultar dados do PNCP"""

    BASE_URL_QUERY = "https://pncp.gov.br/api/consulta"
    BASE_URL_INTEGRATION = "https://pncp.gov.br/api/pncp"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        rate_limit_delay: float = 0.5,
        endpoint_url: Optional[str] = None,
        base_url_query: Optional[str] = None,
        base_url_integration: Optional[str] = None,
    ):
        """
        Args:
            username: Para Integration API (opcional)
            password: Para Integration API (opcional)
            rate_limit_delay: Delay entre requests (segundos)
            endpoint_url: Endpoint base para API (ex: https://pncp.gov.br/api)
            base_url_query: Override explícito para endpoint de consulta
            base_url_integration: Override explícito para endpoint de integração
        """
        self.username = username
        self.password = password
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.token = None
        self.token_expiry = None

        # Permite customizar URLs (útil para ambientes de teste)
        root_endpoint = endpoint_url.rstrip("/") if endpoint_url else None
        self.base_url_query = (
            base_url_query
            if base_url_query
            else f"{root_endpoint}/consulta"
            if root_endpoint
            else self.BASE_URL_QUERY
        )
        self.base_url_integration = (
            base_url_integration
            if base_url_integration
            else f"{root_endpoint}/pncp"
            if root_endpoint
            else self.BASE_URL_INTEGRATION
        )

    def _rate_limit(self):
        """Implementa rate limiting respeitoso"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> requests.Response:
        """Faz request com retry automático"""
        self._rate_limit()

        logger.info(f"{method} {url}")

        response = requests.request(method, url, **kwargs)
        response.raise_for_status()

        return response

    def fetch_contratacoes_by_date(
        self,
        data_inicial: str,
        data_final: str,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> Dict:
        """
        Busca contratações por data de publicação.

        Args:
            data_inicial: YYYYMMDD
            data_final: YYYYMMDD
            modalidades: Lista de enums ModalidadeContratacao. Se None, usa Pregão Eletrônico.
            pagina: Número da página
            tamanho_pagina: Registros por página (max 50)

        Returns:
            Dict com 'data', 'totalRegistros', 'totalPaginas', etc.

        Example:
            >>> client.fetch_contratacoes_by_date(
            ...     "20240101",
            ...     "20240131",
            ...     modalidades=[ModalidadeContratacao.PREGAO_ELETRONICO]
            ... )
        """
        url = f"{self.base_url_query}/v1/contratacoes/publicacao"

        # Default: Pregão Eletrônico
        if modalidades is None:
            modalidades = [ModalidadeContratacao.PREGAO_ELETRONICO]

        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "codigoModalidadeContratacao": build_modalidade_filter(modalidades),
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }

        response = self._make_request(url, params=params, timeout=30)

        # Handle empty responses (common for future dates or rare modalidades)
        if not response.content or response.content.strip() == b"":
            logger.warning(
                "Empty response from PNCP API - no data available for the requested parameters"
            )
            return {"data": [], "totalRegistros": 0, "totalPaginas": 0}

        try:
            result = response.json()
        except ValueError as e:
            # JSONDecodeError inherits from ValueError
            logger.warning(
                f"Invalid JSON response from PNCP API (likely empty/no data): {e}"
            )
            return {"data": [], "totalRegistros": 0, "totalPaginas": 0}

        # Enriquece resposta com enums legíveis
        if "data" in result and isinstance(result["data"], list):
            for item in result["data"]:
                item["_parsed_domains"] = parse_api_response_codes(item)

        return result

    def fetch_all_contratacoes_by_date(
        self,
        data_inicial: str,
        data_final: str,
        modalidades: Optional[List[ModalidadeContratacao]] = None,
        num_pages: Optional[int] = None,
    ) -> List[Dict]:
        """
        Busca TODAS as contratações (paginando automaticamente)

        Args:
            data_inicial: YYYY-MM-DD
            data_final: YYYY-MM-DD
            modalidades: Lista de enums ModalidadeContratacao
            num_pages: Limite opcional de páginas (para testes/limites)

        Returns:
            Lista com todas as contratações do período
        """
        all_data = []
        pagina = 1

        while True:
            if num_pages is not None and num_pages <= 0:
                logger.info("num_pages <= 0, nenhuma página será buscada")
                break

            logger.info(f"Fetching página {pagina}...")

            result = self.fetch_contratacoes_by_date(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidades=modalidades,
                pagina=pagina,
            )

            data = result.get("data", [])

            if not data:
                break

            all_data.extend(data)

            # Check se tem mais páginas
            paginas_restantes = result.get("paginasRestantes", 0)

            if (
                num_pages is not None and pagina >= num_pages
            ) or paginas_restantes == 0:
                break
            pagina += 1

        logger.info(f"Total fetched: {len(all_data)} contratações")

        return all_data

    def fetch_contratacoes_yesterday(self) -> List[Dict]:
        """Busca contratações de ontem (uso comum em DAGs diários)"""
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

        return self.fetch_all_contratacoes_by_date(
            data_inicial=date_str, data_final=date_str
        )

    def fetch_contratacoes_last_30_days(self) -> List[Dict]:
        """Busca últimos 30 dias (backfill inicial)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        return self.fetch_all_contratacoes_by_date(
            data_inicial=start_date.strftime("%Y%m%d"),
            data_final=end_date.strftime("%Y%m%d"),
        )

    def fetch_itens_contratacao(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
        pagina: int = 1,
        tamanho_pagina: int = 100,
    ) -> List[Dict]:
        """
        Busca itens de uma contratação específica.

        Args:
            cnpj: CNPJ do órgão (ex: "83102277000152")
            ano: Ano da compra (ex: 2025)
            sequencial: Número sequencial da compra (ex: 423)
            pagina: Número da página (padrão: 1)
            tamanho_pagina: Registros por página (padrão: 100, max: 100)

        Returns:
            Lista de itens da contratação

        Example:
            >>> client.fetch_itens_contratacao(
            ...     cnpj="83102277000152",
            ...     ano=2025,
            ...     sequencial=423
            ... )
        """
        url = f"{self.base_url_integration}/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"

        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }

        response = self._make_request(url, params=params, timeout=30)

        # Handle empty responses
        if not response.content or response.content.strip() == b"":
            logger.warning(
                f"No items found for contratacao {cnpj}/{ano}/{sequencial}"
            )
            return []

        try:
            result = response.json()
        except ValueError as e:
            logger.warning(
                f"Invalid JSON response for items {cnpj}/{ano}/{sequencial}: {e}"
            )
            return []

        # API returns array directly (not wrapped in {"data": [...]})
        items = result if isinstance(result, list) else result.get("data", [])

        # Enrich with parsed domain codes
        from ..domains.pncp.utils import parse_item_response_codes

        for item in items:
            item["_parsed_domains"] = parse_item_response_codes(item)

        logger.info(f"Fetched {len(items)} items for {cnpj}/{ano}/{sequencial}")

        return items

    def fetch_all_itens_contratacao(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
    ) -> List[Dict]:
        """
        Busca TODOS os itens de uma contratação (paginando automaticamente).

        Args:
            cnpj: CNPJ do órgão
            ano: Ano da compra
            sequencial: Número sequencial da compra

        Returns:
            Lista completa de itens da contratação

        Example:
            >>> client.fetch_all_itens_contratacao(
            ...     cnpj="83102277000152",
            ...     ano=2025,
            ...     sequencial=423
            ... )
        """
        all_items = []
        pagina = 1

        while True:
            logger.debug(f"Fetching items page {pagina} for {cnpj}/{ano}/{sequencial}")

            items = self.fetch_itens_contratacao(
                cnpj=cnpj,
                ano=ano,
                sequencial=sequencial,
                pagina=pagina,
            )

            if not items:
                break

            all_items.extend(items)

            # If we got less than page size, we're done
            if len(items) < 100:
                break

            pagina += 1

        logger.info(
            f"Total items fetched: {len(all_items)} for {cnpj}/{ano}/{sequencial}"
        )

        return all_items

    def fetch_arquivos_contratacao(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
        pagina: int = 1,
        tamanho_pagina: int = 100,
    ) -> List[Dict]:
        """
        Busca arquivos/documentos de uma contratação específica.

        Args:
            cnpj: CNPJ do órgão (ex: "83102277000152")
            ano: Ano da compra (ex: 2025)
            sequencial: Número sequencial da compra (ex: 423)
            pagina: Número da página (padrão: 1)
            tamanho_pagina: Registros por página (padrão: 100, max: 100)

        Returns:
            Lista de arquivos/documentos da contratação

        Example:
            >>> client.fetch_arquivos_contratacao(
            ...     cnpj="83102277000152",
            ...     ano=2025,
            ...     sequencial=423
            ... )
        """
        url = f"{self.base_url_integration}/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"

        params = {
            "pagina": pagina,
            "tamanhoPagina": tamanho_pagina,
        }

        response = self._make_request(url, params=params, timeout=30)

        # Handle empty responses
        if not response.content or response.content.strip() == b"":
            logger.warning(
                f"No arquivos found for contratacao {cnpj}/{ano}/{sequencial}"
            )
            return []

        try:
            result = response.json()
        except ValueError as e:
            logger.warning(
                f"Invalid JSON response for arquivos {cnpj}/{ano}/{sequencial}: {e}"
            )
            return []

        # API returns array directly
        arquivos = result if isinstance(result, list) else result.get("data", [])

        # Enrich with parsed domain codes
        from ..domains.pncp.utils import parse_arquivo_response_codes

        for arquivo in arquivos:
            arquivo["_parsed_domains"] = parse_arquivo_response_codes(arquivo)

        logger.info(
            f"Fetched {len(arquivos)} arquivos for {cnpj}/{ano}/{sequencial}"
        )

        return arquivos

    def fetch_all_arquivos_contratacao(
        self,
        cnpj: str,
        ano: int,
        sequencial: int,
    ) -> List[Dict]:
        """
        Busca TODOS os arquivos de uma contratação (paginando automaticamente).

        Args:
            cnpj: CNPJ do órgão
            ano: Ano da compra
            sequencial: Número sequencial da compra

        Returns:
            Lista completa de arquivos da contratação

        Example:
            >>> client.fetch_all_arquivos_contratacao(
            ...     cnpj="83102277000152",
            ...     ano=2025,
            ...     sequencial=423
            ... )
        """
        all_arquivos = []
        pagina = 1

        while True:
            logger.debug(
                f"Fetching arquivos page {pagina} for {cnpj}/{ano}/{sequencial}"
            )

            arquivos = self.fetch_arquivos_contratacao(
                cnpj=cnpj,
                ano=ano,
                sequencial=sequencial,
                pagina=pagina,
            )

            if not arquivos:
                break

            all_arquivos.extend(arquivos)

            # If we got less than page size, we're done
            if len(arquivos) < 100:
                break

            pagina += 1

        logger.info(
            f"Total arquivos fetched: {len(all_arquivos)} for {cnpj}/{ano}/{sequencial}"
        )

        return all_arquivos


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = PNCPClient()

    # Buscar contratações de um dia específico
    contratacoes = client.fetch_all_contratacoes_by_date(
        data_inicial="20241020", data_final="20241020"
    )

    print(f"Total: {len(contratacoes)} contratações")

    if contratacoes:
        print("\nPrimeira contratação:")
        print(contratacoes[0])
