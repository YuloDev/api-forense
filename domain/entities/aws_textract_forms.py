from dataclasses import dataclass
from typing import Optional, List


@dataclass
class KeyValuePair:
    """Entidad de dominio para par clave-valor de formulario"""
    page: int
    key: str
    value: str
    key_confidence: float
    value_confidence: float
    key_id: str
    value_id: Optional[str]
    selection_status: Optional[str]


@dataclass
class FormAnalysisResult:
    """Resultado del análisis de formularios"""
    total_pairs: int
    key_value_pairs: List[KeyValuePair]
    average_key_confidence: float
    average_value_confidence: float
    document_type: str
    processing_time_ms: float


@dataclass
class FormExtractionRequest:
    """Petición para extracción de formularios"""
    document_bytes: bytes
    document_type: str
