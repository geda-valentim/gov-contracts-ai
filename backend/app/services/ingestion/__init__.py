"""Ingestion services for different data sources."""

from .cnpj import CNPJIngestionService
from .pncp import PNCPIngestionService

__all__ = ["PNCPIngestionService", "CNPJIngestionService"]
