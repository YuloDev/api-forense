from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class TextractDocument:
    """Entidad de dominio para documento a procesar con AWS Textract"""
    content_bytes: bytes
    document_type: str
    size_bytes: int
    analysis_type: str = "DETECT_DOCUMENT_TEXT"
    features: Optional[List[str]] = None


@dataclass
class TextractAnalysisResult:
    """Entidad de dominio para resultado de análisis de Textract"""
    extracted_text: str
    average_confidence: float
    total_blocks: int
    metadata: Dict[str, Any]
    processing_time_ms: float


@dataclass
class DocumentMetadata:
    """Metadatos del documento procesado"""
    document_type: str
    size_bytes: int
    analysis_type: str
    total_blocks: int
    blocks_by_type: Dict[str, int]
    detected_documents: int
    min_confidence: float
    max_confidence: float
    text_lines: int
