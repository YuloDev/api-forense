from abc import ABC, abstractmethod
from typing import Dict, Any

from domain.entities.aws_textract_document import TextractDocument, TextractAnalysisResult
from domain.entities.aws_textract_forms import FormAnalysisResult, FormExtractionRequest
from domain.entities.aws_textract_tables import TableAnalysisResult, TableExtractionRequest


class AWSTextractService(ABC):
    """Puerto para servicio de AWS Textract OCR"""

    @abstractmethod
    def analyze_document(self, document: TextractDocument) -> TextractAnalysisResult:
        """Analiza un documento usando AWS Textract"""
        pass

    @abstractmethod
    def extract_forms(self, request: FormExtractionRequest) -> FormAnalysisResult:
        """Extrae formularios de un documento"""
        pass

    @abstractmethod
    def extract_tables(self, request: TableExtractionRequest) -> TableAnalysisResult:
        """Extrae tablas de un documento"""
        pass

    @abstractmethod
    def validate_document(self, document_base64: str) -> bytes:
        """Valida y decodifica documento base64"""
        pass

    @abstractmethod
    def detect_document_type(self, document_bytes: bytes) -> str:
        """Detecta el tipo de documento"""
        pass
